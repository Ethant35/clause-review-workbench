"""Offline diagnostic against independent CUAD test annotations. Author: Ethan.

No model calls, downloads, threshold tuning, or legal-risk gold labels. Input is
the upstream data.zip, verified before parsing. See docs/legal-evaluation.md.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import yaml
from backend.workbench.engine import analyze
from backend.workbench.models import Playbook
from backend.workbench.parsing import extract, ParseError
from backend.workbench.relations import InteractionLimit
from backend.workbench.safety import EXTRACTION_REVISION, REVIEW_REVISION

ARCHIVE_SHA256 = "f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a"
MAPPING = {"Governing Law": "governing-law", "Cap On Liability": "liability-cap",
           "Anti-Assignment": "assignment", "Termination For Convenience": "termination-convenience"}


def overlap_size(interval, spans):
    start, end = interval
    clipped = sorted((max(start, a), min(end, b)) for a, b in spans if a < end and b > start)
    size, last = 0, start
    for a, b in clipped:
        size += max(0, b - max(last, a))
        last = max(last, b)
    return size


def evaluate(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("CUAD archive hash differs from the documented upstream version")
    with ZipFile(path) as archive:
        data = json.loads(archive.read("test.json"))["data"]
    playbook_bytes = (ROOT / "playbooks/commercial.yaml").read_bytes()
    playbook = Playbook.model_validate(yaml.safe_load(playbook_bytes))
    records, failures = [], []
    counts = {name: Counter() for name in MAPPING}
    for entry in data:
        if len(entry["paragraphs"]) != 1:
            raise ValueError("Unexpected multiple contexts; do not silently select one")
        paragraph = entry["paragraphs"][0]
        context = paragraph["context"]
        qas = {q["id"].rsplit("__", 1)[-1]: q for q in paragraph["qas"]}
        for category in MAPPING:
            for answer in qas[category]["answers"]:
                a = answer["answer_start"]
                if context[a:a + len(answer["text"])] != answer["text"]:
                    raise ValueError(f"Gold span mismatch: {entry['title']} / {category}")
        try:
            document = extract(context.encode())
            issues, checks = analyze(document, playbook)
        except (ParseError, TimeoutError, InteractionLimit) as exc:
            failures.append({"contract": entry["title"], "reason": str(exc),
                             "positive_labels": [name for name in MAPPING if qas[name]["answers"]]})
            continue
        # Map exact extracted lines back to upstream offsets. This mapping
        # changes no whitespace, punctuation, gold labels, or model inputs.
        spans, cursor = {}, 0
        for block in document["blocks"]:
            at = context.find(block["text"], cursor)
            if at < 0:
                raise ValueError("Extracted block cannot be mapped exactly to upstream text")
            spans[block["id"]] = (at, at + len(block["text"]))
            cursor = spans[block["id"]][1]
        by_rule = {c["rule_id"]: c for c in checks}
        for category, rule_id in MAPPING.items():
            gold = qas[category]["answers"]
            related = [issue for issue in issues if issue["rule_id"] == rule_id]
            # COMPLIANT means located text, not a legal correctness label.
            located = by_rule[rule_id]["outcome"] != "NOT_APPLICABLE" and (
                not related or any(not issue["absence"] for issue in related))
            confusion = "TP" if gold and located else "FN" if gold else "FP" if located else "TN"
            anchors = [issue["source_anchor"] for issue in related if issue.get("source_anchor")]
            anchors += [anchor for issue in related for relation in issue.get("interactions", []) for anchor in relation["evidence"]]
            evidence = [spans[a["id"]] for a in anchors]
            coverage = [overlap_size((a["answer_start"], a["answer_start"] + len(a["text"])), evidence) / max(1, len(a["text"])) for a in gold]
            counts[category][confusion] += 1
            counts[category]["gold_spans"] += len(gold)
            counts[category]["gold_spans_half_covered_by_finding_evidence"] += sum(value >= 0.5 for value in coverage)
            records.append({"contract": entry["title"], "category": category, "rule_id": rule_id,
                            "gold_present": bool(gold), "located_by_rule": located, "label_alignment": confusion,
                            "check_outcome": by_rule[rule_id]["outcome"],
                            "absence_finding": any(i["absence"] for i in related),
                            "gold_spans": [{"start": a["answer_start"], "end": a["answer_start"] + len(a["text"]),
                                            "finding_evidence_coverage": value} for a, value in zip(gold, coverage)]})
    return {"author": "Ethan", "dataset_author": "The Atticus Project; Hendrycks, Burns, Chen and Ball",
            "source": "https://github.com/The-Atticus-Project/cuad/blob/main/data.zip",
            "license": "CC BY 4.0", "archive_sha256": ARCHIVE_SHA256,
            "split": "All 102 contracts in upstream test.json, no sampling or tuning on these results",
            "contracts_total": len(data), "contracts_completed": len(data) - len(failures),
            "failures": failures, "category_counts": {k: dict(v) for k, v in counts.items()},
            "playbook_sha256": hashlib.sha256(playbook_bytes).hexdigest(),
            "extraction_revision": EXTRACTION_REVISION, "review_revision": REVIEW_REVISION,
            "engine_sha256": hashlib.sha256((ROOT / "backend/workbench/engine.py").read_bytes()).hexdigest(),
            "limits": ["External labels are independent of this app; this diagnostic and category mapping are implementation-authored.",
                       "Category scope differs: CUAD caps include time limits; anti-assignment asks consent/notice, while the app checks broader assignment wording.",
                       "An FP is a label mismatch, not necessarily an incorrect legal finding; an FN is a review-coverage gap.",
                       "CUAD identifies provisions to review; it does not validate risk priority, enforceability, advice, or exception reasoning.",
                       "Finding-evidence coverage excludes compliant provisions without issue anchors and is not end-to-end extraction recall.",
                       "Text-only benchmark inputs do not test PDF/DOCX fidelity. No independent human reviewed this app's judgments."],
            "records": records}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("contracts_total", "contracts_completed", "failures", "category_counts")}, indent=2))
