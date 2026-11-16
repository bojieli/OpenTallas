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
