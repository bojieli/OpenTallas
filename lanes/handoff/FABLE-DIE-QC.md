# FABLE-DIE-QC handoff (owner of WHOLE-DIE physical design quality, QC die)

Started 2026-11-16 07:0x PST. Work dir epyc9 /srv/opentallas-scratch2/claude/fable-die-qc (bin/ scripts, an/ outputs, delta/ plans,
src/ = lane clone, branch claude/fable-die-qc-1116). Client logs intel2 ~/fable-die-qc/.

## Done
- die_sta_related crash fixed in the clone (kit_windows shim had no types; every QC die STA since S3R stopped there) + test.
- First QC die STA result: an/sta_s4k/sta.log (S4k routed clock proof of die-grt0-qc/qc/s4k).
- Raw-reset -> FSTART audit of all 130 types on the S4Q9CBR bound RTL: an/raw/audit_s4q9.json, bin/raw_audit.py.
- S4q9e = S4q9d + landing_local_resets on coll_core, native59, tt_ctlm: delta/zz_s29_qc103_s4q9e.json (+3 sidecars),
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
  (delta/zz_s29_qc103_s4q9e.json) and post the DELTA to FABLE-FIX-QC-KNEE-HC as the clock half of the event.
- epyc9 scratch2 is under the ot-run disk floor (45 GB): run new work on epyc2 / epyc7.
- Report: lanes/FABLE-DIE-QC.md. Render: intel2 ~/fable-die-qc/qc_die_s4k.png.
