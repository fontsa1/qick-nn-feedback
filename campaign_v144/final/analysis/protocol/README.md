# Data-protocol checks

`REPORT.md` is the record of these checks as written on 2026-11-16; the results ledger hashes it, so it is kept unedited.
Read it with these notes:

- **The leakage audit:** the "fixed copy" `verify_no_leakage_fixed.py` it describes is shipped as
  `tools/verify_no_leakage.py` (sha256 d0a47164…). Against the copy that wrote `logs/fixed_verify_no_leakage.log`, only
  its docstring and check labels, its import path and default `--tmp` folder, and one summary line printed when a whole
  set is blocked were changed; the checks are the same.
- **Not shipped:** the older release script (sha256 704b7cad…), the staging scripts (`stage_release_layout.py`,
  `stage_fixed_extra.py`), `logs/audit_script_sha256.txt` and `provenance_sha256.json` named in the logs and the report
  are working files of the build machine.
- **Blocked without the captures:** C5 and G5 read the per-shot captures listed in `DATA_MANIFEST.csv`; without them
  the audit reports those checks BLOCKED.
- **P-numbers** in the report are paragraphs of our draft of that date.
