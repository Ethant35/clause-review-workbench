"""Content-sniffed extraction. Original bytes are never rewritten."""
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from defusedxml.ElementTree import fromstring
import hashlib
import json
import math
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
    visual_check = {"status": "NOT_REQUIRED", "manifest_sha256": None}
    image_manifest = []
    block_metadata = []
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
                total_image_pixels = 0
                has_page_scale_image = False
                has_clipped_image = False
                for page in pdf:
                    image_info = page.get_image_info()
                    if len(image_manifest) + len(image_info) > 500:
                        raise ParseError("PDF contains too many raster images to verify safely (limit 500).")
                    page_rect = page.rect
                    if image_info and (page_rect.width <= 0 or page_rect.height <= 0):
                        raise ParseError("PDF page has an unsupported size for image verification.")
                    for image in image_info:
                        bbox = image.get("bbox")
                        if not bbox or len(bbox) != 4 or not all(math.isfinite(float(v)) for v in bbox):
                            raise ParseError("PDF contains a raster image with an unsupported or uncertain position. Simplify the PDF and try again.")
                        x0, y0, x1, y1 = map(float, bbox)
                        if x1 <= x0 or y1 <= y0:
                            raise ParseError("PDF contains an invisible or uncertain raster image. Simplify the PDF and try again.")
                        ix0, iy0 = max(x0, page_rect.x0), max(y0, page_rect.y0)
                        ix1, iy1 = min(x1, page_rect.x1), min(y1, page_rect.y1)
                        if ix1 <= ix0 or iy1 <= iy0:
                            raise ParseError("PDF contains a raster image fully outside the page crop. Simplify the PDF and try again.")
                        visible_fraction = ((ix1 - ix0) * (iy1 - iy0)) / ((x1 - x0) * (y1 - y0))
                        if visible_fraction < 0.5:
                            raise ParseError("PDF contains a raster image mostly outside the page crop. Simplify the PDF and try again.")
                        clipped = x0 < page_rect.x0 - 0.01 or y0 < page_rect.y0 - 0.01 or x1 > page_rect.x1 + 0.01 or y1 > page_rect.y1 + 0.01
                        has_clipped_image = has_clipped_image or clipped
                        width, height = int(image.get("width") or 0), int(image.get("height") or 0)
                        if width < 1 or height < 1 or width > 100_000 or height > 100_000 or width * height > 50_000_000:
                            raise ParseError("PDF raster dimensions exceed safe verification limits. Simplify the PDF and try again.")
                        total_image_pixels += width * height
                        if total_image_pixels > 100_000_000:
                            raise ParseError("PDF raster dimensions exceed safe verification limits. Simplify the PDF and try again.")
                        if ((x1 - x0) * (y1 - y0)) / max(1.0, page_rect.width * page_rect.height) >= 0.85:
                            has_page_scale_image = True
                        image_manifest.append({
                            "page": page.number + 1,
                            "bbox": [round((ix0 - page_rect.x0) / page_rect.width, 6), round((iy0 - page_rect.y0) / page_rect.height, 6), round((ix1 - page_rect.x0) / page_rect.width, 6), round((iy1 - page_rect.y0) / page_rect.height, 6)],
                            "raw_bbox_points": [round(v, 3) for v in (x0, y0, x1, y1)],
                            "clipped": clipped,
                            "width": width, "height": height,
                        })
                    page_rows = []
                    page_blocks = [block for block in page.get_text("blocks", sort=True) if block[6] == 0 and block[4].strip()]
                    has_annotations = has_annotations or bool(list(page.annots() or [])) or bool(list(page.widgets() or []))
                    if not has_side_by_side_blocks and not layout_check_limited:
                        # MuPDF can combine separate columns into one block.
                        # Check line geometry as well, without decoding images.
                        layout = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
                        lines = [line["bbox"] for item in layout["blocks"] if item["type"] == 0 for line in item["lines"]]
                        found, comparisons, limited = _inspect_pdf_layout(lines, layout_pair_budget)
                        has_side_by_side_blocks = has_side_by_side_blocks or found
                        layout_pair_budget -= comparisons
                        layout_check_limited = limited
                    for block in page_blocks:
                        if block[6] == 0 and block[4].strip():
                            page_rows.append((block[4].rstrip("\n"), page.number + 1, "paragraph", f"Page {page.number + 1}, block {len(page_rows) + 1}"))
                            block_metadata.append({"bbox_points": [round(float(v), 3) for v in block[:4]]})
                    rows.extend(page_rows)
                    if not page_rows:
                        empty_pages.append(page.number + 1)
                if empty_pages:
                    # Partial extraction is not silently treated as a complete document.
                    raise ParseError("PDF contains pages without extractable text. OCR is unsupported; provide a complete text-based copy.")
                if has_page_scale_image:
                    raise ParseError("PDF contains a page-scale image, which may be a scan with an OCR text layer. OCR completeness cannot be checked; provide a non-scanned text-based copy.")
                if image_manifest:
                    # Images can contain contract terms. A human must compare the
                    # original against extracted text before this upload is usable.
                    canonical = json.dumps(image_manifest, sort_keys=True, separators=(",", ":")).encode()
                    visual_check = {"status": "NEEDS_VISUAL_CHECK", "manifest_sha256": hashlib.sha256(canonical).hexdigest()}
                    warnings.append("PDF contains raster images. OCR and image text checks are unsupported. Image placement does not establish whether a PDF layer or transparency makes an image invisible. Compare the original with all extracted text and verify every listed region; missing terms may change review results.")
                if has_clipped_image:
                    warnings.append("A raster image extends beyond a page crop. Only its visible cropped region is listed; content outside the crop is not analyzed. Compare the original rendered page and extracted text before confirming.")
                if has_annotations:
                    warnings.append("PDF annotations, comments, and form fields are not analyzed. Verify the original for additional terms or review context.")
                if has_side_by_side_blocks:
                    warnings.append("PDF contains side-by-side text blocks. Extracted order may differ from visual reading order; verify sections and clauses in the original.")
                if layout_check_limited:
                    warnings.append("PDF layout checks reached their processing limit. Verify visual reading order in the original.")
                if has_annotations or has_side_by_side_blocks or layout_check_limited:
                    manifest = {"images": image_manifest, "annotations_or_forms": has_annotations,
                                "side_by_side": has_side_by_side_blocks, "layout_check_limited": layout_check_limited,
                                "text_layout": block_metadata}
                    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
                    visual_check = {"status": "NEEDS_VISUAL_CHECK", "manifest_sha256": hashlib.sha256(canonical).hexdigest()}
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
                # Body-only extraction must not silently omit operative text.
                for name in names:
                    if name.startswith(("word/header", "word/footer")) and name.endswith(".xml"):
                        part = fromstring(z.read(name))
                        if any((e.text or "").strip() for e in part.iter(ns + "t")) or any(
                            e.tag in {ns + t for t in ("drawing", "pict", "object", "fldChar", "fldSimple", "altChunk", "sym")}
                            for e in part.iter()
                        ):
                            raise ParseError("DOCX headers or footers contain content that body extraction would omit. Supply a text-based PDF with all terms visible.")
                if any(e.tag in {ns + "sym", ns + "subDoc"} for e in xml.iter()):
                    raise ParseError("DOCX symbols or linked subdocuments cannot be extracted faithfully. Supply a text-based PDF.")
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
                # Automatic numbering is not present in Paragraph.text. Do not
                # invent section labels or silently lose cross-reference targets.
                num = elem.find(ns + "pPr/" + ns + "numPr")
                style = p.style
                visited = set()
                while num is None and style is not None and style.style_id not in visited:
                    visited.add(style.style_id)
                    num = style.element.find(ns + "pPr/" + ns + "numPr")
                    style = style.base_style
                if num is not None:
                    num_id = num.find(ns + "numId")
                    if num_id is None or num_id.get(ns + "val") != "0":
                        raise ParseError("DOCX automatic numbering is unsupported because section labels would be lost. Supply a text-based PDF or convert numbering to literal text.")
                if p.text.strip():
                    kind = "heading" if p.style and p.style.name.startswith(("Heading", "Title")) else "paragraph"
                    location = f"Paragraph {i}"
                    metadata = {}
                    cell = next((a for a in elem.iterancestors() if a.tag == ns + "tc"), None)
                    if cell is not None:
                        row = cell.getparent()
                        table = row.getparent()
                        table_number = list(doc.element.body.iter(ns + "tbl")).index(table) + 1
                        row_number = list(table.iterchildren(ns + "tr")).index(row) + 1
                        cell_number = list(row.iterchildren(ns + "tc")).index(cell) + 1
                        metadata = {"table": table_number, "row": row_number, "cell": cell_number}
                        location += f" · Table {table_number}, row {row_number}, cell {cell_number}"
                    rows.append((p.text, None, kind, location))
                    block_metadata.append(metadata)
            warnings.append("DOCX anchors use body paragraph order, including table cells. Cell order does not establish how headings or merged cells qualify terms; compare the original table.")
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
        if block_metadata:
            blocks[-1].update(block_metadata[i - 1])
        offset += len(text) + 2
    return dict(extraction_revision=EXTRACTION_REVISION, format=fmt, text="\n\n".join(x[0] for x in rows), blocks=blocks, warnings=warnings, visual_check=visual_check, image_manifest=image_manifest)
