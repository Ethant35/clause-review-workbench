# Final source review

Author: Ethan.

I reviewed `CONSTRAINTS.md`, the native source inventory/build path, the upgrade harness, the related usability assertion, and the current frontend analysis/policy/sample changes. I found no material defect that blocks proceeding to the remaining qualification gates.

The native inventory change uses the Git index for a repository build, so untracked synced duplicate files and private evidence are excluded. It requires the expected notices, docs and license inventory, and has tests for both a staged repository tree and an extracted source tree. The extracted-tree fallback also limits selection to backend Python, playbooks, docs, licenses and declared root notices. This addresses the prior filename-with-spaces exclusion without broadening the app bundle to tests or evidence.

The upgrade harness preserves its v1.2.0 default and adds a v1.3.0 source baseline pinned to the verified release commit. I checked that commit: it declares version 1.3.0, extraction revision 5 and review revision 4. Current extraction revision remains 5 while current review revision is 5. Therefore the old snapshot should remain historically unverified, but the document can be reviewed again without re-extraction; the new conditional 409/201 expectation follows the extraction revision check in the API. The harness now compares stored review JSON and saved policy/revisions, checks original bytes and prior reviewer decisions, and verifies a new review does not inherit old decisions. This is a source-created prior-release database test, not a migration from the actual public app binary.

The usability assertion now checks the first source card because a related-clause finding can legitimately render several evidence cards. It still checks the first quoted passage against the highlighted source block after the jump. This narrows a Playwright multi-element visibility assertion while retaining the substantive source-link check.

The frontend saves and restores the policy associated with historical reviews, labels the selector for the next review, disables unavailable policies, and selects the highest-priority finding first. The finding-kind label separates missing provisions and unresolved interpretation from configured adverse wording. The sample is visibly synthetic and is a complete workflow example. The source-location foreground colors in the current CSS have measured contrast ratios of 5.52:1 (`#526974` on `#f8fafa`) and 4.69:1 for the action link (`#247d77` on `#f8fafa`), above 4.5:1 for normal text.

No integrated/native harness or provider test was run for this read-only review. The lead owns remaining end-to-end and package qualification.
