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


def _inspect_pdf_layout(page_blocks, pair_budget):
    """Return side-by-side detection, comparisons used, and budget exhaustion."""
    comparisons = 0
    for index, block in enumerate(page_blocks):
        for other_index in range(index + 1, len(page_blocks)):
            if comparisons >= pair_budget:
                return False, comparisons, True
            other = page_blocks[other_index]
            comparisons += 1
            horizontal_gap = max(block[0], other[0]) - min(block[2], other[2])
            vertical_overlap = min(block[3], other[3]) - max(block[1], other[1])
            smaller_height = min(block[3] - block[1], other[3] - other[1])
            if horizontal_gap > 24 and vertical_overlap >= min(12, smaller_height * 0.15):
                return True, comparisons, False
    return False, comparisons, False


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
                has_annotations = False
                has_side_by_side_blocks = False
                layout_check_limited = False
                layout_pair_budget = 100_000
                for page in pdf:
                    if page.get_image_info():
                        raise ParseError("PDF contains raster images that may contain unextracted terms. OCR is unsupported; provide a text-only PDF or complete DOCX/text copy.")
                    page_rows = []
                    page_blocks = [block for block in page.get_text("blocks", sort=True) if block[6] == 0 and block[4].strip()]
                    has_annotations = has_annotations or bool(list(page.annots() or [])) or bool(list(page.widgets() or []))
                    if not has_side_by_side_blocks and not layout_check_limited:
                        found, comparisons, limited = _inspect_pdf_layout(page_blocks, layout_pair_budget)
                        has_side_by_side_blocks = has_side_by_side_blocks or found
                        layout_pair_budget -= comparisons
                        layout_check_limited = limited
                    for block in page_blocks:
                        if block[6] == 0 and block[4].strip():
                            page_rows.append((block[4].rstrip("\n"), page.number + 1, "paragraph", f"Page {page.number + 1}, block {len(page_rows) + 1}"))
                    rows.extend(page_rows)
                    if not page_rows:
                        empty_pages.append(page.number + 1)
                if empty_pages:
                    # Partial extraction is not silently treated as a complete document.
                    raise ParseError("PDF contains pages without extractable text. OCR is unsupported; provide a complete text-based copy.")
                if has_annotations:
                    warnings.append("PDF annotations, comments, and form fields are not analyzed. Verify the original for additional terms or review context.")
                if has_side_by_side_blocks:
                    warnings.append("PDF contains side-by-side text blocks. Extracted order may differ from visual reading order; verify sections and clauses in the original.")
                if layout_check_limited:
                    warnings.append("PDF layout checks reached their processing limit. Verify visual reading order in the original.")
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
                # Hidden formatting can be inherited from paragraph or run
                # styles. python-docx's paragraph text still returns those
                # characters, so direct-document checks alone can silently
                # present invisible terms as ordinary visible text.
                if "word/styles.xml" in names:
                    styles_xml = fromstring(z.read("word/styles.xml"))
                    defaults = styles_xml.find(ns + "docDefaults")
                    default_run_properties = defaults.find(ns + "rPrDefault/" + ns + "rPr") if defaults is not None else None
                    if default_run_properties is not None and any(
                        element.tag in {ns + "vanish", ns + "webHidden"}
                        and element.get(ns + "val", "true") not in {"0", "false", "off"}
                        for element in default_run_properties
                    ):
                        raise ParseError("DOCX hidden text defaults are unsupported. Supply a visible-text-only copy.")
                    styles = {
                        style.get(ns + "styleId"): style
                        for style in styles_xml.iter(ns + "style")
                        if style.get(ns + "styleId")
                    }
                    default_style_ids = {
                        style.get(ns + "type"): style.get(ns + "styleId")
                        for style in styles.values()
                        if style.get(ns + "default", "false").lower() in {"1", "true"}
                    }

                    def hidden_style(style_id, visited=None):
                        if visited is None:
                            visited = set()
                        if not style_id or style_id in visited:
                            return False
                        visited.add(style_id)
                        style = styles.get(style_id)
                        if style is None:
                            return False
                        run_properties = [style.find(ns + "rPr")]
                        paragraph_properties = style.find(ns + "pPr")
                        if paragraph_properties is not None:
                            run_properties.append(paragraph_properties.find(ns + "rPr"))
                        for properties in run_properties:
                            if properties is not None and any(
                                element.tag in {ns + "vanish", ns + "webHidden"}
                                and element.get(ns + "val", "true") not in {"0", "false", "off"}
                                for element in properties
                            ):
                                return True
                        parent = style.find(ns + "basedOn")
                        return hidden_style(parent.get(ns + "val") if parent is not None else None, visited)

                    style_refs = {
                        element.get(ns + "val")
                        for element in xml.iter()
                        if element.tag in {ns + "pStyle", ns + "rStyle"}
                    }
                    if any(paragraph.find(ns + "pPr/" + ns + "pStyle") is None for paragraph in xml.iter(ns + "p")):
                        default_paragraph_style = default_style_ids.get("paragraph")
                        if default_paragraph_style:
                            style_refs.add(default_paragraph_style)
                    if any(run.find(ns + "rPr/" + ns + "rStyle") is None for run in xml.iter(ns + "r")):
                        default_character_style = default_style_ids.get("character")
                        if default_character_style:
                            style_refs.add(default_character_style)
                    if any(hidden_style(style_id) for style_id in style_refs):
                        raise ParseError("DOCX hidden text styles are unsupported. Supply a visible-text-only copy.")
                if any(e.tag in {ns + "fldSimple", ns + "fldChar", ns + "instrText", ns + "object", ns + "drawing", ns + "pict"} for e in xml.iter()):
                    raise ParseError("DOCX fields, drawings, or embedded objects are unsupported; their visible content may not match extracted text.")
                if any(n.startswith(("word/footnotes", "word/endnotes")) for n in names):
                    raise ParseError("DOCX notes are unsupported. Supply a text-based PDF including all notes.")
                has_comments = "word/comments.xml" in names or any(
                    e.tag in {ns + "commentRangeStart", ns + "commentRangeEnd", ns + "commentReference"}
                    for e in xml.iter()
                )
            doc = Document(BytesIO(data))
            # Preserve XML document order, including paragraphs inside table cells.
            from docx.text.paragraph import Paragraph
            for i, elem in enumerate(doc.element.body.iter(ns + "p"), 1):
                p = Paragraph(elem, doc)
                if p.text.strip():
                    kind = "heading" if p.style and p.style.name.startswith(("Heading", "Title")) else "paragraph"
                    rows.append((p.text, None, kind, f"Paragraph {i}"))
            warnings.append("DOCX anchors use body paragraph order, including tables. Headers and footers are not analyzed; verify the original for additional terms.")
            if has_comments:
                warnings.append("DOCX comments are not analyzed. Verify the original for additional terms or review context.")
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
