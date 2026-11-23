"""EON Actions — modular, allowlisted, preview-and-confirm local skill system.

No arbitrary shell/CMD/PowerShell command tool exists.
Every file operation is restricted to user-authorized folders, rejects symlink/junction escape,
UNC paths, and dangerous executable/script extensions, and maintains rollback + redacted audit logs.
"""
from __future__ import annotations

import ctypes
import fnmatch
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time

from .knowledge import extract_document_sections, KnowledgeError


DANGEROUS_EXTENSIONS = {
    ".exe", ".dll", ".sys", ".bat", ".cmd", ".ps1", ".psm1", ".vbs", ".vbe",
    ".js", ".jse", ".wsf", ".wsh", ".msi", ".msp", ".scr", ".com", ".pif",
    ".hta", ".cpl", ".msc", ".jar", ".reg", ".lnk", ".url", ".py", ".pyw",
}
SAFE_WRITE_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".docx", ".xlsx", ".pdf", ".ics"}
SECRET_REDACT_RE = re.compile(r"(?:AIza[0-9A-Za-z_-]{20,}|ghp_[0-9A-Za-z]{20,}|sk-[0-9A-Za-z_-]{16,})")


class ActionError(ValueError):
    pass


def redact_text(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return SECRET_REDACT_RE.sub("[REDACTED]", value)[:240]


def is_reparse_or_symlink(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
    except OSError:
        return True
    if hasattr(os, "lstat"):
        try:
            st = os.lstat(path)
            if getattr(st, "st_file_attributes", 0) & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                return True
        except OSError:
            pass
    if os.name == "nt":
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != 0xFFFFFFFF and (attrs & 0x400):
                return True
        except Exception:
            pass
    return False


def validate_folder_path(raw_path: str) -> Path:
    if not isinstance(raw_path, str) or not 1 <= len(raw_path.strip()) <= 512 or "\x00" in raw_path:
        raise ActionError("Klasör yolu geçersiz.")
    cleaned = raw_path.strip().strip('"')
    if cleaned.startswith(("\\\\", "//")):
        raise ActionError("Ağ (UNC) yollarına izin verilmez.")
    if os.name == "nt" and not re.match(r"^[A-Za-z]:[\\/]", cleaned):
        raise ActionError("Tam yerel disk yolu gerekli (örn. C:\\Calisma\\Belgeler).")
    p = Path(cleaned)
    if not p.is_absolute():
        raise ActionError("Tam (mutlak) klasör yolu gerekli.")
    if not p.exists() or not p.is_dir():
        raise ActionError("Klasör bulunamadı.")
    for candidate in (p, *p.parents):
        if is_reparse_or_symlink(candidate):
            raise ActionError("Sembolik bağlantı veya junction içeren klasörlere izin verilmez.")
    resolved = p.resolve(strict=True)
    # Block system root or Windows directories
    low = str(resolved).replace("/", "\\").casefold()
    for forbidden in ("c:\\windows", "c:\\program files", "c:\\program files (x86)", "c:\\programdata"):
        if low == forbidden or low.startswith(forbidden + "\\"):
            raise ActionError("Sistem ve program klasörleri çalışma klasörü olarak eklenemez.")
    return resolved


def resolve_inside_allowed(target_raw: str, allowed_roots: list[str], *, must_exist: bool = True,
                           allow_dir: bool = False, write_mode: bool = False) -> tuple[Path, Path]:
    if not isinstance(target_raw, str) or not 1 <= len(target_raw.strip()) <= 600 or "\x00" in target_raw:
        raise ActionError("Hedef dosya yolu geçersiz.")
    cleaned = target_raw.strip().strip('"')
    if cleaned.startswith(("\\\\", "//")):
        raise ActionError("UNC veya ağ yollarına erişilemez.")
    if not allowed_roots:
        raise ActionError("Önce Araçlar bölümünden en az bir izinli çalışma klasörü ekle.")
    roots = [validate_folder_path(r) for r in allowed_roots]
    candidate = Path(cleaned)
    if not candidate.is_absolute():
        candidate = roots[0] / candidate

    # Check every existing prefix for symlink/reparse point before resolve()
    check_curr = candidate
    to_check = []
    while True:
        to_check.append(check_curr)
        if check_curr.parent == check_curr:
            break
        check_curr = check_curr.parent
    for part_path in to_check:
        if part_path.exists() and is_reparse_or_symlink(part_path):
            raise ActionError("Sembolik bağlantı veya junction tespit edildi; işlem engellendi.")

    try:
        if must_exist:
            if not candidate.exists():
                raise ActionError("Hedef dosya veya klasör bulunamadı.")
            resolved = candidate.resolve(strict=True)
        else:
            parent_resolved = candidate.parent.resolve(strict=True)
            resolved = parent_resolved / candidate.name
    except (OSError, RuntimeError):
        raise ActionError("Hedef yol doğrulanamadı.") from None

    matched_root = None
    for root in roots:
        try:
            resolved.relative_to(root)
            matched_root = root
            break
        except ValueError:
            continue
    if matched_root is None:
        raise ActionError("Hedef yol izinli çalışma klasörlerinin dışında.")

    ext = resolved.suffix.lower()
    if ext in DANGEROUS_EXTENSIONS:
        raise ActionError(f"Güvenlik kuralı: '{ext}' uzantılı çalıştırılabilir veya betik dosyalarına erişilemez.")
    if write_mode and not allow_dir and ext not in SAFE_WRITE_EXTENSIONS:
        raise ActionError(f"Yazma işlemi yalnızca güvenli belge uzantılarını destekler: {', '.join(sorted(SAFE_WRITE_EXTENSIONS))}")
    return resolved, matched_root


SKILLS = {
    "search_files": {
        "name": "search_files",
        "title": "İzinli Klasörde Dosya Ara",
        "description": "İzinli çalışma klasörlerinde dosya adına veya uzantısına göre arama yapar.",
        "risk": "low",
        "scope": "filesystem:read",
        "requires_confirmation": False,
        "schema": {"query": "Aranacak dosya adı veya desen (örn. *.pdf, rapor)"},
    },
    "read_file": {
        "name": "read_file",
        "title": "Dosya Oku",
        "description": "İzinli klasördeki bir belgenin (TXT, MD, CSV, DOCX, XLSX, PDF) metin içeriğini okur.",
        "risk": "low",
        "scope": "filesystem:read",
        "requires_confirmation": False,
        "schema": {"path": "Okunacak dosyanın yolu"},
    },
    "summarize_file": {
        "name": "summarize_file",
        "title": "Dosya Özeti Çıkar",
        "description": "İzinli klasördeki bir belgenin içeriğini çıkarır ve yapılandırılmış özetini hazırlar.",
        "risk": "low",
        "scope": "filesystem:read",
        "requires_confirmation": False,
        "schema": {"path": "Özetlenecek dosyanın yolu"},
    },
    "create_folder": {
        "name": "create_folder",
        "title": "Klasör Oluştur",
        "description": "İzinli çalışma klasörü içinde yeni bir alt klasör oluşturur.",
        "risk": "medium",
        "scope": "filesystem:write",
        "requires_confirmation": True,
        "schema": {"path": "Oluşturulacak klasör yolu"},
    },
    "write_text_file": {
        "name": "write_text_file",
        "title": "Metin Belgesi Üret / Güncelle",
        "description": "İzinli klasörde TXT, MD veya CSV belgesi oluşturur ya da mevcut belgeyi yedekleyerek günceller.",
        "risk": "high",
        "scope": "filesystem:write",
        "requires_confirmation": True,
        "schema": {"path": "Hedef dosya yolu (.txt, .md, .csv)", "content": "Yazılacak metin içeriği"},
    },
    "rename_file": {
        "name": "rename_file",
        "title": "Güvenli Yeniden Adlandır",
        "description": "İzinli klasördeki bir dosyayı güvenli uzantı kontrolü ve geri alma kaydıyla yeniden adlandırır.",
        "risk": "medium",
        "scope": "filesystem:write",
        "requires_confirmation": True,
        "schema": {"path": "Mevcut dosya yolu", "new_name": "Yeni dosya adı"},
    },
    "open_app": {
        "name": "open_app",
        "title": "Kayıtlı Uygulamayı Aç",
        "description": "Uygulama başlatıcısında kayıtlı bir programı kullanıcı onayından sonra başlatır.",
        "risk": "high",
        "scope": "process:launch",
        "requires_confirmation": True,
        "schema": {"app_id": "Kayıtlı uygulama kimliği"},
    },
}


class ActionCenter:
    def __init__(self, launcher=None):
        self._lock = threading.RLock()
        self.launcher = launcher
        self.allowed_folders: list[str] = []
        self.pending: dict[str, dict] = {}
        self.rollback_stack: list[dict] = []
        self.audit_log: list[dict] = []

    def dump(self) -> dict:
        with self._lock:
            return {
                "allowed_folders": list(self.allowed_folders),
                "audit_log": list(self.audit_log[-80:]),
            }

    def restore(self, data: dict) -> None:
        if not isinstance(data, dict):
            return
        with self._lock:
            folders = data.get("allowed_folders", [])
            if isinstance(folders, list):
                valid = []
                for f in folders[:16]:
                    if isinstance(f, str):
                        try:
                            valid.append(str(validate_folder_path(f)))
                        except ActionError:
                            pass
                self.allowed_folders = list(dict.fromkeys(valid))
            logs = data.get("audit_log", [])
            if isinstance(logs, list):
                self.audit_log = [
                    {
                        "id": str(entry.get("id", ""))[:24],
                        "time": int(entry.get("time", 0)),
                        "skill": str(entry.get("skill", ""))[:40],
                        "target": redact_text(str(entry.get("target", ""))),
                        "status": str(entry.get("status", ""))[:32],
                        "approved": bool(entry.get("approved", False)),
                        "detail": redact_text(str(entry.get("detail", ""))),
                    }
                    for entry in logs[-80:]
                    if isinstance(entry, dict)
                ]

    def _log(self, skill: str, target: str, status: str, approved: bool, detail: str = "") -> dict:
        entry = {
            "id": secrets.token_hex(6),
            "time": int(time.time()),
            "skill": skill,
            "target": redact_text(target),
            "status": status,
            "approved": approved,
            "detail": redact_text(detail),
        }
        with self._lock:
            self.audit_log.append(entry)
            if len(self.audit_log) > 100:
                self.audit_log = self.audit_log[-100:]
        return entry

    def add_folder(self, path: str) -> list[str]:
        resolved = str(validate_folder_path(path))
        with self._lock:
            if resolved not in self.allowed_folders:
                if len(self.allowed_folders) >= 12:
                    raise ActionError("En fazla 12 izinli klasör eklenebilir.")
                self.allowed_folders.append(resolved)
            self._log("folder_allow", resolved, "added", True, "İzinli klasör eklendi")
            return list(self.allowed_folders)

    def remove_folder(self, path: str) -> list[str]:
        with self._lock:
            target = str(Path(path.strip())) if isinstance(path, str) else ""
            self.allowed_folders = [f for f in self.allowed_folders if f.casefold() != target.casefold()]
            self._log("folder_revoke", target, "removed", True, "Klasör izni kaldırıldı")
            return list(self.allowed_folders)

    def list_skills(self) -> list[dict]:
        return list(SKILLS.values())

    def preview_or_run(self, skill_name: str, params: dict, summarizer=None) -> dict:
        if skill_name not in SKILLS or not isinstance(params, dict):
            raise ActionError("Geçersiz beceri veya parametre.")
        spec = SKILLS[skill_name]

        # Read-only low-risk skills run directly within allowed folders
        if skill_name == "search_files":
            query = str(params.get("query", "")).strip()
            if not query or len(query) > 120:
                raise ActionError("Arama sorgusu 1–120 karakter olmalı.")
            with self._lock:
                roots = [validate_folder_path(r) for r in self.allowed_folders]
            if not roots:
                raise ActionError("Önce izinli bir çalışma klasörü ekle.")
            matches = []
            pattern = f"*{query.casefold()}*" if "*" not in query and "?" not in query else query.casefold()
            seen = 0
            for root in roots:
                for dirpath, subdirs, filenames in os.walk(root, followlinks=False, onerror=lambda _: None):
                    subdirs[:] = [d for d in subdirs if not is_reparse_or_symlink(Path(dirpath, d))]
                    for fname in sorted(filenames):
                        seen += 1
                        if seen > 5000:
                            break
                        fpath = Path(dirpath) / fname
                        if is_reparse_or_symlink(fpath) or fpath.suffix.lower() in DANGEROUS_EXTENSIONS:
                            continue
                        if fnmatch.fnmatch(fname.casefold(), pattern):
                            try:
                                st = fpath.stat()
                                matches.append({
                                    "name": fname,
                                    "path": str(fpath),
                                    "size": st.st_size,
                                })
                            except OSError:
                                pass
                            if len(matches) >= 50:
                                break
                    if len(matches) >= 50 or seen > 5000:
                        break
            self._log("search_files", query, "completed", False, f"{len(matches)} dosya bulundu")
            return {"executed": True, "skill": skill_name, "matches": matches}

        if skill_name in ("read_file", "summarize_file"):
            with self._lock:
                roots = list(self.allowed_folders)
            target, _ = resolve_inside_allowed(str(params.get("path", "")), roots, must_exist=True)
            if not target.is_file():
                raise ActionError("Belirtilen yol bir dosya değil.")
            try:
                raw = target.read_bytes()
                sections = extract_document_sections(target.name, raw)
            except (OSError, KnowledgeError) as exc:
                raise ActionError(str(exc)) from None
            combined = "\n\n".join(f"[{s['section']}]\n{s['text']}" for s in sections)[:16000]
            summary_text = ""
            if skill_name == "summarize_file":
                if summarizer is not None:
                    summary_text = summarizer(target.name, combined[:8000])
                else:
                    lines = [line.strip() for line in combined.splitlines() if line.strip()][:8]
                    summary_text = "\n".join(f"- {line[:180]}" for line in lines)
            self._log(skill_name, str(target), "completed", False, f"{len(combined)} karakter okundu")
            return {
                "executed": True,
                "skill": skill_name,
                "path": str(target),
                "name": target.name,
                "content": combined[:6000],
                "summary": summary_text,
            }

        # Write / Launch skills ALWAYS produce a preview token and wait for user approval
        with self._lock:
            roots = list(self.allowed_folders)
            if len(self.pending) >= 24:
                self.pending.clear()
            token = secrets.token_urlsafe(16)

            if skill_name == "create_folder":
                target, _ = resolve_inside_allowed(str(params.get("path", "")), roots, must_exist=False, allow_dir=True, write_mode=True)
                if target.exists():
                    raise ActionError("Bu konumda zaten bir dosya veya klasör var.")
                plan = {
                    "token": token,
                    "skill": skill_name,
                    "title": spec["title"],
                    "risk": spec["risk"],
                    "target": str(target),
                    "affected_files": [str(target)],
                    "change_summary": f"Yeni klasör oluşturulacak: {target}",
                    "params": {"target": str(target)},
                    "created_at": int(time.time()),
                }

            elif skill_name == "write_text_file":
                target, _ = resolve_inside_allowed(str(params.get("path", "")), roots, must_exist=False, write_mode=True)
                if target.suffix.lower() not in (".txt", ".md", ".csv", ".json", ".ics"):
                    raise ActionError("Metin yazma aracı yalnız .txt, .md, .csv, .json ve .ics uzantılarını kabul eder.")
                content = params.get("content", "")
                if not isinstance(content, str) or len(content) > 250000:
                    raise ActionError("Dosya içeriği geçersiz veya çok büyük.")
                exists = target.exists()
                if exists and not target.is_file():
                    raise ActionError("Hedef yol bir dosya değil.")
                old_preview = ""
                if exists:
                    try:
                        old_preview = target.read_text(encoding="utf-8", errors="replace")[:400]
                    except OSError:
                        old_preview = "(Mevcut dosya)"
                plan = {
                    "token": token,
                    "skill": skill_name,
                    "title": spec["title"],
                    "risk": spec["risk"],
                    "target": str(target),
                    "affected_files": [str(target)],
                    " overwrite": exists,
                    "change_summary": (
                        f"Mevcut dosya güncellenecek (önceki sürüm yedeklenir): {target.name} ({len(content)} karakter)"
                        if exists else f"Yeni dosya oluşturulacak: {target.name} ({len(content)} karakter)"
                    ),
                    "preview_before": old_preview,
                    "preview_after": content[:600],
                    "params": {"target": str(target), "content": content},
                    "created_at": int(time.time()),
                }

            elif skill_name == "rename_file":
                src, root = resolve_inside_allowed(str(params.get("path", "")), roots, must_exist=True, write_mode=True)
                if not src.is_file():
                    raise ActionError("Yeniden adlandırılacak hedef bir dosya olmalı.")
                new_name = str(params.get("new_name", "")).strip()
                if not new_name or "/" in new_name or "\\" in new_name or ".." in new_name:
                    raise ActionError("Geçerli bir yeni dosya adı gir (klasör ayracı içeremez).")
                dst, _ = resolve_inside_allowed(str(src.parent / new_name), [str(root)], must_exist=False, write_mode=True)
                if dst.exists():
                    raise ActionError("Hedef isimde başka bir dosya zaten mevcut.")
                plan = {
                    "token": token,
                    "skill": skill_name,
                    "title": spec["title"],
                    "risk": spec["risk"],
                    "target": str(src),
                    "affected_files": [str(src), str(dst)],
                    "change_summary": f"'{src.name}' dosyası '{dst.name}' olarak yeniden adlandırılacak.",
                    "params": {"src": str(src), "dst": str(dst)},
                    "created_at": int(time.time()),
                }

            elif skill_name == "open_app":
                if self.launcher is None:
                    raise ActionError("Uygulama başlatıcı kullanılamıyor.")
                app_id = str(params.get("app_id", "")).strip()
                exe_target = self.launcher.target(app_id)
                plan = {
                    "token": token,
                    "skill": skill_name,
                    "title": spec["title"],
                    "risk": spec["risk"],
                    "target": exe_target,
                    "affected_files": [exe_target],
                    "change_summary": f"Uygulama başlatılacak: {exe_target}",
                    "params": {"app_id": app_id, "target": exe_target},
                    "created_at": int(time.time()),
                }
            else:
                raise ActionError("Desteklenmeyen eylem.")

            self.pending[token] = plan
            self._log(skill_name, plan["target"], "previewed", False, plan["change_summary"])
            return {
                "executed": False,
                "requires_confirmation": True,
                "preview": {k: v for k, v in plan.items() if k != "params"},
            }

    def confirm(self, token: str, approve: bool) -> dict:
        with self._lock:
            if not isinstance(token, str) or token not in self.pending:
                raise ActionError("Onay bekleyen işlem bulunamadı veya süresi doldu.")
            plan = self.pending.pop(token)
            skill = plan["skill"]
            if not approve:
                self._log(skill, plan["target"], "cancelled", False, "Kullanıcı tarafından iptal edildi")
                return {"cancelled": True, "skill": skill}

            roots = list(self.allowed_folders)
            params = plan["params"]
            if skill == "create_folder":
                target, _ = resolve_inside_allowed(params["target"], roots, must_exist=False, allow_dir=True, write_mode=True)
                target.mkdir(parents=False, exist_ok=False)
                self.rollback_stack.append({"kind": "create_folder", "target": str(target), "time": int(time.time())})
                self._log(skill, str(target), "executed", True, "Klasör oluşturuldu")
                return {"executed": True, "skill": skill, "target": str(target), "rollback_available": True}

            if skill == "write_text_file":
                target, _ = resolve_inside_allowed(params["target"], roots, must_exist=False, write_mode=True)
                previous_bytes = target.read_bytes() if target.exists() else None
                fd, tmp = tempfile.mkstemp(prefix=".eon-act-", dir=target.parent)
                try:
                    with os.fdopen(fd, "wb") as handle:
                        handle.write(params["content"].encode("utf-8"))
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(tmp, target)
                finally:
                    Path(tmp).unlink(missing_ok=True)
                self.rollback_stack.append({
                    "kind": "write_text_file",
                    "target": str(target),
                    "previous_bytes": previous_bytes,
                    "time": int(time.time()),
                })
                self._log(skill, str(target), "executed", True, "Belge kaydedildi")
                return {"executed": True, "skill": skill, "target": str(target), "rollback_available": True}

            if skill == "rename_file":
                src, root = resolve_inside_allowed(params["src"], roots, must_exist=True, write_mode=True)
                dst, _ = resolve_inside_allowed(params["dst"], [str(root)], must_exist=False, write_mode=True)
                if dst.exists():
                    raise ActionError("Hedef dosya adı zaten kullanımda.")
                os.replace(src, dst)
                self.rollback_stack.append({
                    "kind": "rename_file",
                    "src": str(src),
                    "dst": str(dst),
                    "time": int(time.time()),
                })
                self._log(skill, f"{src.name} -> {dst.name}", "executed", True, "Dosya yeniden adlandırıldı")
                return {"executed": True, "skill": skill, "target": str(dst), "rollback_available": True}

            if skill == "open_app":
                self.launcher.launch(params["app_id"], params["target"])
                self._log(skill, params["target"], "executed", True, "Uygulama başlatıldı")
                return {"executed": True, "skill": skill, "target": params["target"], "rollback_available": bool(self.rollback_stack)}

            raise ActionError("Bilinmeyen işlem.")

    def rollback_last(self) -> dict:
        with self._lock:
            if not self.rollback_stack:
                raise ActionError("Geri alınacak dosya işlemi yok.")
            entry = self.rollback_stack.pop()
            kind = entry["kind"]
            roots = list(self.allowed_folders)
            if kind == "create_folder":
                target, _ = resolve_inside_allowed(entry["target"], roots, must_exist=True, allow_dir=True, write_mode=True)
                try:
                    target.rmdir()
                except OSError:
                    raise ActionError("Klasör boş olmadığı için geri alınamadı.") from None
                self._log("rollback", str(target), "rolled_back", True, "Oluşturulan klasör kaldırıldı")
                return {"rolled_back": True, "target": str(target)}

            if kind == "write_text_file":
                target, _ = resolve_inside_allowed(entry["target"], roots, must_exist=False, write_mode=True)
                prev = entry["previous_bytes"]
                if prev is None:
                    target.unlink(missing_ok=True)
                    detail = "Oluşturulan dosya silindi"
                else:
                    target.write_bytes(prev)
                    detail = "Önceki dosya sürümü geri yüklendi"
                self._log("rollback", str(target), "rolled_back", True, detail)
                return {"rolled_back": True, "target": str(target), "detail": detail}

            if kind == "rename_file":
                dst, root = resolve_inside_allowed(entry["dst"], roots, must_exist=True, write_mode=True)
                src, _ = resolve_inside_allowed(entry["src"], [str(root)], must_exist=False, write_mode=True)
                if src.exists():
                    raise ActionError("Eski dosya konumunda başka bir dosya var; geri alınamadı.")
                os.replace(dst, src)
                self._log("rollback", f"{dst.name} -> {src.name}", "rolled_back", True, "Ad değişikliği geri alındı")
                return {"rolled_back": True, "target": str(src)}

            raise ActionError("Bu işlem türü geri alınamıyor.")
