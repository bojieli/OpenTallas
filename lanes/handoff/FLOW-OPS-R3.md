# FLOW-OPS-R3 handoff (Opus 5.5), updated 2026-11-23 ~16:4x PST

Lane clone: epyc10 /srv/opentallas-scratch2/claude/FLOW-OPS-R3/repo (helper clones repo_anchor, repo_stale, repo_rekey, repo_sitegrid).

## Landed today (main)
- 767ad7f34e7 per-type verilog_defines (type_define_effect.py; OT_BIND_TYPE_DEFINES warn default, =on realizes + fails closed).
- 177ad9e6457 CTS-DPL-DIAMOND-1123 (grt183_make.sh, wave kits).
- 60ec1be1e499 CTS-DPL-DIAMOND-1123b: tools/orfs_dpl_diamond.py in run_abi3_physical.py (ref_tile / closure_loop hard flow; btab_s4r). FAM-QC-HCST-R3 told to rerun btab_s4r/s4rB.
- bacf9b6248a CLAND-FFKEY-CLAMP-1123 (+ cland_ffkey_clamp.py census).
- 4a4ce3b89b26 REVIEW-REQUIRED-KEEP-1123: marker apply keeps review_before_route.required (HEAD r18g unblock).
- 6ca14d0fb59b TOOLROOT-1123: tool_root.py + PRE class TOOLROOT.
- Codex: 82775f07a3f ADV-CELLCAP, 5eef1b26275 reset_anchor re-record.

## In flight (helpers)
- ANCHORDRY PRE (anchor_dry.py + plan_gate_pre), rebasing onto 5eef1b26275, for S81 compose 17:30.
- BIND-REPORT-STALE-1123 (remove old bind_report.json at start; readers fail on report mtime < run start), ETA 18:00.
- CLAND-CTL-REKEY A/B on kv3_hroot (flag OT_CLAND_CTL_REKEY, per-type opt-in if off shortens leg, 0 new findings), report 18:30.
- ADV-SITEGRID PRE (macro/bank origins on site/row lattice, all dies), ETA 20:00.

## Open (original scope)
- GPL -overflow 0.2 default branch + family count (flip after S81-LEAF-J9 t14 a1 gain).
- Missing views restore + hourly canary: S81 dsfd_coll_lane_e/w, KV qkd_hr_core_tx / qkd_hr_cdc_ch; QC coll_ftc ODB/DEF gone.
- GRT-0273 -apply_ndr at CTS (S81 leaf, col_h9_r0, serdes rck, QC st_a).
- rt snapshot refresh after each main push (check hook).
- Define census rerun on S81 Wave A / D29 / V4 candidates; ruling: warn default, composed gates set OT_BIND_TYPE_DEFINES=on.
- Optional: bind_emit_par.json should record failing type + unapplied count (emit A/B: no merge loss).

## 11-23 18:5x update (FLOW-OPS-R3)
Landed on main: GENDRY 9f3deddc069; LANDREMAP-TREE-FAIL + SHIFT 08da0a07542; EMIT-HEARTBEAT c66090747375; BPC-UNDEF-FATAL 9ede7df1b32d.
rt: c66090747375 flipped 18:40 on intel2/intel1/epyc2/epyc7, epyc11 at 18:46. epyc8, epyc9 and epyc10 are held on 70b6 until their unpinned gates clear: KV S1b PRE/G0, the c4 tail on E9 (pid 316706), and the slice PRE (pid 152436). intel2 units flowops-rtflip-{epyc8,epyc9,epyc10} flip each host and post RT-FLIP; logs are in FLOW-OPS-R3/tmp/rt_hold_flip_<h>.log.
OPEN:
- After all three hosts flip, restart the timers on intel2: `systemctl --user unset-environment MQ_SYNC_HOOK; systemctl --user start ot-tools-follow.timer ot-tools-catchup.timer` (BPC 9ede7df then goes live).
- EPYC11: it is on the place hosts now (hub 4bbf75ad). Add it to gen_hosts after the KV D29 and QC V4 applies land and the die src snapshots are replicated to it.
- STATION-1BIT-SWEEP was posted; the TSV is intel2 FLOW-OPS-R3/tmp/station1bit_sweep.tsv. COORD to rule on the 6 running R6V3 route jobs.
