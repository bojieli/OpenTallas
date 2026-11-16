# FABLE-DIE-QC handoff (owner of WHOLE-DIE physical design quality, QC die)

Started 2026-11-16 07:0x PST. Work dir epyc9 /srv/opentallas-scratch2/claude/fable-die-qc (bin/ scripts, an/ outputs, delta/ plans,
src/ = lane clone, branch claude/fable-die-qc-1116). Client logs intel2 ~/fable-die-qc/.

## Done
- die_sta_related crash fixed in the clone (kit_windows shim had no types; every QC die STA since S3R stopped there) + test.
- First QC die STA result: an/sta_s4k/sta.log (S4k routed clock proof of die-grt0-qc/qc/s4k).
- Raw-reset -> FSTART audit of all 130 types on the S4Q9CBR bound RTL: an/raw/audit_s4q9.json, bin/raw_audit.py.
- S4q9e = S4q9d + landing_local_resets on coll_core, native59, tt_ctlm: delta/zz_s29_qc103_s4q9d_dieqc_rst.json (reference only, NOT bound by me; rows handed to FABLE-FIX-QC-KNEE-HC for the one S4q9e) (+3 sidecars),
  rows lanes/handoff/FABLE-DIE-QC-rows.json.

## Next
See lanes/FABLE-DIE-QC.md.

## State 2026-11-16 08:5x PST
- Branch claude/fable-die-qc-1116 @dd7250845f3 (2 commits: kit_windows shim; kit offset rows mid-range). Gate GREEN 37/37, READY posted.
- RUNNING: S4q9c die chain on epyc2 /srv/opentallas-scratch2/claude/fable-die-qc/chain/qc/s4q9c (script bin/chain_f.sh, event tree treeF =
  v2 tools + qwen_compute copy + S4q9c files; client intel2 ~/fable-die-qc/chain_s4q9c.client.log). CHAIN.log lines: KIT, REG_GRT_TT/FF,
  REG_TTA, REG_STA, LPO, CA_C/CA_D, BIND, STA_C, CHAIN_DONE. Kit stage ~3.5 h.
- When REG_STA is written: (1) rerun die_sta_related from the branch head (mid-range rows) on chain/qc/s4q9c/reg/proof to get kitoffs/kitwin;
  (2) python3 -I bin/clock_rows_delta.py SRC PLAN kitoffs kitwin sta/die_sta_related.json OUT REPORT (rows: tap_offset.per_port_ps,
  tap_window.per_port_ps, seam_ps = ceil10(need + 10)); (3) STA again on OUT: TAP-OFFSET-GATE must PASS; (4) compose on S4q9e
  (delta/zz_s29_qc103_s4q9d_dieqc_rst.json (reference only, NOT bound by me; rows handed to FABLE-FIX-QC-KNEE-HC for the one S4q9e)) and post the DELTA to FABLE-FIX-QC-KNEE-HC as the clock half of the event.
- epyc9 scratch2 is under the ot-run disk floor (45 GB): run new work on epyc2 / epyc7.
- Report: lanes/FABLE-DIE-QC.md. Render: intel2 ~/fable-die-qc/qc_die_s4k.png.

## CODEX 2026-11-16 clock rows from S4q9c (next delta only)
- C die kit completed 10:47:13. Regional TT/FF GRT EXIT0; overflow fields0/0/0, totalcapacity integer wraps negative (INFO). Tap extraction 42256 taps per corner, missing0,313regions/127842nodes.
- REG_STA completed11:09:37. Existing rows TAP-OFFSET FAIL5014/84302; seam need169.18 vs110ps. Raw hold diagnostics are not measured real-view qualification (0 measured pairs).
- The inherited epyc2 src/ was a pre-dd725 tool COPY, still using mean kit offsets, despite the original handoff describing branch-head tools. No active file was patched. Exact approved dd7250845f39500a5e4d6126b7d8690fb286115e loaded separately from bin/die_sta_related_dd725.py; bin/clock_rows_1116.py re-derives mid-range offsets and invokes the existing tap_offset_gate directly on the immutable routed arrivals.
- READY rows epyc2 /srv/opentallas-scratch2/claude/fable-die-qc/delta/clock_c_1116/: clock_rows.json, zz_s29_qc103_s4q9c_clock.json reference full plan, report.json, tap_gate.json, kitoffs_midrange.json. Exact gate before FAIL5014/84302 -> after PASS0/84512;52types/15391ports change; seam110->180 for need169.18;gen_phys tap tables0errors,maxspan724.5ps.0cycles/lanes. Existing per-port window needs preserved (same clock proof and core offsets). Not a full STA rerun or actual-view hold signoff; do not claim those.
- QC parent owns composing these on the next corrected successor after J/final-calendar event. H/J source/plan untouched. Do not add a blocking clock gate beyond the owner academic profile. Existing chain continues count-align analysis; preserve it.

## CODEX notes: optional-null CA pair source fix
- Existing epyc9 Git clone /srv/opentallas-scratch2/claude/fable-die-qc/src was clean on claude/fable-die-qc-1116. Committed/pushed dec8cc442acfcee01c5f3f85fd363db15188ef9e; only tools/die_plan/die_sta_related.py and test_count_align_onemodel.py changed. ca_named_pairs now falls back independently from null src_part/dst_part to src/dst. Opus5.5 trailer.
- New actual planner-row-to-bind regression fails on old code; focused one-model file16/16PASS after fix. Immutable sourcegate logs in epyc9 fable-die-qc/gate_null_pair_before_pytest.log and gate_null_pair_after.log. Initial isolated-Python missing-pytest tool error retained gate_null_pair_before.log; rerun explicitly used installed usersite pytest via python3-I.
- Scoped actual145tap replay + exact2expression patch and analytical3port+1edge candidate remain epyc2 fable-die-qc/delta/ca_pair_diag_1116/. Old planner classified0landed, corrected144; TTinterval[-472.0283,62.5234],FF[-432.6631,30.25]. Proper planner with fixed code must choose final counts. No fullplanner/STA or PNR job launched, no active epyc2source/RTL/plan edits, no candidate adopted. Root/merge_ops owns normal remote gate.
