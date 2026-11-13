# KIT-STAGE-1 handoff (updated 2026-11-13 03:56 PST)

Brief: COORD 11-13 KIT-STAGE-1 (kit staging failures = 58% of kit-wave FAILs; self-contained kits, CLEAN-2 protection, retry cap, one relaunch batch).

## State
- Branch claude/kit-stage-1-1113@b286608a85 (epyc9 wt /srv/opentallas-scratch2/claude/wt/kit-stage-1), READY posted. NOT deployed: needs merge, then
  ot-autoclean.py -> every host ~/.local/share/ot-autoclean-auto (+ hub kitwave-reduce; new arg --config, default ~/coord/autopilot/kit_wave.json),
  kit_wave.py + kit_store.py -> /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot.
- kit_wave.json (coord-commit): dies.qwen_kvsys.kit_store pilot OFF (kept as kit_store_prev_kitstage1_1113; restore after deploy);
  dies.*.die_owner = DIE-KV-99 / DIE-S81-88 / HEAD-96 / DIE-QC-100 / DIE-HBM-102; backups kit_wave.json.bak-kitstage1-step{1,2}-1113.
- Relaunch batch = KV kv3_pv_* x15 @1 (stale KW-FIX-23 retry entries removed one pass, re-added = re-armed).
- Not relaunched: QC NSC/TOPO rows (all WAIT-FORM held: KW-FIX-46 old floor / HF-1c DIE-QC-100), HBM (parked), HEAD hd_mesh/hd_spn
  (KIT-OPS-1 freeze to 11-15 04:00; prep/assets/sink_bins_4.json only on epyc8; HEAD now on rp19).

## Findings (11-10..13 log): 1,484 FAIL: NSC 440, PRUNED 166, TOPO 116, COLH 86, PLANINV 54, other 622; 3,470 LAUNCH on 501 items.
- COLH (old S81 event, sidecar missing __pv types) and PLANINV (QC whole-plan validation; scope_errors 9a292b1c16) are not live.
- NSC loop driver: host_input_gap relabels to INFRA -> RETRY-INFRA auto relaunch. Retry cap now stops it at 3 same signatures.
- epyc2 qc-transport-fix-4 deletions 02:51 / 03:32: not KIT-STAGE-1 (tests on epyc9 temp roots only). Old ot-autoclean-dx deleted src_sw2 11-12 06:04.

## Next (if resumed)
- After step2 (bpjanouoq): check KIT-WAVE LAUNCH qwen_kvsys/kv3_pv_* lines, post RESULT with counts.
