# FIX-LEDGER handoff (Opus, started 11-23 01:5x by COORD)

Job: lanes/DIE-FIX-LEDGER.tsv = one row per Fable gap item (FABLE-RC-REVIEW PARTIAL/MISSED/WRONG-CAUSE; later HOTSPOT-GAPS/HOP-GAPS).
Owner rule 6079af4: one comprehensive event per die, no partial apply. Cuts: HEAD r18 12:00, KV D29 14:00, QC V4 14:00, S81 J9 18:00.
Owner deadline = cut - 1 h (HEAD 11:00, KV/QC 13:00, S81 17:00).

Status rules I apply:
- GATED = row passed its own gate (PRE/bind/LATCHECK) and is in this event.
- ROW-DRAFT = named row with a form, targeted at this event (J9/D29(+D30)/V4(+V5)/r18), not yet gated.
- OPEN = no row, partial row, row targeted at J10 (not allowed: S81 has one event), or a reason not yet accepted by Fable.
- REASONED = reason accepted by the die Fable reviewer (FABLE-RC-S81 / -QC / -KVHEAD).

Build script: local scratchpad fl/bin/build.py (mapping per FABLE-RC-REVIEW line number).
v1 02:0x: 98 items. S81 43 OPEN/18 DRAFT/1 REASONED; KV 11/4; QC 3/9; HEAD 4/5. 0 GATED.
Dead-owner candidates: FAM-S81-LEPE-4 (last post 23:36), FAM-S81-DSDV-R1 (19:16). Unknown ids: RANKSEAT-R2, VIS-HEAD.
HOTSPOT-GAPS.tsv / HOP-GAPS.tsv: not landed at 02:0x.
