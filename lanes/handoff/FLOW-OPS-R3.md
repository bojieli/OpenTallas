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

## 19:4x 11-23 update
- rt f2156bb449c5 live 19:40:45 on intel2/intel1/epyc2/epyc7/epyc10/epyc11 (3e1a fork-stream fix; DEPTH-PRE+BPC-UNDEF reverted on main f2156). 3e1a2180ccb3 was live 19:27-19:29 and was rolled back to c660 (COORD 19:40).
- epyc8/epyc9 on 70b6, held. Waiters: flowops-rtflip-epyc8d (KV-D29 APPLIED post), flowops-rtflip-epyc9b (c4 tail pid 316706 on epyc9 gone) -> f2156. After both flip: unset MQ_SYNC_HOOK + start ot-tools-follow/catchup timers, post.
- DEPTH-HELD drafted locally: epyc10 lane clone branch flowops-depth-held-1123 commit ef287ff3ec0 (on top of pre-revert main; rebase = re-apply e8e1621+9ede7df+HELD). depth_accepted.json = qfd_tt_ctlm_* / *tt_ctlm* (QC-TTC-RETIME); typed hold list = kit_wave dies.<die>.hold_items. Next: dry-run DEPTH+BPC on KV A2g (epyc8 kv-allfix), QC C1b (epyc7 QC-ALLFIX/rows_c/plan_c1_fix1.json), S81 c7a (epyc9 s81-allfix-int/c7a), post, then re-land.
- Copy slots: OT_TREE_COPY_SLOTS is caller env only (default 2); epyc11=4 needs per-host override file -> planned for DEPTH/BPC cut.
- epyc11 gen_hosts after D29+V4 applies land.

## 19:5x 11-23 update
- rt 8d19c5d78e6d live 19:50:09 (COPY-SLOTS-HOST-1123 on f2156): per-host /var/tmp/ot-tree-copy/SLOTS; epyc11 SLOTS=4 written. Waiters now flowops-rtflip-epyc8e / -epyc9c -> 8d19c5d78e6d. Lane notice posted.
- Still next: DEPTH-HELD+BPC dry-runs on KV A2g / QC C1b / S81 c7a, then re-land; timers after epyc8+epyc9 flip; epyc11 gen_hosts after D29+V4.

## 20:3x 11-23 update
- rt 9b19260c1cde live 20:35 on all hosts except epyc8 (DEPTH-HELD/CAP-CONFIG/DEPTH-PRE/BPC, ADV-IST-PRICE, R8 zero-bit guard, R8 lane fix 356816a). Previous: 356816a53858 20:22.
- epyc8 stays on 70b6 for D29 seal s3; rt 356816a53858 + 9b19260c1cde staged on epyc8 (rsync, sha-verified). Waiter flowops-rtflip-epyc8g (systemd user unit, linger on) flips epyc8 to 9b19260c1cde on KV-D29 APPLIED. epyc9 flipped 19:53.
- After epyc8 flips: systemctl --user unset-environment MQ_SYNC_HOOK; start ot-tools-follow.timer ot-tools-catchup.timer; post.
- Next cut: KV-RRL-EXPORT verifier fix once pushed. test_leaf_cs_depth bind-gate string test fails on plain main (stale literal), not ours.
- epyc11: wrappers + .bashrc localbin done; SLOTS=4; gen_hosts after D29+V4 applies.
- Dry-runs posted: QC C1c 1 HELD (s5_ctl_repair4), KV A2h/S81 c7a 0 reached; BPC PASS (C1b 133/133, S81 out 1218/1218).

## 20:5x 11-23 update
- KV-D29 APPLIED 20:49 -> epyc8 flipped; all 8 hosts on 9b19260c1cde. MQ_SYNC_HOOK unset, ot-tools-follow + catchup timers ACTIVE on intel2 (auto-cut of origin/main resumes).
- Next cut (main 11ca5152455: ADV-PAD-LAUNCH fa21a27c0f3 + OTRUN-ORPHAN 11ca5152455) REFUSED 20:51: hub scratch2 91 GB < 100 GB rail. Follow timer cuts once space is freed; requesters told. KV-RRL-EXPORT verifier fix still not pushed.

## 21:0x 11-23 update
- KV wave rt: no die-level rt pin exists; KV kit tools = bind_rt_follow/KW_BIND_RT on bind of record stamp. Current bind_out (d29 portable_bind, 70b6 stamp) resolves to rt 7f184148 (reset_tree.py differs). Ruling posted: KV-D29 repoints kit_rtl.bind_out to its 9b19 postbind (unit postbind-qwen_kvsys-9b19_1123, epyc8, ETA ~22:00) BEFORE lifting kv3_* hold; then I re-verify with kit_wave.bind_rt_follow from rt/9b19 vs live kit_wave.json (expect 9b19). KV-D29 agent a39af6d5d832f96bd told.
- Follow timer retries the cut each run; hub 96 GB < 100 floor (cleanup running per COORD). Next cut = main head (11ca515 OTRUN-ORPHAN, fa21a27 ADV-PAD-LAUNCH, 8e13dda BIND-EMIT-MEM). Requesters told.
