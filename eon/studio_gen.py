"""EON Studio — pure-Python document generation (DOCX, PDF, XLSX, CSV, Markdown, TXT).

Produces valid Office Open XML (.docx / .xlsx) and PDF 1.4 documents without mandatory external libraries.
"""
from __future__ import annotations

import base64
import csv
import io
from pathlib import Path
import re
import tempfile
import os
import xml.sax.saxutils as sax
import zipfile

from .actions import resolve_inside_allowed, ActionError


STUDIO_FORMATS = {"docx", "pdf", "xlsx", "csv", "md", "txt"}


class StudioError(ValueError):
    pass


def _esc(text: str) -> str:
    return sax.escape(str(text).replace("\x00", ""))


def parse_table_rows(content: str) -> list[list[str]]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    md_rows = []
    for i, line in enumerate(lines):
        if "|" in line:
            if re.match(r"^\s*\|?(?:\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?\s*$", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if any(cells):
                md_rows.append(cells)
    if len(md_rows) >= 2:
        return md_rows
    reader = csv.reader(io.StringIO(content))
    rows = []
    for row in reader:
        cleaned = [c.strip() for c in row]
        if any(cleaned):
            rows.append(cleaned)
    return rows if rows else [[line] for line in lines]


def build_docx_bytes(title: str, content: str) -> bytes:
    buf = io.BytesIO()
    paragraphs = []
    if title.strip():
        paragraphs.append(
            f'<w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr><w:t>{_esc(title.strip())}</w:t></w:r></w:p>'
        )
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line:
            paragraphs.append("<w:p/>")
            continue
        m_head = re.match(r"^(#{1,3})\s+(.+)", line)
        if m_head:
            sz = {1: "32", 2: "28", 3: "24"}[len(m_head.group(1))]
            paragraphs.append(
                f'<w:p><w:r><w:rPr><w:b/><w:sz w:val="{sz}"/></w:rPr>'
                f'<w:t>{_esc(m_head.group(2))}</w:t></w:r></w:p>'
            )
        else:
            paragraphs.append(
                f'<w:p><w:r><w:t xml:space="preserve">{_esc(line)}</w:t></w:r></w:p>'
            )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{"".join(paragraphs)}<w:sectPr/></w:body></w:document>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        '</Relationships>'
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


def _col_letter(idx: int) -> str:
    res = ""
    n = idx + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        res = chr(65 + rem) + res
    return res


def build_xlsx_bytes(title: str, content: str) -> bytes:
    rows = parse_table_rows(content)
    buf = io.BytesIO()
    row_xml = []
    for r_idx, row in enumerate(rows[:2000], 1):
        cells = []
        for c_idx, val in enumerate(row[:64]):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if re.fullmatch(r"-?\d+(?:\.\d+)?", val):
                cells.append(f'<c r="{ref}"><v>{val}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{_esc(val)}</t></is></c>')
        row_xml.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )
    sheet_title = re.sub(r"[\[\]\*\?/\\:]", "", title.strip() or "Veri")[:31] or "Veri"
    wb_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{_esc(sheet_title)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    ctypes = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ctypes)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", wb_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()


_TR_MAP = str.maketrans({
    "ğ": "g", "Ğ": "G", "ü": "u", "Ü": "U", "ş": "s", "Ş": "S",
    "ı": "i", "İ": "I", "ö": "o", "Ö": "O", "ç": "c", "Ç": "C",
    "—": "-", "–": "-", "“": '"', "”": '"', "’": "'", "‘": "'", "…": "...", "•": "*", "·": ".",
})


def _pdf_safe_line(text: str) -> str:
    # Standard Type1 Helvetica supports WinAnsi/Latin-1; normalize unsupported glyphs cleanly
    norm = text.translate(_TR_MAP)
    safe = norm.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_bytes(title: str, content: str) -> bytes:
    wrapped_lines = []
    if title.strip():
        wrapped_lines.append(("B", title.strip()[:80]))
        wrapped_lines.append(("N", ""))
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            wrapped_lines.append(("N", ""))
            continue
        while len(line) > 88:
            split_at = line.rfind(" ", 0, 88)
            if split_at <= 20:
                split_at = 88
            wrapped_lines.append(("N", line[:split_at]))
            line = line[split_at:].lstrip()
        wrapped_lines.append(("N", line))

    lines_per_page = 44
    pages_lines = [wrapped_lines[i:i + lines_per_page] for i in range(0, max(1, len(wrapped_lines)), lines_per_page)]
    pages_lines = pages_lines[:40]

    objects: list[bytes] = []

    def add_obj(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font_obj = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font_bold_obj = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    pages_id_placeholder = add_obj(b"")  # Obj 3 reserved for /Pages

    page_ids = []
    for plines in pages_lines:
        cmds = [b"BT", b"50 780 Td", b"15 TL"]
        for style, txt in plines:
            f_tag = b"/F2 13 Tf" if style == "B" else b"/F1 11 Tf"
            escaped = _pdf_safe_line(txt).encode("latin-1")
            cmds.append(f_tag + b" (" + escaped + b") Tj T*")
        cmds.append(b"ET")
        stream_data = b"\n".join(cmds)
        content_id = add_obj(f"<< /Length {len(stream_data)} >>\nstream\n".encode("ascii") + stream_data + b"\nendstream")
        page_body = (
            f"<< /Type /Page /Parent {pages_id_placeholder} 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_obj} 0 R /F2 {font_bold_obj} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_ids.append(add_obj(page_body))

    kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id_placeholder - 1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_ids)} >>".encode("ascii")
    catalog_id = add_obj(f"<< /Type /Catalog /Pages {pages_id_placeholder} 0 R >>".encode("ascii"))

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def build_csv_bytes(content: str) -> bytes:
    rows = parse_table_rows(content)
    sio = io.StringIO()
    writer = csv.writer(sio)
    for row in rows:
        writer.writerow(row)
    return sio.getvalue().encode("utf-8-sig")


def build_studio_artifact(title: str, content: str, fmt: str) -> tuple[bytes, str, str]:
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise StudioError("Belge başlığı 1–120 karakter olmalı.")
    if not isinstance(content, str) or not content.strip() or len(content) > 250000:
        raise StudioError("Belge içeriği boş olamaz ve 250.000 karakteri aşamaz.")
    fmt = (fmt or "").strip().lower().lstrip(".")
    if fmt not in STUDIO_FORMATS:
        raise StudioError(f"Desteklenmeyen çıktı türü. Seçenekler: {', '.join(sorted(STUDIO_FORMATS))}")
    safe_stem = re.sub(r"[^\w ._-]", "", title.strip(), flags=re.UNICODE).strip()[:64] or "EON-Belge"
    filename = f"{safe_stem}.{fmt}"

    if fmt == "docx":
        return build_docx_bytes(title, content), filename, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if fmt == "xlsx":
        return build_xlsx_bytes(title, content), filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if fmt == "pdf":
        return build_pdf_bytes(title, content), filename, "application/pdf"
    if fmt == "csv":
        return build_csv_bytes(content), filename, "text/csv; charset=utf-8"
    if fmt == "md":
        body = f"# {title.strip()}\n\n{content.strip()}\n".encode("utf-8")
        return body, filename, "text/markdown; charset=utf-8"
    body = f"{title.strip()}\n{'=' * len(title.strip())}\n\n{content.strip()}\n".encode("utf-8")
    return body, filename, "text/plain; charset=utf-8"


def preview_studio_document(title: str, content: str, fmt: str, folder: str = "", allowed_folders: list[str] | None = None) -> dict:
    raw, filename, mime = build_studio_artifact(title, content, fmt)
    target_path = ""
    if folder and folder.strip():
        try:
            resolved, _ = resolve_inside_allowed(str(Path(folder.strip()) / filename), allowed_folders or [], must_exist=False, write_mode=True)
            target_path = str(resolved)
        except ActionError as exc:
            raise StudioError(str(exc)) from None
    parsed_rows = parse_table_rows(content)
    rows_preview = parsed_rows[:10] if (fmt in ("csv", "xlsx") or (len(parsed_rows) >= 2 and len(parsed_rows[0]) >= 2)) else []
    return {
        "title": title.strip(),
        "format": fmt,
        "filename": filename,
        "mime": mime,
        "size_bytes": len(raw),
        "target_path": target_path or f"(Tarayıcı İndirilenler Klasörü) / {filename}",
        "content_preview": content[:800],
        "table_preview": rows_preview,
    }


def save_or_encode_studio_document(title: str, content: str, fmt: str, folder: str = "",
                                   allowed_folders: list[str] | None = None,
                                   confirm: bool = False) -> dict:
    if confirm is not True:
        raise StudioError("Dosya üretimi için önizleme onayı gerekli.")
    raw, filename, mime = build_studio_artifact(title, content, fmt)
    saved_path = ""
    if folder and folder.strip():
        try:
            resolved, _ = resolve_inside_allowed(str(Path(folder.strip()) / filename), allowed_folders or [], must_exist=False, write_mode=True)
        except ActionError as exc:
            raise StudioError(str(exc)) from None
        fd, tmp = tempfile.mkstemp(prefix=".eon-studio-", dir=resolved.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, resolved)
        finally:
            Path(tmp).unlink(missing_ok=True)
        saved_path = str(resolved)
    return {
        "filename": filename,
        "mime": mime,
        "size_bytes": len(raw),
        "saved_path": saved_path,
        "data_base64": base64.b64encode(raw).decode("ascii"),
    }
