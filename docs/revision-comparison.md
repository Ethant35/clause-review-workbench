# Comparing contract revisions

Author: Ethan. October 28, 2026.

Select the earlier document and choose **Upload revision**. Upload a clean TXT,
text-based PDF, or supported DOCX. The app saves a separate original and links it
to the earlier document. Resolve Word tracked changes first. This feature compares
two saved reviews; it does not interpret a pre-marked redline or apply edits.

Run a review of the new upload, then open **Revisions**. Choose the earlier
document and baseline review. The selected main review is the after version.
The comparison uses the policies saved in those reviews, not the current settings.
More documents and earlier reviews can be loaded through the library and selector.

Changed paragraph groups show exact extracted text and locations on both sides.
Moves can appear as deletion plus addition. Formatting, images, Word numbering
and other material outside the extracted text are not compared. Open both
originals when those features matter. Matching extracted text with different
original hashes produces a separate warning.

Findings are compared by rule and by their quoted evidence, including supported
clause interactions. The view distinguishes new, changed, unchanged and no-longer-
flagged results. A no-longer-flagged result does not mean a risk was resolved.
Different saved policies or extraction/analysis revisions are marked as not
directly comparable; their differences cannot be attributed solely to contract edits.

Earlier notes and decisions remain in the earlier review. New reviews always
start with unresolved findings and empty notes. Any change to source bytes,
extracted text, saved policy or checks prompts reconsideration of earlier
decisions, including decisions on apparently unchanged findings. This conservative
rule covers dependencies the recognizers do not model. **Review this finding**
opens the new finding for a fresh decision. It does not modify the earlier one.

The JSON comparison export includes both document IDs/hashes, review IDs, source
changes, finding groups, prior decisions and limitations. It is a snapshot at the
time of export; subsequent reviewer edits require a fresh export. Deleting an
earlier document does not delete its later revision, but removes that baseline
from comparison. The original delete confirmation still applies to its own reviews.

## Fidelity changes

Extraction revision 6 preserves PDF text-block coordinates and DOCX table, row
and physical-cell locations. Physical cells are not logical grid columns when a
table uses merged cells. The app does not resolve table-heading semantics.

PDFs with images, annotations/forms, side-by-side lines or exhausted layout-check
budgets require a visual source comparison before review. Line geometry is checked
even when a PDF extractor groups multiple columns into one block. Confirmation is
the reviewer's assertion, not an automated fidelity guarantee. If text is missing
or in the wrong order, provide a corrected source instead of confirming it.

DOCX automatic numbering, content-bearing headers/footers, special symbols and
linked subdocuments are rejected because body-only text could omit them. Existing
rejections for tracked changes, hidden text, fields, notes and drawings remain.
Use a text-based PDF showing the complete contract, or convert numbering to literal
text. Literal section numbers remain exact; nothing invents missing section labels.

Existing uploads and reviews are preserved. Older extractions must be reprocessed
into a new record before a new analysis. Legacy review comparisons check retained
quoted evidence, but explicitly disclose the absence of a historical full-text
digest. New reviews save both original and extracted-text SHA256 values.

## Research basis and limits

The public [LegalQuants read-redline workflow](https://github.com/LegalQuants/lq-plugin-oss/blob/main/skills/transactional/read-redline/SKILL.md)
emphasizes source preservation, visual reconciliation, and disclosed extraction
gaps. It expressly excludes comparing two clean documents. This app's clean-version
comparison is a separate implementation informed by those principles; it is not a
port, installation or qualification of that skill. No LegalQuants code was copied.

See [External-label evaluation](legal-evaluation.md) for measured detection gaps.
Neither exact text differences nor green software tests establish legal effect.
