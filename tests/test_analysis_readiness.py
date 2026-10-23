"""Independent regression and metamorphic checks for extraction and analysis."""
from io import BytesIO
from pathlib import Path
import unittest
from zipfile import ZipFile

import yaml
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pymupdf
from hypothesis import given, settings, strategies as st

from workbench.engine import analyze
from workbench.models import Playbook
from workbench.parsing import ParseError, extract
from workbench.safety import EXTRACTION_REVISION, REVIEW_REVISION, review_view


ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = Playbook.model_validate(
    yaml.safe_load((ROOT / "playbooks/commercial.yaml").read_text())
)
CAP_ONLY = PLAYBOOK.model_copy(
    update={"rules": [rule for rule in PLAYBOOK.rules if rule.id == "liability-cap"]}
)


def cap_review(blocks):
    document = extract(("\n\n".join(blocks)).encode())
    issues, checks = analyze(document, CAP_ONLY)
    linked = [
        relation
        for issue in issues
        for relation in issue.get("interactions", [])
        if relation["kind"] == "cap-exception"
    ]
    return document, checks[0], linked


class CapScopeRegression(unittest.TestCase):
    def test_exclusion_of_foregoing_cap_in_another_paragraph_requires_review(self):
        document, check, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "Indemnification obligations are excluded from the foregoing cap.",
            ]
        )

        self.assertEqual("NEEDS_REVIEW", check["outcome"])
        self.assertEqual(1, len(relations))
        self.assertEqual(
            {document["blocks"][0]["id"], document["blocks"][1]["id"]},
            {anchor["id"] for anchor in relations[0]["evidence"]},
        )
        self.assertTrue(
            all(
                document["text"][anchor["start"] : anchor["end"]] == anchor["text"]
                for anchor in relations[0]["evidence"]
            )
        )

    @settings(max_examples=80, deadline=None)
    @given(st.lists(st.integers(min_value=0, max_value=99), max_size=6))
    def test_unrelated_paragraph_insertions_preserve_cap_finding_and_evidence(self, fillers):
        cap = "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months."
        exception = "Indemnification obligations are not subject to the liability cap."
        baseline = [cap, exception]
        blocks = [f"Neutral recital {number}." for number in fillers]
        insert_at = len(fillers) // 2
        expanded = [*blocks[:insert_at], cap, *blocks[insert_at:], exception]

        _, baseline_check, baseline_relations = cap_review(baseline)
        document, expanded_check, expanded_relations = cap_review(expanded)

        self.assertEqual(baseline_check["outcome"], expanded_check["outcome"])
        self.assertEqual("NEEDS_REVIEW", expanded_check["outcome"])
        self.assertEqual(1, len(baseline_relations))
        self.assertEqual(1, len(expanded_relations))
        self.assertEqual(
            {cap, exception},
            {anchor["text"] for anchor in expanded_relations[0]["evidence"]},
        )
        self.assertTrue(
            all(
                document["text"][anchor["start"] : anchor["end"]] == anchor["text"]
                for anchor in expanded_relations[0]["evidence"]
            )
        )
    def test_non_exclusion_in_another_paragraph_is_not_a_cap_exception(self):
        _, check, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "The foregoing cap does not exclude indemnification obligations.",
            ]
        )

        self.assertEqual("COMPLIANT", check["outcome"])
        self.assertEqual([], relations)

    def test_foregoing_limitations_carveout_in_another_paragraph_requires_review(self):
        _, check, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "The foregoing limitations do not apply to either party's indemnification obligations.",
            ]
        )

        self.assertEqual("NEEDS_REVIEW", check["outcome"])
        self.assertEqual(1, len(relations))

    def test_not_subject_to_cap_in_another_paragraph_requires_review(self):
        _, check, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "Indemnification obligations are not subject to the liability cap.",
            ]
        )

        self.assertEqual("NEEDS_REVIEW", check["outcome"])
        self.assertEqual(1, len(relations))

    def test_configured_narrow_exception_stays_compliant(self):
        _, check, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "The liability cap does not apply to fraud or willful misconduct.",
            ]
        )

        self.assertEqual("COMPLIANT", check["outcome"])
        self.assertEqual([], relations)

    def test_exception_list_with_indemnity_scope_requires_review(self):
        document, check, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "The liability cap does not apply to fraud, willful misconduct, or indemnification obligations.",
            ]
        )

        self.assertEqual("NEEDS_REVIEW", check["outcome"])
        self.assertEqual(1, len(relations))
        self.assertEqual(
            {block["text"] for block in document["blocks"]},
            {anchor["text"] for anchor in relations[0]["evidence"]},
        )

    def test_same_block_negated_carveout_cannot_confirm_fee_cap(self):
        document = extract(
            b"Aggregate liability will not exceed Fees paid in the preceding twelve months, "
            b"and indemnification obligations are not excluded from this cap."
        )
        issues, checks = analyze(document, CAP_ONLY)

        self.assertEqual("NEEDS_REVIEW", checks[0]["outcome"])
        self.assertFalse(checks[0]["properties"]["explicit_fee_cap"])
        cap_issue = next(issue for issue in issues if issue["rule_id"] == "liability-cap")
        self.assertEqual(document["blocks"][0], cap_issue["source_anchor"])

    def test_named_exclusion_explanation_uses_readable_category_names(self):
        _, _, relations = cap_review(
            [
                "Each party's aggregate liability will not exceed the Fees paid in the preceding twelve months.",
                "Indemnification obligations are excluded from the foregoing cap.",
                "Indemnification liability is capped at $1,000,000.",
            ]
        )

        explanation = relations[0]["explanation"]
        self.assertIn("separate limit", explanation)
        self.assertIn("indemnification", explanation.lower())
        self.assertNotIn(r"indemn\w*", explanation)


class ExtractionLayoutRegression(unittest.TestCase):
    @settings(max_examples=120, deadline=None)
    @given(st.binary(max_size=2048))
    def test_arbitrary_small_inputs_fail_safely_or_return_exact_spans(self, payload):
        try:
            extracted = extract(payload)
        except ParseError:
            return

        self.assertEqual(
            "\n\n".join(block["text"] for block in extracted["blocks"]),
            extracted["text"],
        )
        self.assertTrue(
            all(
                extracted["text"][block["start"] : block["end"]] == block["text"]
                for block in extracted["blocks"]
            )
        )

    def test_nested_docx_table_text_is_retained_in_document_order(self):
        source = Document()
        source.add_paragraph("Before table.")
        outer = source.add_table(rows=1, cols=1)
        cell = outer.cell(0, 0)
        cell.paragraphs[0].text = "Outer table term."
        nested = cell.add_table(rows=1, cols=1)
        nested.cell(0, 0).text = "Nested table exception."
        source.add_paragraph("After table.")
        payload = BytesIO()
        source.save(payload)

        extracted = extract(payload.getvalue())

        self.assertEqual(
            ["Before table.", "Outer table term.", "Nested table exception.", "After table."],
            [block["text"] for block in extracted["blocks"]],
        )

    def test_hidden_character_style_cannot_enter_analysis_as_visible_text(self):
        source = Document()
        base = source.styles.add_style("HiddenBase", WD_STYLE_TYPE.CHARACTER)
        base.font.hidden = True
        hidden = source.styles.add_style("HiddenClause", WD_STYLE_TYPE.CHARACTER)
        hidden.base_style = base
        paragraph = source.add_paragraph()
        paragraph.add_run("Visible provision. ")
        secret = paragraph.add_run("Hidden liability exception.")
        secret.style = hidden
        payload = BytesIO()
        source.save(payload)

        with self.assertRaisesRegex(ParseError, "hidden text"):
            extract(payload.getvalue())

    def test_hidden_default_run_formatting_cannot_enter_analysis(self):
        source = Document()
        defaults = source.styles.element.find(qn("w:docDefaults"))
        run_defaults = defaults.find(qn("w:rPrDefault"))
        run_properties = run_defaults.find(qn("w:rPr"))
        if run_properties is None:
            run_properties = OxmlElement("w:rPr")
            run_defaults.append(run_properties)
        run_properties.append(OxmlElement("w:vanish"))
        source.add_paragraph("Text rendered hidden by document defaults.")
        payload = BytesIO()
        source.save(payload)

        with self.assertRaisesRegex(ParseError, "hidden text"):
            extract(payload.getvalue())

    def test_hidden_default_paragraph_and_character_styles_are_detected_without_style_refs(self):
        paragraph_default = Document()
        paragraph_default.styles["Normal"].font.hidden = True
        paragraph_default.add_paragraph("Hidden by default paragraph style.")
        paragraph_payload = BytesIO()
        paragraph_default.save(paragraph_payload)

        character_default = Document()
        character_default.styles["Default Paragraph Font"].font.hidden = True
        character_default.add_paragraph("Hidden by default character style.")
        character_payload = BytesIO()
        character_default.save(character_payload)

        for payload in (paragraph_payload.getvalue(), character_payload.getvalue()):
            with self.subTest(payload=payload[:24]), self.assertRaisesRegex(ParseError, "hidden text"):
                extract(payload)

    def test_pdf_layout_pair_budget_is_never_exceeded(self):
        from workbench.parsing import _inspect_pdf_layout

        blocks = [
            (0.0, 0.0, 10.0, 10.0, "text", 0, 0)
            for _ in range(450)
        ]

        found, comparisons, limited = _inspect_pdf_layout(blocks, 100_000)

        self.assertFalse(found)
        self.assertLessEqual(comparisons, 100_000)
        self.assertTrue(limited)

    def test_docx_comments_are_disclosed_as_not_analyzed(self):
        source = Document()
        source.add_paragraph("Visible operative text.")
        payload = BytesIO()
        source.save(payload)

        commented = BytesIO()
        with ZipFile(BytesIO(payload.getvalue())) as original, ZipFile(commented, "w") as updated:
            for entry in original.infolist():
                updated.writestr(entry, original.read(entry.filename))
            updated.writestr(
                "word/comments.xml",
                b'<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                b'<w:comment w:id="0"><w:p><w:r><w:t>Reviewer comment contains an exception.</w:t></w:r></w:p></w:comment>'
                b'</w:comments>',
            )

        extracted = extract(commented.getvalue())

        self.assertTrue(any("comment" in warning.lower() for warning in extracted["warnings"]))

    @settings(max_examples=60, deadline=None)
    @given(
        st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ,.-", min_size=1, max_size=100).filter(str.strip),
            min_size=1,
            max_size=12,
        )
    )
    def test_docx_extraction_roundtrips_generated_paragraphs(self, paragraphs):
        source = Document()
        for paragraph in paragraphs:
            source.add_paragraph(paragraph)
        payload = BytesIO()
        source.save(payload)

        extracted = extract(payload.getvalue())

        self.assertEqual(paragraphs, [block["text"] for block in extracted["blocks"]])
        self.assertEqual("\n\n".join(paragraphs), extracted["text"])
        self.assertTrue(
            all(
                extracted["text"][block["start"] : block["end"]] == block["text"]
                for block in extracted["blocks"]
            )
        )

    def test_docx_table_terms_keep_body_order_and_exact_offsets(self):
        source = Document()
        source.add_paragraph("Opening provision.")
        table = source.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Left cell term."
        table.cell(0, 1).text = "Right cell term."
        source.add_paragraph("Closing provision.")
        payload = BytesIO()
        source.save(payload)

        extracted = extract(payload.getvalue())

        self.assertEqual(
            ["Opening provision.", "Left cell term.", "Right cell term.", "Closing provision."],
            [block["text"] for block in extracted["blocks"]],
        )
        self.assertTrue(
            all(
                extracted["text"][block["start"] : block["end"]] == block["text"]
                for block in extracted["blocks"]
            )
        )

    def test_pdf_page_blocks_retain_page_identity_and_exact_offsets(self):
        source = pymupdf.open()
        for text in ("First page condition.", "Second page exception."):
            page = source.new_page()
            page.insert_text((72, 72), text)
        payload = source.tobytes()
        source.close()

        extracted = extract(payload)

        self.assertEqual([1, 2], [block["page"] for block in extracted["blocks"]])
        self.assertEqual(
            ["First page condition.", "Second page exception."],
            [block["text"] for block in extracted["blocks"]],
        )
        self.assertTrue(
            all(
                extracted["text"][block["start"] : block["end"]] == block["text"]
                for block in extracted["blocks"]
            )
        )

    def test_pdf_side_by_side_text_warns_that_order_needs_visual_review(self):
        source = pymupdf.open()
        page = source.new_page(width=612, height=792)
        page.insert_textbox(
            pymupdf.Rect(40, 60, 280, 500),
            "Section 4. Liability\nEach party liability will not exceed 100.\nIndemnification applies to third-party claims.",
            fontsize=12,
        )
        page.insert_textbox(
            pymupdf.Rect(330, 60, 570, 500),
            "Section 5. Other Terms\nPayment is due in 30 days.\nConfidentiality lasts five years.",
            fontsize=12,
        )
        payload = source.tobytes()
        source.close()

        extracted = extract(payload)

        self.assertTrue(any("side-by-side" in warning.lower() for warning in extracted["warnings"]))

    def test_pdf_annotations_are_disclosed_as_not_analyzed(self):
        source = pymupdf.open()
        page = source.new_page()
        page.insert_text((72, 72), "Visible operative text.")
        page.add_text_annot((72, 100), "Reviewer comment contains a proposed exception.")
        payload = source.tobytes()
        source.close()

        extracted = extract(payload)

        self.assertTrue(any("annotation" in warning.lower() for warning in extracted["warnings"]))


class ReviewRevisionRegression(unittest.TestCase):
    def test_old_review_is_labeled_without_rewriting_its_decision(self):
        stored = {
            "review_revision": REVIEW_REVISION - 1,
            "extraction_revision": EXTRACTION_REVISION,
            "issues": [{"rule_id": "liability-cap", "status": "accepted", "notes": "Existing note."}],
            "playbook_snapshot": {"rules": []},
        }

        visible = review_view(stored)

        self.assertEqual("HISTORICAL_UNVERIFIED", visible["verification_status"])
        self.assertIn("current clause interaction checks", visible["verification_warning"])
        self.assertEqual("accepted", visible["issues"][0]["status"])
        self.assertEqual("Existing note.", visible["issues"][0]["notes"])
        self.assertEqual("accepted", stored["issues"][0]["status"])

    def test_older_extraction_requires_reupload_warning(self):
        visible = review_view(
            {
                "review_revision": REVIEW_REVISION,
                "extraction_revision": EXTRACTION_REVISION - 1,
                "issues": [],
                "playbook_snapshot": {"rules": []},
            }
        )

        self.assertEqual("HISTORICAL_UNVERIFIED", visible["verification_status"])
        self.assertIn("Re-upload the original", visible["verification_warning"])

    def test_current_revision_does_not_show_historical_warning(self):
        visible = review_view(
            {
                "review_revision": REVIEW_REVISION,
                "extraction_revision": EXTRACTION_REVISION,
                "issues": [],
                "playbook_snapshot": {"rules": []},
            }
        )

        self.assertEqual("CURRENT_CHECKS", visible["verification_status"])
        self.assertIsNone(visible["verification_warning"])

if __name__ == "__main__":
    unittest.main()
