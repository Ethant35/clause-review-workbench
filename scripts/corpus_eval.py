"""End-to-end corpus scoring over the real HTTP API, never imports the engine."""
import argparse
import json
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]

def evaluate(base_url, output):
    manifest = json.loads((ROOT / "corpus/manifest.json").read_text())
    results = []
    with httpx.Client(base_url=base_url, timeout=40, trust_env=False) as client:
        for scenario in manifest["scenarios"]:
            path = ROOT / "corpus" / scenario["file"]
            r = client.post("/api/documents", files={"file": (path.name, path.read_bytes(), "text/plain")})
            r.raise_for_status()
            doc = r.json()
            try:
                r = client.post(f"/api/documents/{doc['id']}/reviews", json={"playbook_id": scenario["playbook"]})
                r.raise_for_status()
                review = r.json()
                actual = {c["rule_id"] for c in review["checks"] if c["outcome"] == "ISSUE"}
                uncertain = {c["rule_id"] for c in review["checks"] if c["outcome"] == "NEEDS_REVIEW"}
                expected = set(scenario["expected_issues"])
                expected_uncertain = set(scenario["expected_uncertain"])
                bad_controls = [c["rule_id"] for c in review["checks"] if c["rule_id"] in scenario["compliant_controls"] and c["outcome"] != "COMPLIANT"]
                mismatches = []
                for i in review["issues"]:
                    a = i["source_anchor"]
                    if i["absence"]:
                        valid = a is None and i["observed_language"] is None
                    else:
                        valid = a in doc["blocks"] and doc["text"][a["start"]:a["end"]] == a["text"] and bool(i["observed_language"]) and i["observed_language"] in a["text"]
                    if not valid: mismatches.append(i["id"])
                result = {"scenario": scenario["id"], "expected": sorted(expected), "actual": sorted(actual), "expected_uncertain": sorted(expected_uncertain), "actual_uncertain": sorted(uncertain), "false_positives": sorted(actual - expected), "false_negatives": sorted(expected - actual), "failed_compliant_controls": bad_controls, "citation_mismatches": mismatches, "issues_validated": len(review["issues"])}
                result["pass"] = not any([result["false_positives"], result["false_negatives"], bad_controls, mismatches]) and uncertain == expected_uncertain
                results.append(result)
            finally:
                client.delete(f"/api/documents/{doc['id']}").raise_for_status()
    report = {"author": "Ethan", "scenarios": results, "passed": sum(x["pass"] for x in results), "total": len(results), "false_positives": sum(len(x["false_positives"]) for x in results), "false_negatives": sum(len(x["false_negatives"]) for x in results), "citation_mismatches": sum(len(x["citation_mismatches"]) for x in results)}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8765")
    p.add_argument("--output", default="artifacts/corpus-results.json")
    args = p.parse_args()
    report = evaluate(args.base_url, args.output)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
