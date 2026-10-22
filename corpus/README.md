# Synthetic contract evaluation corpus

This directory contains twelve synthetic commercial contract scenarios and an independently authored expected-results manifest. The manifest was specified from the scenario designs before running the application; it is not copied from application findings. Each agreement keeps each clause in its own paragraph so a finding can point to a stable source block.

The expected results cover only the objective controls listed for each scenario and the supplied playbook rule IDs. `expected_issues` lists planted deviations, while `expected_uncertain` identifies a deliberately ambiguous condition that should not be reported as a confirmed deviation. `compliant_controls` lists the other in-scope controls that should not produce issues. These results measure this synthetic corpus only. They do not establish legal accuracy or performance on real contracts.

The contracts are fictional, written for this project, and contain no personal or customer data. See `manifest.json` for the machine-readable scenario mapping.
