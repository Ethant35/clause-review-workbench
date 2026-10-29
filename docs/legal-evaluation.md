# External-label evaluation

Author: Ethan. October 28, 2026.

This is a diagnostic of clause detection against independently authored labels.
It is **not independent legal validation of this app**. No independent lawyer
has reviewed these risk judgments, priorities, negotiating responses or revision
effects. Passing software tests does not fill that gap.

## Source and method

[CUAD](https://www.atticusprojectai.org/cuad/) was created by The Atticus Project,
with annotations made under experienced lawyers' supervision. Its 41 categories
identify provisions for review, not whether a provision is acceptable for a
particular client. Attribution: Dan Hendrycks, Collin Burns, Anya Chen and Spencer
Ball, *CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review*, 2021.
The dataset is distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The diagnostic uses every contract in the publisher's `test.json`: 102 contracts,
with four category mappings fixed before running. There was no sampling, no
recognizer tuning on the results, and no exclusion for low scores. All 102
completed. Exact answer offsets were checked against the upstream text. Source
line positions were mapped without changing annotation text or whitespace.

Upstream archive:
https://github.com/The-Atticus-Project/cuad/blob/main/data.zip

SHA256: `f8161d18bea4e9c05e78fa6dda61c19c846fb8087ea969c172753bc2f45b999a`.
The runner rejects a different archive. The archive remains a local research
input, not an app runtime dependency. It is not sent to a model. No paid calls,
downloads or model requests occur in the evaluation runner.

```sh
.venv/bin/python scripts/evaluate_cuad.py /path/to/data.zip /path/to/results.json
```

Results and per-contract records: `evidence/revisions/cuad-evaluation.json`.
Counts describe this frozen diagnostic, not performance across all contracts.

## Results

| CUAD category | App rule | Labeled present: located / total | Labeled present: missed | Labeled absent: app located / total |
| --- | --- | ---: | ---: | ---: |
| Governing Law | governing-law | 83 / 83 | 0 | 6 / 19 |
| Cap On Liability | liability-cap | 22 / 44 | 22 | 9 / 58 |
| Anti-Assignment | assignment | 62 / 72 | 10 | 5 / 30 |
| Termination For Convenience | termination-convenience | 11 / 29 | 18 | 20 / 73 |

“Located” means the app reported a non-absence finding or matched its configured
conditions. It does not prove that the app found the annotated provision or
correctly interpreted it. In particular, finding a heading or an unrelated use
of a keyword can produce a positive detection. The output therefore also records
overlap of each annotated span with actual finding evidence. At least half of
the annotated span was covered by finding evidence for 45/90 governing-law spans,
20/118 cap spans, 40/137 assignment spans and 1/41 convenience-termination spans.
These are diagnostic evidence-coverage counts, not extraction recall: provisions
that match configured conditions do not receive finding anchors.

The mapping has substantive limits. CUAD caps include time limits for bringing
claims. The app's cap rule mainly targets monetary limits. CUAD anti-assignment
asks about consent or notice; the app scans broader assignment wording. A label
mismatch on an annotated absence therefore is not automatically a false legal
finding. Do not aggregate these into a “legal accuracy” score.

The practical finding is still serious: the current rule set misses relevant
language in public commercial contracts. A missing-provision finding needs a
full source check. “Configured conditions matched” is a pattern-check result,
not an approval of the agreement. The app now uses that phrase in the rule view
instead of presenting the internal `COMPLIANT` token as a legal conclusion.

## What this does not test

- PDF/DOCX extraction, reading order, layout, redlines, or original-file fidelity.
- Completeness or correctness of exception, definition, precedence and
  cross-reference reasoning. CUAD does not supply the needed risk-effect labels.
- Client-specific materiality, party position, enforceability, or current law.
- Generalization beyond these categories and the upstream public test split.

The existing synthetic exception tests demonstrate specified software behavior.
Their expected answers were authored with the implementation and are not an
independent legal-quality benchmark. The external annotation provenance is
independent; the adapter, scoring code and report are implementation-authored.

## Independent legal review protocol

Before claiming legal-quality acceptance, have an independent qualified reviewer
evaluate a separate, permissioned set of complete contracts and clean revisions.
Do not use the above test results for tuning and then describe a rerun as held out.

1. Record the client side, transaction context, policy, governing-law assumptions,
   original hashes, all exhibits, document versions and extraction limitations.
2. Before showing app output, have the reviewer identify operative provisions,
   definitions, exceptions, exceptions to exceptions, separate limits, precedence
   rules and unresolved references. Keep exact source spans and explanations.
3. Record each revision's effect on the earlier conclusion and decision. Include
   changed definitions and remedies while the primary clause remains unchanged,
   deleted exceptions, narrower exceptions, separate caps and changed exhibits.
4. Then compare the frozen app output. Score missed material issues, unsupported
   assertions, incorrect scope, citation coverage and uncertainty separately.
   Preserve disagreements; use another reviewer to adjudicate consequential ones.
5. Keep a reserved set out of fixes. Record the evaluator, date, rubric, exclusions
   and denominators. Do not count a software assertion as a legal judgment.

This protocol is prepared, not executed. No paid reviewer engagement or external
transmission is authorized or initiated by this work.


## 1.5.1 bounded completion pass

The three-axis frozen rubric and software release gates are in
`evaluation/release-contract.json`. No formats or rule categories were added or
withdrawn. The 18 commercial and 6 NDA categories remain the supported screening
scope. Every import, citation, preserved-review and installed-release requirement
remains a software gate; legal-quality acceptance is a separate pending gate.

The previously exposed CUAD test split is now development evidence, not held out.
Two demonstrated misses in the complete CENTRACK hosting agreement were repaired:
an explicit monetary cap beyond the short matching window and an express
without-cause termination right. Negative controls also exposed and now block
negated rights and heading/notice sentences being combined into an acceptable
termination result. This changes matching behavior; saved snapshots are unchanged.
Commercial policy 1.0.1 is added alongside older saved policies on upgrade. Select
it explicitly for new reviews. Analysis revision 6 marks old results historical.

The rerun uses all 102 previously exposed contracts, with no exclusions. Counts
are below; remaining misses and label mismatches are retained, not declared solved.
These counts do not establish precision or recall of legal risk because category
scope differs and independent scope adjudication has not occurred.

| Category | Located / labeled present | Missed | Located / labeled absent |
| --- | ---: | ---: | ---: |
| Governing Law | 83 / 83 | 0 | 6 / 19 |
| Cap On Liability | 29 / 44 | 15 | 10 / 58 |
| Anti-Assignment | 62 / 72 | 10 | 5 / 30 |
| Termination For Convenience | 15 / 29 | 14 | 20 / 73 |

The full new record is `evidence/release-1.5.1/cuad-development.json`; the original
October 28 record is preserved. Do not describe the comparison as independent
held-out improvement. False positives/negatives above are label-alignment terms,
not adjudicated legal errors. No stronger legal-quality claim follows from release.

The downloadable `legal-review-packet-1.5.1.zip` contains the fixed rubric, blank
blind worksheets, one complete exposed CUAD development context, four reserved
complete CUAD contexts outside the exposed test split, two full public Common Paper
cover-and-standard-terms templates, and separate exact-offset external reference
labels. The original/exhibit completeness of CUAD contexts must be verified by a
human before substantive legal acceptance. Common Paper templates have unfilled
business terms; reviewers must not invent client context.

The four reserved cases were selected by a fixed hash rule before fixes, were not
run through the app, and were not used for tuning. They are held out from this
project, not asserted unseen in model training. Reference labels establish only
provision identification. Additional source-reading notes are explicitly provisional
implementer-authored judgments, never independent legal gold. Reviewers see the
blind sources and rubric first, lock judgments, and then compare references/app
output. Consequential disagreements need a second qualified reviewer.

Reproduce the packet locally with `scripts/prepare_legal_review.py` and the pinned
archive. No qualified human reviewer was available/engaged in this session; all
independent legal interpretation, client materiality and enforceability acceptance
remain PENDING. No confidential documents or paid review calls were used.
