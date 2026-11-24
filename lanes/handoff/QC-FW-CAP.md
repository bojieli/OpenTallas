# QC-FW-CAP handoff (narrow lane, COORD 11-23 21:2x; job: QC fw types over the 400k cap)
Work dir: epyc11 /srv/opentallas-scratch2/claude/QC-FW-CAP (census/*.json, *.py). OT_LANE=QC-FW-CAP.
- 21:30 CENSUS posted (hub 5009b025). Added cells are all BUF (repair_design maxwire 100 plus port buffers). Synth has ~1 INV per FF; chain INV (FF.QN->INV->FF.D) is 54-80k per type.
- ROW = store-complement relays. Inside bind_cells ot_dp_dly, stages alternate polarity; names r[k] are kept. Optional: a CPL param on ot_dp_st chains.
- Base: QC-ALLFIX C1c 3b12251bfd6c, plan epyc7 /srv/opentallas-scratch2/claude/QC-ALLFIX/rows_c/plan_c1_fix2s.json. fw types are identical across C1c/C1d.
  Strict: ot-tree-fork kw45/snap_qwen_compute/qwen_compute_v4c4 -> own dir on epyc7. Then a COPY of QC-ALLFIX/bindB3.sh <dir> <plan> <sha12> rows_f16/auth rows_f16/comb rows_b2/ov_red2 rows_b2/ov_r8 <my overlay>.
  The only acceptable PRE FAIL is ROWS-NO-PROOF on 9 sle_sc. Deliver an idempotent overlay and post ROW-REBASED to QC-ALLFIX, cc FABLE-RC-QC.
## 21:52 PST state
- bind.py OT_DLY_CPL commit 45e1fd372c in epyc7 QC-FW-CAP/repo; ot-push-main running (log tmp/push.log).
  Projection (pol_*.json): dly-only alternation saves 22-31k INV per fw type. With st alternation too (not built, it needs a name-safe CPL on ot_dp_st) it would save 62-66k.
  Synth test: 144 -> 16 NOT; bounded equivalence passes.
- Row: epyc7 QC-FW-CAP/row/fw_dly_cpl_row.py (sha 610e5728d3ee, idempotent) adds OT_DLY_CPL to 9 fw types. Output plan_c1_fwcpl.json 0c14d74c49f2 (on C1c 3b12251bfd6c).
- Tree fork epyc7 QC-FW-CAP/cF/tree (fork.log) for the scoped strict. Use a COPY of QC-ALLFIX bindB3.sh with R = the rt that carries 45e1fd.
- Synth-only probe: epyc11 QC-FW-CAP/probe/slw_fw_v1..._cpl (a kit copy; run_kit refuses it with ENV-PROVENANCE, so it runs make synth directly). Log probe/syn_cpl.log.
  The real place/CTS hold probe needs kit_wave private-spec from the cF bind.
