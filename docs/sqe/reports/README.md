# Area reports (snapshots)

The final project report is built from the repository documents by `docs/sqe/final_report/build_final_report.py`
(output `docs/sqe/final_report/Project_<rolls>_<section>.pdf`).

The files in `sami/` and `tawassul/` are the Area 2 and Area 3 reports as written on 26 Nov 2026. They are kept as
snapshots with their real screenshots; where they differ from the final report, the final report and the documents
in `src/tests/team/` are current (for example the API suite grew from 260 to 520 tests, the k6 runs were repeated with
limits fixed beforehand, and SonarQube measured V(G) = 6 for `Quota.availability`).

The former team master report, the former Area 1 report and the former defect log were removed on 27 Nov 2026
because they contained results that were not produced by real runs (see the AI-use record, correction note).
