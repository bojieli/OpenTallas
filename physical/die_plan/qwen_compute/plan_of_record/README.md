# QC die plan of record (DIE-QC-46, 2026-10-30)

- `plan_qc43.json` (sha256 e630ffb8da5e...): the QC plan of record (DIE-QC-43), frozen base of the GRT TRIAL0/TRIAL1 runs.
- `plan_qc45.json` (sha256 2257b9fb1a47...): plan_qc43 plus the plan_qc45 event (results/qc_die46_1030/plan/compose_qc45.py).
  It is the candidate that replaces plan_qc43 once QC-KITS-W has regenerated its types. G0C 155 (0 new vs qc43), strict bind 0.
- `cores/`, `census/` and `macro_pins/` are the plan-relative tables both plans reference (hard-core pin tables etc.).
  They are byte copies of intel2:/srv/opentallas-scratch2/claude/die-qc-46/plan.

`physical/die_plan/qwen_compute/die_plan.json` on main is the old 10-25 plan (0b1fad815a4). For example, its SU VMR
hard core is 259.2x276.48, while the signed view f4kfinal / DIE-QC-44 V1 is 250.56x216. Use the files in this directory.
