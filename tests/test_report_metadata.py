"""Export properties describe the exported artifact, not its template. Author: Ethan."""
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from backend.workbench.reports import export


def test_docx_export_records_current_utc_dates_without_changing_saved_review():
    review = {"id": "saved-review", "created_at": "2020-01-01T00:00:00Z",
              "playbook_name": "Synthetic policy", "ai_status": "NOT_REQUESTED",
              "issues": [], "checks": []}
    saved = deepcopy(review)
    before = datetime.now(timezone.utc).replace(microsecond=0)
    data, _, extension = export(review, {"name": "synthetic.txt", "sha256": "a" * 64}, "docx")
    after = datetime.now(timezone.utc)
    assert extension == "docx"
    with ZipFile(BytesIO(data)) as archive:
        properties = ElementTree.fromstring(archive.read("docProps/core.xml"))
    ns = {"terms": "http://purl.org/dc/terms/", "dc": "http://purl.org/dc/elements/1.1/",
          "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"}
    stamps = [properties.findtext(f"terms:{field}", namespaces=ns) for field in ("created", "modified")]
    assert stamps[0] == stamps[1]
    for stamp in stamps:
        assert stamp.endswith("Z")
        assert before <= datetime.fromisoformat(stamp.replace("Z", "+00:00")) <= after
    assert properties.findtext("dc:creator", namespaces=ns) == "Ethan"
    assert properties.findtext("cp:lastModifiedBy", namespaces=ns) == "Ethan"
    assert review == saved
