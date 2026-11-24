# QC-FW-CAP handoff (narrow lane, COORD 11-23 21:2x; job: QC fw types over the 400k cap)
Work dir: epyc11 /srv/opentallas-scratch2/claude/QC-FW-CAP (census/*.json, *.py). OT_LANE=QC-FW-CAP.
- 21:30 CENSUS posted (hub 5009b025). Added cells are all BUF (repair_design maxwire 100 plus port buffers). Synth has ~1 INV per FF; chain INV (FF.QN->INV->FF.D) is 54-80k per type.
- ROW = store-complement relays. Inside bind_cells ot_dp_dly, stages alternate polarity; names r[k] are kept. Optional: a CPL param on ot_dp_st chains.
- Base: QC-ALLFIX C1c 3b12251bfd6c, plan epyc7 /srv/opentallas-scratch2/claude/QC-ALLFIX/rows_c/plan_c1_fix2s.json. fw types are identical across C1c/C1d.
  Strict: ot-tree-fork kw45/snap_qwen_compute/qwen_compute_v4c4 -> own dir on epyc7. Then a COPY of QC-ALLFIX/bindB3.sh <dir> <plan> <sha12> rows_f16/auth rows_f16/comb rows_b2/ov_red2 rows_b2/ov_r8 <my overlay>.
  The only acceptable PRE FAIL is ROWS-NO-PROOF on 9 sle_sc. Deliver an idempotent overlay and post ROW-REBASED to QC-ALLFIX, cc FABLE-RC-QC.
