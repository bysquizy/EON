"""EON Knowledge Base — local document parser, SQLite FTS5 keyword index, and optional vector similarity."""
from __future__ import annotations

import base64
import csv
import io
import math
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
import zlib


SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".docx", ".xlsx", ".pptx", ".pdf",
    ".json", ".html", ".htm", ".py", ".js", ".ts", ".sql", ".yaml", ".yml", ".xml", ".css",
}
CODE_TEXT_EXTENSIONS = {".json", ".html", ".htm", ".py", ".js", ".ts", ".sql", ".yaml", ".yml", ".xml", ".css"}
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_DOC_CHARS = 120000
MAX_CHUNKS_PER_DOC = 160
MAX_DOCS_PER_PROJECT = 32

INJECTION_PATTERNS = re.compile(
    r"(?:ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|"
    r"system\s*prompt\s*:|you\s+are\s+now\s+dan|"
    r"önceki\s+tüm\s+talimatları\s+unut|sistem\s+yönergesini\s+yoksay)",
    re.IGNORECASE,
)


def sanitize_untrusted_doc_text(text: str) -> tuple[str, bool]:
    """Neutralize indirect prompt-injection commands inside documents while preserving informational content."""
    if not isinstance(text, str):
        return "", False
    flagged = bool(INJECTION_PATTERNS.search(text))
    cleaned = INJECTION_PATTERNS.sub("[FİLTRELENMİŞ-TALİMAT]", text)
    return cleaned, flagged


class KnowledgeError(ValueError):
    pass


def _clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _check_safe_zip(zf: zipfile.ZipFile, max_uncompressed: int = 24 * 1024 * 1024) -> None:
    total = 0
    infos = zf.infolist()
    if len(infos) > 512:
        raise KnowledgeError("Arşiv çok fazla iç dosya içeriyor.")
    for info in infos:
        if ".." in info.filename or info.filename.startswith(("/", "\\")):
            raise KnowledgeError("Arşiv içi dosya yolu geçersiz.")
        total += info.file_size
        if total > max_uncompressed:
            raise KnowledgeError("Açılmış belge boyutu güvenlik sınırını aşıyor.")


def _parse_xml_safe(raw_bytes: bytes) -> ET.Element:
    text_head = raw_bytes[:4096].decode("utf-8", errors="ignore").upper()
    if "<!DOCTYPE" in text_head or "<!ENTITY" in text_head:
        raise KnowledgeError("XML varlık tanımı (DOCTYPE/ENTITY) güvenlik nedeniyle reddedildi.")
    try:
        return ET.fromstring(raw_bytes)
    except ET.ParseError as exc:
        raise KnowledgeError("Belge XML yapısı okunamadı.") from exc


def extract_docx_sections(raw: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            _check_safe_zip(zf)
            if "word/document.xml" not in zf.namelist():
                raise KnowledgeError("Geçerli bir DOCX belgesi değil.")
            xml_bytes = zf.read("word/document.xml")
    except zipfile.BadZipFile:
        raise KnowledgeError("DOCX dosyası bozuk veya okunamıyor.") from None
    root = _parse_xml_safe(xml_bytes)
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    sections = []
    current_heading = "Giriş"
    current_lines = []
    for p in root.iter(f"{ns}p"):
        style_el = p.find(f".//{ns}pStyle")
        style_val = style_el.attrib.get(f"{ns}val", "") if style_el is not None else ""
        texts = [t.text for t in p.iter(f"{ns}t") if t.text]
        line = "".join(texts).strip()
        if not line:
            continue
        if style_val.lower().startswith("heading") or (len(line) < 80 and style_val.lower() in ("title", "subtitle")):
            if current_lines:
                sections.append({"section": current_heading, "page": None, "text": "\n".join(current_lines)})
                current_lines = []
            current_heading = line[:80]
        else:
            current_lines.append(line)
    for tbl in root.iter(f"{ns}tbl"):
        rows = []
        for tr in tbl.iter(f"{ns}tr"):
            cells = []
            for tc in tr.iter(f"{ns}tc"):
                cell_text = " ".join("".join(t.text for t in p.iter(f"{ns}t") if t.text).strip() for p in tc.iter(f"{ns}p")).strip()
                cells.append(cell_text)
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            current_lines.append("\n".join(rows))
    if current_lines:
        sections.append({"section": current_heading, "page": None, "text": "\n".join(current_lines)})
    if not sections:
        raise KnowledgeError("DOCX içinde okunabilir metin bulunamadı.")
    return sections


def extract_xlsx_sections(raw: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            _check_safe_zip(zf)
            names = set(zf.namelist())
            if "xl/workbook.xml" not in names:
                raise KnowledgeError("Geçerli bir XLSX dosyası değil.")
            shared = []
            if "xl/sharedStrings.xml" in names:
                s_root = _parse_xml_safe(zf.read("xl/sharedStrings.xml"))
                for si in s_root.iter():
                    if si.tag.endswith("}si"):
                        parts = [t.text for t in si.iter() if t.tag.endswith("}t") and t.text]
                        shared.append("".join(parts))
            wb_root = _parse_xml_safe(zf.read("xl/workbook.xml"))
            sheet_names = []
            for el in wb_root.iter():
                if el.tag.endswith("}sheet") and el.attrib.get("name"):
                    sheet_names.append(el.attrib["name"])
            sheet_files = sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
            sections = []
            for idx, sfile in enumerate(sheet_files[:16]):
                s_root = _parse_xml_safe(zf.read(sfile))
                sname = sheet_names[idx] if idx < len(sheet_names) else f"Sayfa {idx + 1}"
                rows_out = []
                for row in s_root.iter():
                    if not row.tag.endswith("}row"):
                        continue
                    vals = []
                    for c in row:
                        if not c.tag.endswith("}c"):
                            continue
                        ctype = c.attrib.get("t", "")
                        v_el = next((ch for ch in c if ch.tag.endswith("}v")), None)
                        is_el = next((ch for ch in c if ch.tag.endswith("}is")), None)
                        val = ""
                        if ctype == "s" and v_el is not None and v_el.text:
                            try:
                                s_idx = int(v_el.text)
                                val = shared[s_idx] if 0 <= s_idx < len(shared) else ""
                            except ValueError:
                                val = ""
                        elif ctype == "inlineStr" and is_el is not None:
                            val = "".join(t.text for t in is_el.iter() if t.tag.endswith("}t") and t.text)
                        elif v_el is not None and v_el.text:
                            val = v_el.text
                        vals.append(val.strip())
                    if any(vals):
                        rows_out.append(" | ".join(vals))
                    if len(rows_out) >= 1500:
                        break
                if rows_out:
                    sections.append({"section": f"Tablo: {sname}", "page": idx + 1, "text": "\n".join(rows_out)})
    except zipfile.BadZipFile:
        raise KnowledgeError("XLSX dosyası bozuk veya okunamıyor.") from None
    if not sections:
        raise KnowledgeError("XLSX içinde okunabilir veri bulunamadı.")
    return sections


def extract_pptx_sections(raw: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            _check_safe_zip(zf)
            names = sorted(
                (n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                key=lambda s: int(re.findall(r"\d+", s)[-1]),
            )
            if not names:
                raise KnowledgeError("Geçerli bir PPTX sunumu değil veya slayt bulunamadı.")
            sections = []
            for idx, sfile in enumerate(names[:100], 1):
                root = _parse_xml_safe(zf.read(sfile))
                texts = [el.text.strip() for el in root.iter() if el.tag.endswith("}t") and el.text and el.text.strip()]
                if texts:
                    sections.append({"section": f"Slayt {idx}", "page": idx, "text": "\n".join(texts)})
    except zipfile.BadZipFile:
        raise KnowledgeError("PPTX dosyası bozuk veya okunamıyor.") from None
    if not sections:
        raise KnowledgeError("PPTX içinde okunabilir metin bulunamadı.")
    return sections


def windows_native_ocr(image_bytes: bytes, ext: str = ".png") -> str:
    """Offline OCR via Windows built-in WinRT Windows.Media.Ocr (zero third-party dependencies)."""
    import os
    import subprocess
    import sys
    import tempfile
    if sys.platform != "win32":
        return ""
    exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    if not os.path.isfile(exe):
        return ""
    fd, tmp_path = tempfile.mkstemp(prefix="eon-ocr-", suffix=ext if ext in (".png", ".jpg", ".jpeg", ".webp") else ".png")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image_bytes)
        script = (
            "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
            "$p=$args[0];"
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
            "$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime];"
            "$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime];"
            "$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime];"
            "$asTask=([System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'})[0];"
            "Function Await($op,$t){$m=$asTask.MakeGenericMethod($t);$tk=$m.Invoke($null,@($op));$tk.Wait();$tk.Result};"
            "$f=Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile]);"
            "$s=Await ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream]);"
            "$d=Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s)) ([Windows.Graphics.Imaging.BitmapDecoder]);"
            "$b=Await ($d.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]);"
            "$e=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();"
            "if($e){$r=Await ($e.RecognizeAsync($b)) ([Windows.Media.Ocr.OcrResult]);Write-Output $r.Text}"
        )
        res = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", script, tmp_path],
            capture_output=True, text=True, encoding="utf-8", timeout=12,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return _clean_text(res.stdout or "")
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _decode_pdf_literal(s: bytes) -> str:
    out = bytearray()
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == 92 and i + 1 < n:  # backslash
            nxt = s[i + 1]
            if nxt in (110, 114, 116):
                out.append({110: 10, 114: 13, 116: 9}[nxt])
                i += 2
                continue
            if 48 <= nxt <= 55:
                oct_digits = bytes([nxt])
                i += 2
                for _ in range(2):
                    if i < n and 48 <= s[i] <= 55:
                        oct_digits += bytes([s[i]])
                        i += 1
                    else:
                        break
                out.append(int(oct_digits, 8) & 0xFF)
                continue
            out.append(nxt)
            i += 2
        else:
            out.append(ch)
            i += 1
    if out.startswith(b"\xfe\xff"):
        return out[2:].decode("utf-16-be", errors="ignore")
    if out.startswith(b"\xff\xfe"):
        return out[2:].decode("utf-16-le", errors="ignore")
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return out.decode("cp1254", errors="ignore")


def _extract_text_from_pdf_stream(data: bytes) -> str:
    pieces = []
    # Match (string) Tj or [(string) ...] TJ
    for match in re.finditer(rb"\[((?:[^\[\]]|\([^()]*\))*)\]\s*TJ|\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*(?:Tj|'|\"|\b)", data):
        arr, single = match.groups()
        if single is not None:
            pieces.append(_decode_pdf_literal(single))
        elif arr is not None:
            sub = [ _decode_pdf_literal(m.group(1)) for m in re.finditer(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)", arr) ]
            if sub:
                pieces.append("".join(sub))
    for hex_match in re.finditer(rb"<([0-9A-Fa-f]{4,})>\s*Tj", data):
        raw_hex = hex_match.group(1)
        if len(raw_hex) % 2 == 0:
            try:
                b = bytes.fromhex(raw_hex.decode("ascii"))
                if b.startswith(b"\xfe\xff"):
                    pieces.append(b[2:].decode("utf-16-be", errors="ignore"))
                elif len(b) % 2 == 0 and all(x == 0 for x in b[0::2]):
                    pieces.append(b.decode("utf-16-be", errors="ignore"))
                else:
                    pieces.append(b.decode("latin-1", errors="ignore"))
            except ValueError:
                pass
    return _clean_text(" ".join(pieces))


def extract_pdf_sections(raw: bytes, cancel_event: threading.Event | None = None) -> list[dict]:
    if not raw.startswith(b"%PDF-"):
        raise KnowledgeError("Geçerli bir PDF başlığı bulunamadı.")
    # Check optional pypdf / fitz first if installed
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(io.BytesIO(raw))
        if len(reader.pages) > MAX_PDF_PAGES:
            raise KnowledgeError(f"PDF sayfa sınırı ({MAX_PDF_PAGES}) aşıldı.")
        sections = []
        for idx, page in enumerate(reader.pages, 1):
            if cancel_event and cancel_event.is_set():
                raise KnowledgeError("Dosya işleme iptal edildi.")
            txt = _clean_text(page.extract_text() or "")
            if txt:
                sections.append({"section": f"Sayfa {idx}", "page": idx, "text": txt})
        if sections:
            return sections
    except ImportError:
        pass
    except KnowledgeError:
        raise
    except Exception:
        pass

    # Pure-Python stdlib PDF content stream parser
    page_count = len(re.findall(rb"/Type\s*/Page\b(?!s)", raw))
    if page_count > MAX_PDF_PAGES:
        raise KnowledgeError(f"PDF sayfa sınırı ({MAX_PDF_PAGES}) aşıldı ({page_count} sayfa).")

    sections = []
    stream_idx = 0
    for match in re.finditer(rb"<<(.*?)>>\s*stream\r?\n(.*?)\r?\nendstream", raw, re.DOTALL):
        if cancel_event and cancel_event.is_set():
            raise KnowledgeError("Dosya işleme iptal edildi.")
        header, payload = match.group(1), match.group(2)
        if b"/Subtype" in header and b"/Image" in header:
            continue
        data = payload
        if b"/FlateDecode" in header:
            try:
                data = zlib.decompress(payload)
            except zlib.error:
                try:
                    data = zlib.decompress(payload.strip(b"\r\n"))
                except zlib.error:
                    continue
        if b"BT" not in data and b"Tj" not in data and b"TJ" not in data:
            continue
        text = _extract_text_from_pdf_stream(data)
        if text and len(text) >= 2:
            stream_idx += 1
            page_num = min(stream_idx, max(1, page_count)) if page_count else stream_idx
            sections.append({"section": f"Sayfa {page_num}", "page": page_num, "text": text})
            if len(sections) >= MAX_PDF_PAGES:
                break
    if not sections:
        raise KnowledgeError("PDF içinde okunabilir metin katmanı bulunamadı (taranmış görsel veya şifreli PDF olabilir).")
    return sections


def extract_document_sections(name: str, raw: bytes, cancel_event: threading.Event | None = None) -> list[dict]:
    if not isinstance(name, str) or not name.strip():
        raise KnowledgeError("Dosya adı gerekli.")
    ext = Path(name.strip()).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise KnowledgeError(f"Desteklenmeyen dosya biçimi ({ext or 'uzantısız'}). Desteklenenler: TXT, MD, CSV, DOCX, XLSX, PDF.")
    if not raw:
        raise KnowledgeError("Dosya boş.")
    if len(raw) > MAX_FILE_BYTES:
        raise KnowledgeError("Dosya boyutu 8 MiB sınırını aşıyor.")
    if cancel_event and cancel_event.is_set():
        raise KnowledgeError("İçe aktarma iptal edildi.")

    if ext in (".txt", ".md") or ext in CODE_TEXT_EXTENSIONS:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw.decode("utf-16")
            except UnicodeDecodeError:
                text = raw.decode("cp1254", errors="replace")
        if ext in (".html", ".htm"):
            text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
        text = _clean_text(text)
        if not text:
            raise KnowledgeError("Metin dosyası boş.")
        if ext == ".md":
            sections = []
            heading = "Başlangıç"
            buf = []
            for line in text.splitlines():
                m = re.match(r"^(#{1,4})\s+(.+)", line)
                if m:
                    if buf:
                        sections.append({"section": heading, "page": None, "text": "\n".join(buf).strip()})
                        buf = []
                    heading = m.group(2).strip()[:80]
                else:
                    buf.append(line)
            if buf and "\n".join(buf).strip():
                sections.append({"section": heading, "page": None, "text": "\n".join(buf).strip()})
            return sections or [{"section": "Metin", "page": None, "text": text}]
        return [{"section": f"Kaynak ({ext})", "page": 1, "text": text}]

    if ext == ".csv":
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1254", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = []
        for idx, row in enumerate(reader, 1):
            if cancel_event and cancel_event.is_set():
                raise KnowledgeError("İçe aktarma iptal edildi.")
            cleaned = [c.strip() for c in row]
            if any(cleaned):
                rows.append(" | ".join(cleaned))
            if idx >= 2500:
                break
        if not rows:
            raise KnowledgeError("CSV dosyasında okunabilir satır bulunamadı.")
        return [{"section": "CSV Tablosu", "page": 1, "text": "\n".join(rows)}]

    if ext == ".docx":
        return extract_docx_sections(raw)
    if ext == ".xlsx":
        return extract_xlsx_sections(raw)
    if ext == ".pptx":
        return extract_pptx_sections(raw)
    if ext == ".pdf":
        return extract_pdf_sections(raw, cancel_event=cancel_event)
    raise KnowledgeError("Desteklenmeyen dosya türü.")


def chunk_sections(sections: list[dict], chunk_size: int = 850, overlap: int = 120) -> list[dict]:
    chunks = []
    total_chars = 0
    for sec in sections:
        text = _clean_text(sec.get("text", ""))
        if not text:
            continue
        section_name = str(sec.get("section") or "Bölüm")[:80]
        page = sec.get("page") if type(sec.get("page")) is int else None
        pos = 0
        while pos < len(text):
            piece = text[pos:pos + chunk_size].strip()
            if piece:
                chunks.append({
                    "index": len(chunks),
                    "section": section_name,
                    "page": page,
                    "text": piece,
                })
                total_chars += len(piece)
            if len(chunks) >= MAX_CHUNKS_PER_DOC or total_chars >= MAX_DOC_CHARS:
                return chunks
            if pos + chunk_size >= len(text):
                break
            pos += max(1, chunk_size - overlap)
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


class KnowledgeBase:
    """In-memory SQLite FTS5 index backed by vault-persisted document records."""

    def __init__(self):
        self._lock = threading.RLock()
        self.documents: dict[str, dict] = {}
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_db()

    def close(self):
        try:
            self.db.close()
        except Exception:
            pass

    def __del__(self):
        self.close()

    def _init_db(self):
        with self._lock:
            self.db.execute("DROP TABLE IF EXISTS chunks_fts")
            self.db.execute(
                "CREATE VIRTUAL TABLE chunks_fts USING fts5("
                "doc_id UNINDEXED, project UNINDEXED, doc_name, section, page UNINDEXED, chunk_index UNINDEXED, content"
                ")"
            )

    def dump(self) -> dict:
        with self._lock:
            return dict(self.documents)

    def restore(self, data: dict) -> None:
        if not isinstance(data, dict):
            raise KnowledgeError("Bilgi tabanı verisi geçersiz.")
        with self._lock:
            self.documents.clear()
            self._init_db()
            for doc_id, doc in data.items():
                if not isinstance(doc_id, str) or not isinstance(doc, dict):
                    raise KnowledgeError("Belge kaydı geçersiz.")
                name = doc.get("name")
                project = doc.get("project", "")
                chunks = doc.get("chunks", [])
                if (not isinstance(name, str) or not 1 <= len(name) <= 160
                        or not isinstance(project, str) or not isinstance(chunks, list)
                        or len(chunks) > MAX_CHUNKS_PER_DOC):
                    raise KnowledgeError("Belge üstverisi geçersiz.")
                validated_chunks = []
                for idx, ch in enumerate(chunks):
                    if not isinstance(ch, dict) or not isinstance(ch.get("text"), str):
                        raise KnowledgeError("Belge parçası geçersiz.")
                    entry = {
                        "index": idx,
                        "section": str(ch.get("section") or "Bölüm")[:80],
                        "page": ch.get("page") if type(ch.get("page")) is int else None,
                        "text": ch["text"][:2000],
                    }
                    if isinstance(ch.get("embedding"), list) and all(isinstance(v, (int, float)) for v in ch["embedding"][:512]):
                        entry["embedding"] = [float(v) for v in ch["embedding"][:512]]
                    validated_chunks.append(entry)
                record = {
                    "id": doc_id,
                    "name": name,
                    "project": project,
                    "ext": str(doc.get("ext", Path(name).suffix.lower()))[:12],
                    "size": int(doc.get("size", 0)),
                    "added_at": int(doc.get("added_at", int(time.time()))),
                    "chunk_count": len(validated_chunks),
                    "chunks": validated_chunks,
                }
                self.documents[doc_id] = record
                self._index_doc(record)

    def _index_doc(self, record: dict) -> None:
        rows = [
            (
                record["id"],
                record["project"],
                record["name"],
                ch["section"],
                "" if ch["page"] is None else str(ch["page"]),
                str(ch["index"]),
                ch["text"],
            )
            for ch in record["chunks"]
        ]
        self.db.executemany(
            "INSERT INTO chunks_fts(doc_id, project, doc_name, section, page, chunk_index, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.db.commit()

    def import_document(self, *, name: str, raw: bytes, project: str = "",
                        cancel_event: threading.Event | None = None,
                        progress_cb=None, embed_fn=None) -> dict:
        clean_name = Path(name.strip()).name
        if not clean_name or len(clean_name) > 160:
            raise KnowledgeError("Geçerli bir dosya adı seç.")
        with self._lock:
            proj_docs = [d for d in self.documents.values() if d["project"] == project]
            if len(proj_docs) >= MAX_DOCS_PER_PROJECT:
                raise KnowledgeError(f"Proje başına en fazla {MAX_DOCS_PER_PROJECT} belge eklenebilir.")
        if progress_cb:
            progress_cb(0.15, "Belge ayrıştırılıyor...")
        sections = extract_document_sections(clean_name, raw, cancel_event=cancel_event)
        if progress_cb:
            progress_cb(0.55, "Metin bölümleniyor...")
        chunks = chunk_sections(sections)
        if not chunks:
            raise KnowledgeError("Belgeden aranabilir metin çıkarılamadı.")
        if embed_fn is not None:
            for i, ch in enumerate(chunks[:32]):
                if cancel_event and cancel_event.is_set():
                    raise KnowledgeError("İçe aktarma iptal edildi.")
                try:
                    vec = embed_fn(ch["text"])
                    if vec:
                        ch["embedding"] = vec[:512]
                except Exception:
                    break
                if progress_cb:
                    progress_cb(0.55 + 0.35 * ((i + 1) / min(len(chunks), 32)), "Vektör indeksi oluşturuluyor...")
        doc_id = secrets.token_hex(8)
        record = {
            "id": doc_id,
            "name": clean_name,
            "project": project,
            "ext": Path(clean_name).suffix.lower(),
            "size": len(raw),
            "added_at": int(time.time()),
            "chunk_count": len(chunks),
            "chunks": chunks,
        }
        with self._lock:
            self.documents[doc_id] = record
            self._index_doc(record)
        if progress_cb:
            progress_cb(1.0, "Tamamlandı.")
        return self.summary_item(record)

    @staticmethod
    def summary_item(record: dict) -> dict:
        return {
            "id": record["id"],
            "name": record["name"],
            "project": record["project"],
            "ext": record["ext"],
            "size": record["size"],
            "added_at": record["added_at"],
            "chunk_count": record["chunk_count"],
            "has_embeddings": any("embedding" in c for c in record.get("chunks", [])),
        }

    def list_documents(self, project: str | None = None) -> list[dict]:
        with self._lock:
            items = [
                self.summary_item(doc)
                for doc in self.documents.values()
                if project is None or doc["project"] == project
            ]
            return sorted(items, key=lambda d: (-d["added_at"], d["name"]))

    def remove_document(self, doc_id: str) -> None:
        with self._lock:
            if not isinstance(doc_id, str) or doc_id not in self.documents:
                raise KnowledgeError("Belge bulunamadı.")
            del self.documents[doc_id]
            self.db.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))
            self.db.commit()

    def remove_project_documents(self, project_id: str) -> None:
        with self._lock:
            to_delete = [k for k, v in self.documents.items() if v["project"] == project_id]
            for doc_id in to_delete:
                del self.documents[doc_id]
                self.db.execute("DELETE FROM chunks_fts WHERE doc_id = ?", (doc_id,))
            if to_delete:
                self.db.commit()

    def get_chunk(self, doc_id: str, chunk_index: int = 0) -> dict:
        with self._lock:
            doc = self.documents.get(doc_id)
            if not doc:
                raise KnowledgeError("Belge bulunamadı.")
            chunks = doc.get("chunks", [])
            idx = max(0, min(int(chunk_index), len(chunks) - 1)) if chunks else 0
            ch = chunks[idx] if chunks else {"index": 0, "section": "Bölüm", "page": None, "text": ""}
            return {
                "doc_id": doc["id"],
                "name": doc["name"],
                "project": doc["project"],
                "chunk_count": len(chunks),
                "chunk_index": ch["index"],
                "section": ch["section"],
                "page": ch["page"],
                "text": ch["text"],
            }

    def search(self, query: str, *, project: str = "", limit: int = 5, query_embedding: list[float] | None = None) -> list[dict]:
        if not isinstance(query, str):
            return []
        tokens = [t for t in re.findall(r"[\w]{2,}", query.casefold()) if len(t) >= 2][:12]
        with self._lock:
            proj_docs = [d for d in self.documents.values() if d["project"] == project]
            if not proj_docs:
                return []
            bm25_ranks: dict[tuple[str, int], int] = {}
            scored: dict[tuple[str, int], dict] = {}
            if tokens:
                fts_expr = " OR ".join(f'"{t}"*' for t in tokens)
                try:
                    cur = self.db.execute(
                        "SELECT doc_id, doc_name, section, page, chunk_index, content, bm25(chunks_fts) AS rank "
                        "FROM chunks_fts WHERE chunks_fts MATCH ? AND project = ? ORDER BY rank LIMIT ?",
                        (fts_expr, project, limit * 4),
                    )
                    for r_idx, (doc_id, doc_name, section, page, chunk_index, content, rank) in enumerate(cur.fetchall(), 1):
                        key = (doc_id, int(chunk_index))
                        bm25_ranks[key] = r_idx
                        scored[key] = {
                            "doc_id": doc_id,
                            "name": doc_name,
                            "section": section,
                            "page": int(page) if page.isdigit() else None,
                            "chunk_index": int(chunk_index),
                            "snippet": content,
                            "score": float(-rank) if isinstance(rank, (int, float)) else 1.0,
                        }
                except sqlite3.OperationalError:
                    pass
            # Hybrid RRF (Reciprocal Rank Fusion, k=60) + keyword overlap + vector cosine similarity
            vec_candidates = []
            for doc in proj_docs:
                for ch in doc["chunks"]:
                    key = (doc["id"], ch["index"])
                    low_text = ch["text"].casefold()
                    kw_hits = sum(1 for t in tokens if t in low_text)
                    vec_sim = _cosine(query_embedding, ch.get("embedding", [])) if query_embedding and ch.get("embedding") else 0.0
                    if vec_sim > 0.15:
                        vec_candidates.append((key, vec_sim))
                    if kw_hits > 0 or vec_sim > 0.20 or key in bm25_ranks:
                        entry = scored.get(key) or {
                            "doc_id": doc["id"],
                            "name": doc["name"],
                            "section": ch["section"],
                            "page": ch["page"],
                            "chunk_index": ch["index"],
                            "snippet": ch["text"],
                            "score": 0.0,
                        }
                        rrf_bm25 = (1.0 / (60 + bm25_ranks[key])) if key in bm25_ranks else 0.0
                        entry["score"] += rrf_bm25 * 50.0 + kw_hits * 1.4 + vec_sim * 4.5
                        scored[key] = entry
            if vec_candidates:
                vec_candidates.sort(key=lambda x: -x[1])
                for v_rank, (key, _) in enumerate(vec_candidates, 1):
                    if key in scored:
                        scored[key]["score"] += (1.0 / (60 + v_rank)) * 50.0
            ranked = sorted(scored.values(), key=lambda x: (-x["score"], x["name"], x["chunk_index"]))
            return ranked[:limit]
