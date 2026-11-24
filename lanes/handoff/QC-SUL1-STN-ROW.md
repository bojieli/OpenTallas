# QC-SUL1-STN-ROW handoff (COORD split 11-23 20:5x PST; FABLE-RC-QC eadf2a98)
Job: move 42 su_l1 in-core RSN die lane stations to the street. Base C1c 3b12251bfd6c (epyc7 QC-ALLFIX/rows_c/plan_c1_fix2s.json); FIX3 not landed (QC-ALLFIX applies the script onto C1c+FIX3 for C1d).
- Row script: epyc7+epyc11 /srv/opentallas-scratch2/claude/QC-SUL1-STN-ROW/unbury_sul1.py (77cf42f8f4d9), idempotent. Usage: unbury_sul1.py IN OUT REPORT
- Output C1c+row: plan_c1c_sul1stn.json 6e5430030349 (epyc7 + epyc11 lane dir); report row_sul1stn.json
- 14 type sites (4 types) moved; worst hop 389.5; 0 cycles; only rsn regs_um+note differ.
- Validation: epyc11 lane dir: fork.ot (tree fork of cE/tree from epyc7), chain.sh -> val.sh (PRE, G0, elab, bind --strict --types 4 su_l1), logs val.ot pre.log g0/ elab.log bind.log, summary chain.log.
- TODO: when done, post ROW-REBASED <sha> <result> to QC-ALLFIX cc FABLE-RC-QC-SU, FABLE-RC-QC; report to COORD.
