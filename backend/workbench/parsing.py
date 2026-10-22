"""Content-sniffed extraction. Original bytes are never rewritten."""
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from defusedxml.ElementTree import fromstring
import pymupdf
from docx import Document
from .safety import EXTRACTION_REVISION

MAX_TEXT = 300_000
MAX_BLOCKS = 5000

class ParseError(ValueError):
    pass

def extract(data: bytes):
    rows = []
    warnings = []
    if data.startswith(b"%PDF-"):
        fmt = "pdf"
        try:
            with pymupdf.open(stream=data, filetype="pdf") as pdf:
                if pdf.needs_pass:
                    raise ParseError("Encrypted PDF is unsupported. Supply an unlocked copy.")
                if len(pdf) > 200:
                    raise ParseError("PDF exceeds the 200-page limit.")
                empty_pages = []
                for page in pdf:
                    if page.get_image_info():
                        raise ParseError("PDF contains raster images that may contain unextracted terms. OCR is unsupported; provide a text-only PDF or complete DOCX/text copy.")
                    page_rows = []
                    for block in page.get_text("blocks", sort=True):
                        if block[6] == 0 and block[4].strip():
                            page_rows.append((block[4].rstrip("\n"), page.number + 1, "paragraph", f"Page {page.number + 1}, block {len(page_rows) + 1}"))
                    rows.extend(page_rows)
                    if not page_rows:
                        empty_pages.append(page.number + 1)
                if empty_pages:
                    # Partial extraction is not silently treated as a complete document.
                    raise ParseError("PDF contains pages without extractable text. OCR is unsupported; provide a complete text-based copy.")
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError("Malformed or unsupported PDF.") from exc
    elif data.startswith(b"PK"):
        fmt = "docx"
        try:
            with ZipFile(BytesIO(data)) as z:
                entries = z.infolist()
                if len(entries) > 2000 or sum(x.file_size for x in entries) > 30_000_000:
                    raise ParseError("DOCX expanded size exceeds the processing limit.")
                names = set(z.namelist())
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                    raise ParseError("ZIP file is not a DOCX document.")
                if any("vbaProject" in n for n in names):
                    raise ParseError("Macro-enabled documents are unsupported.")
                for name in names:
                    if name.endswith((".xml", ".rels")):
                        fromstring(z.read(name))  # reject DTD/entity attacks before python-docx
                xml = fromstring(z.read("word/document.xml"))
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                if any(e.tag in {ns + x for x in ("ins", "del", "moveFrom", "moveTo", "moveFromRangeStart", "moveToRangeStart")} for e in xml.iter()):
                    raise ParseError("Tracked changes and moved-text revisions are unsupported. Resolve revisions before upload.")
                if any(e.tag in {ns + "txbxContent", ns + "altChunk"} for e in xml.iter()):
                    raise ParseError("DOCX text boxes or embedded text imports are unsupported. Supply a text-based PDF.")
                if any(e.tag == ns + "sdt" for e in xml.iter()):
                    raise ParseError("DOCX content controls are unsupported. Supply a flattened text-only copy.")
                if any(e.tag in {ns + "vanish", ns + "webHidden"} and e.get(ns + "val", "true") not in {"0", "false", "off"} for e in xml.iter()):
                    raise ParseError("DOCX hidden text is unsupported. Supply a visible-text-only copy.")
                if any(e.tag in {ns + "fldSimple", ns + "fldChar", ns + "instrText", ns + "object", ns + "drawing", ns + "pict"} for e in xml.iter()):
                    raise ParseError("DOCX fields, drawings, or embedded objects are unsupported; their visible content may not match extracted text.")
                if any(n.startswith(("word/footnotes", "word/endnotes")) for n in names):
                    raise ParseError("DOCX notes are unsupported. Supply a text-based PDF including all notes.")
            doc = Document(BytesIO(data))
            # Preserve XML document order, including paragraphs inside table cells.
            from docx.text.paragraph import Paragraph
            for i, elem in enumerate(doc.element.body.iter(ns + "p"), 1):
                p = Paragraph(elem, doc)
                if p.text.strip():
                    kind = "heading" if p.style and p.style.name.startswith(("Heading", "Title")) else "paragraph"
                    rows.append((p.text, None, kind, f"Paragraph {i}"))
            warnings.append("DOCX anchors use body paragraph order, including tables. Headers and footers are not analyzed; verify the original for additional terms.")
        except ParseError:
            raise
        except (BadZipFile, Exception) as exc:
            raise ParseError("Malformed or unsupported DOCX.") from exc
    else:
        fmt = "txt"
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ParseError("Unsupported content. Use DOCX, text-based PDF, or UTF-8 plain text.") from exc
        if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            raise ParseError("Binary content is not a plain-text contract.")
        if text.lstrip().lower().startswith(("<!doctype", "<html", "<?xml", "{\\rtf", "%!ps")):
            raise ParseError("Unsupported markup format. Use UTF-8 plain text.")
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip():
                rows.append((line, None, "heading" if len(line) < 80 and line.isupper() else "paragraph", f"Line {i}"))
    if not rows:
        raise ParseError("Document is empty or contains no extractable text. OCR is unsupported.")
    if len(rows) > MAX_BLOCKS or sum(len(x[0]) for x in rows) > MAX_TEXT:
        raise ParseError("Extracted text exceeds the processing limit (300,000 characters / 5,000 blocks).")
    blocks = []
    offset = 0
    for i, (text, page, kind, location) in enumerate(rows, 1):
        blocks.append(dict(id=f"b{i}", text=text, start=offset, end=offset + len(text), page=page, kind=kind, location=location))
        offset += len(text) + 2
    return dict(extraction_revision=EXTRACTION_REVISION, format=fmt, text="\n\n".join(x[0] for x in rows), blocks=blocks, warnings=warnings)
