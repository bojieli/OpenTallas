# Codex takeover — 2026-10-24 08:54 PDT
All lanes covered. Latest owner signoff: TT setup / FF hold, 833 ps, 60/25 ps, spread <=80 ps. Failed geometry is held before new route.

## COORD-REVIEW-QUEUE
Owner: Codex root. Source: lanes/COORD-REVIEW-QUEUE.md
Current / jobs / next / failures (source snapshot):
tests need docker yosys). Without docker, 23 bind tests fail on the environment, not on the code.
| claude/geom-review8-1023 | 0e0f022b2 | MERGE | d59e42f105 | 14 new verdict records and 6 amended ones. kv3_hub_Ei 383b07 goes FAIL (21:07) -> PASS-COND (23:23) under the quoted COORD 23:22 OWNER DECISION CLOCK. The reviewer re-amended in place, as GR8 did at 21:07. The measured FAIL numbers (TT 342 / FF 288 spread) stay in the reasons text, and the old record is in git at 96c29cfeb. Flag for the coordinator: confirm that owner decision. |
| codex/hbm-token-0936-1023 | 1c729e419 | RECORD-MERGE (missed by the plan) | edcd4f42f8 | FAIL evidence: HBM token rec2 collective transport mismatch. New dir only, nothing claimed as qualified. |
| claude/s81-p9-1023 | 359e63c39 | MERGE | c3ef3b9039 | Plan v4.8: G0 PASS on main, G2 PASS 31 probes (r8eq), LANDED BUNDLES R8 rule plus tests, LPR_ROOT N2 seam bench PASS. The plan file equals the branch's. 7 tools/die_plan files auto-merged without conflict. |
| claude/s81-p9-fc-1023 | 9e40c62fa | MERGE | b55d98264a | fc30 status fault fix: calendar 72 frames 0 fail, probe tt/ff PASS, mutants caught. Adds new tools and evidence only. |
| claude/s81-p9-cf-1023 | 61744766b | RECORD-MERGE, NOT CLOSED | 57e8f36bc2 | crs4p gate 3 FAIL textbook.reset_landing; gate_result.json is committed. |
| claude/core-s81-1023 | cdc5721f0 | RECORD-MERGE | 0ff2bb82e4 | ve r5 closed view, split miters PASS. GEOM-REVIEW8 FAILED the 1442.88-um leaf placement, so the decision is open for S81. The gen_plan_v4 NONFRAME_HC change is in main, but die_plan.json (v4.8) was not regenerated with it. |
| claude/qc-p6-a0v6-1023 | 21cf43d19 | HOLD (carried by QC-A0) | - | See QC section below. Regenerating main's QC plan with the a0v6 gen_plan hook gives G0 FAIL. |
| claude/qc-p6-ftc-1023 | 3a1e9ffa2 | HOLD | - | Pre-ruling (19:17) coll_ftc on tap_mode 'sinks' only. Main's QC plan was later rebuilt by qc-p6-r8/qc-p6-g0c (22:59), and CP1 r8 RULING 21:26 makes grid taps the default (sinks only as additions). A textual merge would mix two generations of a generated die_plan.json. Its tools/die_plan part (kv-p6-tap) is already in main. The GR8 PASS record for coll_ftc g3h is merged. The QC lane must port the coll_ftc tap and station change onto main's gen_plan.py and regenerate. |
| claude/kv-p6-boot-1023 | - | contained | Inside kv-p7 (merged). |
| claude/kv-p6-v37-1023 / kv-p6-pv-1023 | 0ec5c902d | HOLD (superseded) | First-proof PV pad table. KV-P7 states the table was withdrawn (PV_CHECK FAIL 14 on kv39). The plan's "kv-p6-* leave" applies. |
| claude/kv-p3-1023 | 87f498afe | HOLD (superseded) | 0 unique patches; kv-p3b/kv-p3-rtl merged. |
  - main merged with a0v6 (gen_plan.py +3 lines that call a0_core_taps.declare): G0 FAIL, 404 errors, all check=clock, "clock tap ... outside the outline". By type: sle_su_c 82, slw_su_c 82, and 60 each for sle_su_l0, sle_su_l1, slw_su_l0, slw_su_l1. Report: ~/coord/evidence/root-merge/qc-a0v6-on-main_g0_report.json
- WARNING for QC-A0: a34546df17 took the a0v6 gen_plan.py hook and the plan_notes a0_core_taps hunk, but kept main's die_plan.json without regenerating it. The committed plan therefore does not match its generator, and regenerating it gives G0 FAIL as shown above. Before asking to merge: fix the a0_core_taps declaration for the current plan geometry, or drop the hook, then run run.sh and get G0 PASS.

## CP1-R10
Owner: Codex root. Source: lanes/CP1-R10.md
Current / jobs / next / failures (source snapshot):
    r1 120 dropped frame_int_i0 regs + merged frame_int_o1[32]/[238]. => r10a seam numbers miss those bits.
  - ORFS synth of both kits with keep cells (epyc3:~/ot-scratch/cp1-r10/keepsynth): face_guard PASS 6719/6719, 3147/3147.
- r10b kits = r10 plan + new tools (sdc_lint PASS, keep cells): epyc3:~/ot-scratch/cp1-r10b/kits, pids 108292/108293
- 07:5x merged 4b7b2b3e64 (branch 2b5af0700 = origin/main 5f8481bb2 + lane; conflicts with CP2 resolved: sdc_lint accepts
  Tests on epyc3 (docker + venv pytest): die_plan suite main 4 fail -> branch 3 fail (same pre-existing 3: render
- Die step waiters on epyc3 (run die_step_cp1r10.sh after the route kits exit): r10a pid 164429 -> ~/ot-scratch/cp1-r10/die_step.log,
  r10b pid 164430 -> ~/ot-scratch/cp1-r10b/die_step.log. Results: <root>/die/sta_{flat,etm}_{SS,TT,FF}.txt, abut_audit.json.
  back threads. r10a is SUPERSEDED (old tools: face_guard FAIL, seam census incomplete); r10a r1 routed (PIN_AUDIT PASS
- REVIEW (results/geom_review/cp1_r10_pair__cp1_r10__e910d33b3242.json + cp1_r10/*.png): r10b verdict FAIL.
  (1) TOOL BUG: ORFS synth_odb eliminate_dead_logic deleted face regs after Yosys (r1 120, r0 16) -> FIXED + merged
  r10c = r10b + tools 7735347 + clock.tap_mode grid+sinks, tap_max_sinks 1500 (CP1 variant): ~/ot-scratch/cp1-r10c/kits,
         run_kit pids 1613897 / 1613908 (08:4x).
  r10d = r10b + tools only (control): ~/ot-scratch/cp1-r10d/kits, waiter pid 172524 starts both after r10c kits exit.
## OWNER?

## DIE-CI
Owner: Codex root. Source: lanes/DIE-CI.md
Current / jobs / next / failures (source snapshot):
# DIE-CI lane (claude/die-ci-1024, wt localhost:~/wt/die-ci)
## Current step (08:00 PDT)
MERGED to main (de1efdb76c tool, 9d2065c7a2 README, 3b3f7e5834 systemd %h fix). Timers installed + enabled on localhost
via die-ci-nightly.service on epyc2 (/srv/opentallas-scratch2/claude/die-ci; ot-run --mem 340 --priority die).
  localhost:/srv/opentallas-scratch/claude/die-ci/results, commits JSON/MD to branch claude/die-ci-results, keeps a
| s81 | PASS | FAIL 91 hard_cores | FAIL (xdie_io s81 130: copyb_in lk_EN2 missing, S/B host flag) | PASS | PASS |
| s81_head | PASS | PASS | FAIL (same s81 system) | N/A (census none) | FAIL: no s81_head_latency.json |
| qwen_compute | PASS | FAIL 4 ft_budget | FAIL 4 ft_budget | PASS | PASS |
| qwen_kvsys | PASS | FAIL 22 hard_cores | PASS | PASS | PASS (lat_v38s) |
| hbm | PASS | FAIL 121 (core_faces 110, die_io_plan 10, ft_budget 1) | FAIL: xdie_io hbm-ds 961 missing (rack lk_SE0.. vs die_io NW_io..) | PASS | FAIL: no hbm_d4g_latency.json |
- intel2: ~/OpenTallas missing (moved to /srv/opentallas-scratch2/claude/moved/home__ubuntu__OpenTallas, no symlink);
## OWNER?
- Margin values (xtalk MCF=2 bound, OCV 5 %, IR 5 % VDD) are documented assumptions; they make every current seam

## DIE-STA
Owner: Codex root. Source: lanes/DIE-STA.md
Current / jobs / next / failures (source snapshot):
# DIE-STA lane (claude/die-sta-1024, wt localhost:~/wt/die-sta)
## Current step (08:25 PDT)
die_sta.py v1 committed + pushed (ilm / flat / etm modes, compare, replica). Flat capacity replicas running on intel2.
Waiting for CP1-R10 routed kits (r10a epyc3:~/ot-scratch/cp1-r10/kits at GRT; r10b ~/ot-scratch/cp1-r10b/kits) to
## Blocked
  epyc3:~/ot-scratch/die-sta/cp1_die_sta.sh (ilm+flat TT/FF/SS + compare) -> run when r10b r0 has 6_final.*.
  intel2:~/ot-scratch/die-sta/kv): ETM vs flat seam slack off by -82 ps setup (pessimistic) / +73 ps hold (optimistic).
  (SPEF read 55 s of it). N=32/128 running (intel2 ~/ot-scratch/die-sta/rep, nohup pid 258599).
  N=512 (73M inst) running on intel1 /srv/opentallas-scratch2/die-sta/rep512 (ot-run, 260 GB).
- intel2:~/ot-scratch/die-sta/{kv,rep}; bin = copy of die_sta.py.

## ELASTIC
Owner: Codex root. Source: lanes/ELASTIC.md
Current / jobs / next / failures (source snapshot):
Branch claude/elastic-1024 (worktree localhost:~/wt/elastic, removed after merge). No server runs (analysis + 15 s yosys cal on localhost).
## Status: DONE 2026-10-24 07:42 PDT — verdict REJECT (analytical, AGENTS.md step 1); merged main 8e69517bf2 (record only, 0 code/default change)
## OWNER?

## ELEM-HBM
Owner: Codex hbm. Source: lanes/ELEM-HBM.md
Current / jobs / next / failures (source snapshot):
Rule (owner 2026-10-24, AGENTS.md): setup TT / hold FF (std boundary-hold overlay: out min 0, in min -40), 60/25 ps, pin-flop spread <= 80 TT+FF, DRV at TT+FF; SS information only. All routed DBs of closed blocks were on the wiped old fleet -> NEEDS RE-RUN. 'rec TT' = closure_loop metrics.ss_ps (historical key; now published as tt_setup_ps). Paper FAIL = needs re-close; paper PASS still needs re-run + signoff.py (records predate the hold standard / sdc_lint / face_guard). New gen_phys kits run signoff.py automatically at the end of run_kit.sh (KIT/signoff/signoff.json).
### hbm: 55 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 55 (paper FAIL 2, PASS 51, no/incomplete record 2)
- ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x64: NEEDS RE-RUN | rec TT 29.75 FF 13.65 spread TT/FF 117.5/117.7 | kit repo | paper FAIL (recorded TT pin-flop spread 117.5 ps > 80; recorded FF pin-flop spread 117.7 ps > 80)
- ot_hgi_qdq_transport_rslice x16: NEEDS RE-RUN | rec TT 287.66 FF 6.28 spread TT/FF 84.7/80.8 | kit repo | paper FAIL (recorded TT pin-flop spread 84.7 ps > 80; recorded FF pin-flop spread 80.8 ps > 80)
### hbm_b2r2: 51 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 51 (paper FAIL 2, PASS 47, no/incomplete record 2)
- ot_hbm_svc_pc_ctrl_leaf_cfg_h9b x32: NEEDS RE-RUN | rec TT 29.75 FF 13.65 spread TT/FF 117.5/117.7 | kit repo | paper FAIL (recorded TT pin-flop spread 117.5 ps > 80; recorded FF pin-flop spread 117.7 ps > 80)
- ot_hgi_qdq_transport_rslice x8: NEEDS RE-RUN | rec TT 287.66 FF 6.28 spread TT/FF 84.7/80.8 | kit repo | paper FAIL (recorded TT pin-flop spread 84.7 ps > 80; recorded FF pin-flop spread 80.8 ps > 80)
- 2026-10-24 08:22 SM: owner orders applied (TT setup + FF hold sign-off; review before route). epyc2 n-f WC run was killed (ELEM-HBM prefix cancel, exit 137); n-h epyc3, s-f/s-h intel1 WC runs kept as PATHFINDING. Plan-stage reviews PASS-COND: results/geom_review/hnx_rp3lp3h_{n,s}__*-t_plan__*.json (pics review/hnx_rp3lp3h_{n,s}_*/plan.png, context.png). TC kits launched: n-t epyc2:/srv/opentallas-scratch/claude/elem-hbm/kits_sm/hnx_rp3lp3h_n_1938f3904f84-t (hash 65cbb15398c1884e), s-t epyc3:.../kits_sm/hnx_rp3lp3h_s_33365650555c-t (d70b9ba3b263ade2). Branch claude/elem-hbm-sm-1024.
Die-level review of B2r2 (results/geom_review/hbm_plan__hbm_b2r2__c1bc2d0f7ada.json): q_sm*, q_hub and root partition G3 are BLOCKED pending re-floorplan (HBM-ARCH lane file). Core hardening of SM halves / hub cores may continue (outline/pins may change if HBM-ARCH re-pins the hub). Tile review of your running core kits in progress (GR-HBM).
- 2026-10-24 09:15 GEOM-REVIEW tile (GR-HBM; records on claude/geom-review-1024 results/geom_review/, images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-HBM/):
  - bankq0 lanes0_2 = FAIL: pin plan twisted against its partners (see HBM-ARCH note). Fill is 25.7%, 120k cells vs 289k planned because the wrapper ties s_i[767:0]=0 and fst=1: confirm against the parent or the core is not the die function.
  - gq_land = FAIL: 79% empty, pin-limited outline; 612 vm_kq_lo pins on S while the partners are N; ld_* pins face qw_dec.
  - gq_issue = FAIL (plan).
  STOP submitting these three, and any q_hub core, until HBM-ARCH re-floorplans and re-pins the hub (q_hub FAIL).

## ELEM-QK
Owner: Codex qwen. Source: lanes/ELEM-QK.md
Current / jobs / next / failures (source snapshot):
  macro parameter overrides (tools/elem_qk/kit_strip_macro_params.py, logged per kit). Place re-running on intel2.
Rule (owner 2026-10-24, AGENTS.md): setup TT / hold FF (std boundary-hold overlay: out min 0, in min -40), 60/25 ps, pin-flop spread <= 80 TT+FF, DRV at TT+FF; SS information only. All routed DBs of closed blocks were on the wiped old fleet -> NEEDS RE-RUN. 'rec TT' = closure_loop metrics.ss_ps (historical key; now published as tt_setup_ps). Paper FAIL = needs re-close; paper PASS still needs re-run + signoff.py (records predate the hold standard / sdc_lint / face_guard). New gen_phys kits run signoff.py automatically at the end of run_kit.sh (KIT/signoff/signoff.json).
### qwen_compute: 21 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 21 (paper FAIL 2, PASS 17, no/incomplete record 2)
- qfd_dv_lane_h_safe2 x96: NEEDS RE-RUN | rec TT 10.97 FF 6.5 spread TT/FF 82.4/77 | kit repo | paper FAIL (recorded TT pin-flop spread 82.4 ps > 80)
- qfd_dv_s8_station_tail1 x48: NEEDS RE-RUN | rec TT 62.87 FF 16.31 spread TT/FF 84/80.2 | kit repo | paper FAIL (recorded TT pin-flop spread 84.0 ps > 80; recorded FF pin-flop spread 80.2 ps > 80)
### qwen_kvsys: 20 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 20 (paper FAIL 2, PASS 18, no/incomplete record 0)
- qkd_kvs_ctl x1: NEEDS RE-RUN | rec TT 24.38 FF 8.88 spread TT/FF 121.8/109.3 | kit repo | paper FAIL (recorded TT pin-flop spread 121.8 ps > 80; recorded FF pin-flop spread 109.3 ps > 80)
- qkd_kvs_emb x1: NEEDS RE-RUN | rec TT 27.3 FF 13.35 spread TT/FF 149.9/66.7 | kit repo | paper FAIL (recorded TT pin-flop spread 149.9 ps > 80)
  DRC 0. OWNER?/SIGNOFF asked (lanes/SIGNOFF.md) whether ref_tile re-runs can sign or need die-plan re-kit.
- tt_ctlm G3 place: face_guard FAIL (dropped 80, shared 91, feedthrough 61) = P5 bound_r8 vs P6 plan; waits for bound_p6.
- 08:35 PDT reviews PASS (results/geom_review/kv_g3_kv3_io_ft*__elemqk__*.json): io_ft, io_ft_v1 -> FINISH launched intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3b (ot-run 24G/8). sys_c PHY moved to y 250.56 (core margin), place relaunched kvg3d.
- 08:55 PDT main merge (CP1-R10 face_keep hooks + odb face_guard) -> ALL KV kits regenerated: intel2:/srv/opentallas-scratch2/claude/elem-qk/kvg3e (face_guard planned-pins fix re-applied @499a830ac1). Stale-tool runs stopped (my containers only): g3b io_ft/io_ft_v1 finish, intel1 kvg3 pathfinding routes. FINISH running kvg3e io_ft, io_ft_v1 (geometry = reviewed kvg3b, io.tcl identical). PLACE for review: sys_c (kvg3e), io_cor/io_cor_v1 (kvg3b), hroot (kvg3c).
- 2026-10-24 08:28 PDT native59 G3 synth: face_guard FAIL (dropped 34, shared 133, ft 1) - same cause as tt_ctlm (bound_r8 P5 vs P6 plan);
  9 kits failed on harness bugs / missing ~/.local PDK (now present) -> relaunched. Re-runs at closed commit lack the

## ELEM-S81
Owner: Codex s81. Source: lanes/ELEM-S81.md
Current / jobs / next / failures (source snapshot):
- 2026-10-24 08:19 PDT start: batch C = dsfd_cfifo_crs4 (kit s81coll_cfifo_crs4 = plan LEF; crs4p NOT used), dsfd_node_{LLd,LLfd,LLfu,NNfd,NNfu} (s81net_node_*), dsfd_rstg (s81net_rstg); run base /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/ (epyc2/epyc3), src = git archive origin/main fd219eafe7
Rule (owner 2026-10-24, AGENTS.md): setup TT / hold FF (std boundary-hold overlay: out min 0, in min -40), 60/25 ps, pin-flop spread <= 80 TT+FF, DRV at TT+FF; SS information only. All routed DBs of closed blocks were on the wiped old fleet -> NEEDS RE-RUN. 'rec TT' = closure_loop metrics.ss_ps (historical key; now published as tt_setup_ps). Paper FAIL = needs re-close; paper PASS still needs re-run + signoff.py (records predate the hold standard / sdc_lint / face_guard). New gen_phys kits run signoff.py automatically at the end of run_kit.sh (KIT/signoff/signoff.json).
### s81: 37 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 37 (paper FAIL 1, PASS 35, no/incomplete record 1)
- dsdv_gunit_l5 x1: NEEDS RE-RUN | rec TT 20.6 FF 20.07 spread TT/FF 101.9/95.3 | kit repo | paper FAIL (recorded TT pin-flop spread 101.9 ps > 80; recorded FF pin-flop spread 95.3 ps > 80)
### s81_head: 4 closed modules -> SIGNED 0 / NOT SIGNED 0 / NEEDS RE-RUN 4 (paper FAIL 0, PASS 2, no/incomplete record 2)
- 2026-10-24 08:24 PDT reviews written /srv/opentallas-scratch/claude/elem-s81/hc/reviews/<kit>.json (crs4 + 5 nodes PASS-COND: no pre-route images for nodes / crs4 spread margin; rstg PASS); 7 jobs (bench+route+collect via hc/C/tools/cl_local.py = closure-loop ref_tile env reproduced) queued: ot-run --hosts epyc2,epyc3 (both memory-full: 20+ waiters each); local client logs hc/C/logs/<kit>.log
- 2026-10-24 08:25 setup: main fd219eafe7 snapshots per kit at /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/src (localhost: l5_n32 l4 l1c l0r l4r l5f; epyc3: l0 l1 l2 l3); runner hc/bin/route_kit.sh (closure_loop route-stage env reproduced: TC, mm hold + FF SDCs + io_ref_routed, pinflop ref, fp-lint/preroute gate, LEC-off shim).
  epyc3/localhost (kits_head/launch.log). hd_spn/spn_end/serdes/lep0N/mesh/ctl/host BLOCKED on plan sources (posted S81-HEAD).
- 2026-10-24 08:27 PDT attempt 1 of rstg/nnfd/nnfu FAILED at 3_3 global place (flow infra, not design): my minimal source snapshot lacked physical/dsrom_window_source/leaf_iohold.tcl (OT_IOHOLD_IN hook). Snapshot now = tools rtl Makefile + all physical/* except ref_tile (only my 7 kits) at fd219eafe7; relaunched as attempt 2 (failed dirs kept as <kit>.failed_a1.*). Bench judge fixed to closure_loop expected_fail_seen (fail_regex decides; rstg mutant was CAUGHT, my first judge mis-read rc 0)
- 2026-10-24 08:27 setup: snapshot origin/main fd219eafe7 -> per-kit trimmed src (tools rtl physical Makefile minus other ref_tile kits + job extra results paths) at /srv/opentallas-scratch/claude/elem-s81/hc/<kit>/src on localhost, synced to epyc2/epyc3. Runner hc/D_bin/run_stage.sh (closure_loop launch_stage reproduction: TC corner, mm hold, pinflop ref, fp-lint/preroute gate, LEC-off docker shim). Installed missing ~/.local/opentallas-pdk-asap7 on localhost (copy of epyc2's). New fix kit s81hd_spo_m4 (216x216 compact, same fix as spr_m -> spr_m4; spo_m rec spread 78/72.9, ins 708 ps, TT +19.7) generated in hc/s81hd_spo_m4/src (not committed); spo_m re-run in parallel as recorded.
- Frames col_h9_r0_p2/p4/p5/p6 and col_h10_r0_p4 (floorplan only, not placed): **FAIL on inputs** (results/geom_review/col_*__{g3k2|elem}_col_*__<hash>.json; images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81F/<kit>/ (see col_h9_r2__t1/h9_r2_dataflow.png)). Same generator defects as S81's 7 frames (S81.md 09:35): ROM ot_rom_4096x72_m8 cores have no lib (untimed, unbuffered address fan-out); elem_q/bf_col cores (552/645 ps internal latency) on ordinary grid taps; sequencer at the row end. Stop these frame runs until the plan/generator fix lands.
- DISK RULE: col_h9_r0_p5/p6 run from intel2:/srv/opentallas-scratch/claude/elem-s81, which is on intel2's ROOT disk (/dev/nvme1n1p2 /). Use /srv/opentallas-scratch2/claude/ there.
- 2026-10-24 08:29 reviews written (hc/reviews/<kit>.json: eg PASS, 7 PASS-COND, 0 FAIL). dsdv_bksel_q: inventory kit s81dvbk_sq_hq3 never closed; its views are the hk2l closure (9da51c5d14) -> re-run kit s81dvbk_sq_hk2l. Main RTL differs from closure source for selc2/hk2l/xfin(ENG mode, never gated)/capc5r/xrt1 -> benches re-run. Snapshots main fd219eafe7 under /srv/opentallas-scratch/claude/elem-s81/hc/<kit> (epyc2: /srv/opentallas-scratch2/...).
- 2026-10-24 08:29 routes running (ORFS synth/floorplan): epyc3 l0 (detached after ot-run cancel); intel2 l5_n32 l4 l1c l0r l4r; intel1 l5f l1 l2 l3 (localhost/epyc2/epyc3 had no memory admission: 19+ waiters each; intel1/2 used, run dirs /srv/opentallas-scratch/claude/elem-s81/hc/<kit> -> scratch2). l5_n32 bench running intel2. signoff tools = main a2c726e597 (TT-rule signoff.py 70c11a4b18).

## FLEET-DISK
Owner: Codex root. Source: lanes/FLEET-DISK.md
Current / jobs / next / failures (source snapshot):
Merged to main 1ed91ad4ca + 6281884e3d (census resync); ~/.local/bin/ot-run re-installed (v13). Lane DONE except background movers.
- intel1 384G 87% -> 116G 26%   (claude/ FLIPPED -> scratch2; busy: /srv/opentallas-scratch/tok-qw 89G)
- ot-run v13: on hosts with a separate /srv/opentallas-scratch2 (intel1/intel2/epyc2) OT_SCRATCH + new run dirs ONLY on that
- localhost: role normal with HOST_RESERVE 32 threads / 64 GB (coordinator request).
  make check-figures: prose coverage OK; check-headline-bundle + final-number-readiness FAIL identically on main (pre-existing).
## Background (retry every 10 min, never kill/pause anything; logs /srv/opentallas-scratch2/claude/fleet-disk/)
  bind mounts once no container runs for 3 checks (docker stopped ~1 min then; a docker run in that minute would fail).
- 07:41-07:57 my first ot-mvlink used lsof +D only (blind to docker bind mounts). Checked afterwards: no running container

## FLEET-NEW3
Owner: Codex root. Source: lanes/FLEET-NEW3.md
Current / jobs / next / failures (source snapshot):
Merged to main 8a5d1f3dab (branch tip 00a85d87a6), pushed. Lane DONE except OWNER? below.
  linger, cron reconcile */2, scratch /srv/opentallas-scratch/claude + ~/ot-scratch link). localhost role coord
- Tests: test_ot_run_* all OK (spill fixed: tar prefix /usr/bin/tar:). Pre-existing FAIL on main too:
  test_ot_heavy_admit (reconcile selftest v17 HARD_INVARIANT=0 case), test_ot_heavy_v174_replay (1 failure).
OWNER?

## GEOM-REVIEW
Owner: Codex root. Source: lanes/GEOM-REVIEW.md
Current / jobs / next / failures (source snapshot):
Branch claude/geom-review-1024, worktree localhost:/srv/opentallas-scratch/claude/wt/geom-review (base origin/main 4ab1ec1399).
## Current step
08:07 started. 08:55 batch 1 (die level) DONE; merged main f1964316b9 (09:20). 09:05 tile batch running: sub-reviews GR-S81F (S81 + ELEM-S81 frames),
GR-S81S (34 slice_station, S81-CORES vs/vq/hrow + svc hcore, head hd_tile), GR-HBM (ELEM-HBM cores, HBM G2 probes); GR-QK done.
- renders: localhost:/srv/opentallas-scratch/claude/geom-review/
  QC P6 0028ad53 PASS-COND | KV v3.8v bc4edcd4 PASS-COND | HBM B2r2 c1bc2d0f PASS-COND, G3 BLOCKED q_sm*/q_hub/root
- tile (GR-QK): QC A0 v7 NK/NL PASS-COND (pathfinding; equivalence + clock contract) | KV hub_Ei vC FAIL (ft out legs 500-720 um, empty taps) |
## OWNER?

## HBM-ARCH
Owner: Codex hbm. Source: lanes/HBM-ARCH.md
Current / jobs / next / failures (source snapshot):
branch claude/hbm-arch-1024, worktree localhost:~/wt/hbm-arch
## current step
G2 probes on B2r2 running (localhost, sudo docker, 8 cpu each): die (64g), worst-5 parts q_b010/b011/b112/spu0/spu1 (32g),
extra q_su10/b102/b113/b000/su30 (32g), q_hub (160g). Dirs: localhost:/srv/opentallas-scratch/claude/hbm-arch/g2_b2r2/{die,worst,extra,hub}
## OWNER?
- recovered old scratch: localhost:~/ot-scratch/hbm-arch/recovered/
  claude/core-hbm-1023 cores/harden tooling (merged into claude/elem-hbm-1024), plus sdc_lint (pre-synth) + face_guard
Renders: /srv/opentallas-scratch/claude/elem-hbm/review/<view>/{plan,context}.png + stats.json (tool physical/die_plan/hbm_arch_cores/review_core.py on
   pairs): hc_qhub_static 26962 (lg_rq/lg_rr/lg_wq/lg_w_done/rstb_e/wc_e), su_programme_pslice_c5 22235 (command/busy/done/
   Full list: /srv/opentallas-scratch/claude/elem-hbm/away_top.txt and each stats.json partner_checks. Each wraps around the core (+1 core edge of wire).
- HBM B2r2 plan c1bc2d0f (@3277b5e78b): die plan PASS-CONDITIONAL, partition G3 BLOCKED for q_sm*, q_hub, root (record hbm_plan__hbm_b2r2__c1bc2d0f7ada.json, pictures img/hbm_b2r2/zoom_hub2.png, zoom_root2.png, zoom_dense.png). (1) q_sm*: 32 SM-half cores tile the partition 100% (0-um gaps, cores on all 4 edges, glue 0) yet 6 buses / 3,702 b + a tap: show the pin-to-pin abutment design (where face flops, the L28/L29 1,615-b fan-out, CTS and PDN live) or open a glue band along the bus faces. (2) q_hub: 76 cores shelf-packed with 0-5 um gaps, flush on W/S faces, empty N band, tap on a macro, 80k bus bits: re-floorplan data-flow ordered with channels + macro-free face-flop bands. (3) root: core stack in the lower half with the upper half empty, while L4 (2,816 b) / L22 cross the macro wall - the die's hottest bin (9 kb/100 um at 12.55,6.25 mm): open a straight ft channel (move cores up), declare regs_um. (4) q_su30/su10/su31/su01: 558 ft station points inside cores -> regs_um. (5) hops already at 0.85 of reach: re-check after (3)/(4). Twist / IO / symmetry clean.
- 2026-10-24 09:15 GEOM-REVIEW tile follow-up (sub-review GR-HBM; records results/geom_review/q_hub__die_plan.json__c1bc2d0f7ada.json and the core records on claude/geom-review-1024; picture localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-HBM/hub/hub_flow.png): **q_hub = FAIL**. Measured against your own core_conns: of 298k core-to-core bits, 81% run > 1 mm and 65% > 2 mm. Worst: wbk<->hb_dbk 2x2,312 b at 3.8 mm, pgp->sucore 2,470 b 3.7 mm, xl_ctl->aq 2x2,048 b 3.7 mm, vmks_Q3<->ctl_p13-15 5 mm, xq_p1_eg/bd pair 2.5 mm apart. These are pin-registered core-to-core links that cannot close in one 833-ps cycle. The 0-overflow hub G2 probe has no core-to-core nets, so it gives false comfort: add the core_conns links to it. Required: a data-flow-ordered q_hub floorplan (cluster by link weight, partners adjacent, channels + face-flop bands), re-derived core pin faces (gq_land/gq_issue are crossed against hcollks/hcollrs), then G2 with core-to-core nets.
  Also from tile review: (a) split-piece pin tables were never checked against partners (344 cores without core_conns, none for q_sm). bankq0 lanes0_2 FAILs: the lane outputs leave through the W face to the partition edge, while the bank piece takes them on S/E and puts 2,048-b sum_out on the N face toward the lanes. Expect the same in tkm / pgslice / sfu split3 / idx score: supply connectivity and re-run core_faces before ELEM-HBM hardens them. (b) SM halves: 2,069-b bin fan-out from the neighbour n-half bout (y 1047-1544) to the s-half bin (y 629-1026) is a ~420-um vertical jog per bit over abutted macros with no channel, at 7 seams x 2 rows x 8 partitions. gout 200 b abuts gin 100 b (width mismatch). Align the windows or reserve an over-core layer budget (OWNER? if a rule change).

## KV-G3
Owner: Codex qwen. Source: lanes/KV-G3.md
Current / jobs / next / failures (source snapshot):
- hub_Ei 4_cts (placement RC, old-gate kits = pathfinding): pair-skew CPPR TT/FF: vA 173.7/146.8 FAIL, vB 140.1/125.9 FAIL, vC (grid+sinks r250 cap1500) 79.1/72.7 PASS; face spread vC TT 76.5 / FF 68.0. STA TT WNS -679 (hp_fault_1052 plan-cell OR of N-face dcal_flt + W-face ahub_hf, 2.2 mm unregistered), recovery -162.7 (single u_rst_sync -> fixed by kit_rsync).
- Gated kit (main 4b7b2b3e64 sdc_lint/face_guard + kit_rsync, vC clock): intel2:/srv/opentallas-scratch2/claude/kv-g3/g4/vC/kv3_hub_Ei via ot-run (64G/16t).
- Old vA-vE (intel2:~/scratch/kv-g3/g3, ROOT DISK) still running to route = pathfinding only; move to scratch2 after they finish.
## OWNER?/COORD
  their bound RTL differs and a plan merge FAILS G0 R8 (7 errors; r1/r3/r5 alone: 4 errors): kvs_attn.acal_<Q> added
  5 -> 3 hg kits IF the R8 acal/o_kg per-row delay is resolved: OWNER? either the acal/o_kg arrival is made uniform
Recommendation: keep r1..r5 separate (or merge only via the per-instance-parameter route: one netlist with the kg pad depth as a boot/strap parameter is a rule change -> OWNER? only if kit count matters; numbers above).
- MERGED main fd219eafe7: plan v3.8v (hub_Ei fault-OR plan cells FIRM at W face + internal stations: i_dcal_flt 3 (hop 556), i_hp_fault_N_q 2 (hop 504); L357 +3, L758 +2; G0 PASS 0/1788, G0C PASS 0 err; R8 table r8/ unchanged), tools/die_plan/kit_istations.py (+test) realising plan internal_stations/plan-cell sites in bound kits (gen_phys copies istations.tcl, face_flops.tcl sources it).
- Review: die render g3/review/die_v38v.png (N-half vertical ft bundles x 3.3-3.8 / 6.8-7.6 mm + central spine = die channel hot spot), type render g3/review/hubEi_plan_v38v.png: 24/229 ft hops > 675 um (max 727, N->W L slots) = OWNER? 1. Record results/geom_review/kv3_hub_Ei__kvg3v38v_38f97e0c8749.json (AUTHOR PASS-COND). GEOM-REVIEW: please second-review.
- vD (grid300) CTS pair skew TT 91.0 / FF 79.3 -> FAIL (WNS TT -648 / WHS -100.5). vC remains the clock choice.
- Runs (intel2 scratch2 /srv/opentallas-scratch2/claude/kv-g3/g4, ot-run 64G/16t): vC (gated, v3.8s, pathfinding for the fault leg) at CTS; vF = vC + MAX_ROUTING_LAYER M9 + die M8/M9 PG (prices OWNER? 1) at CTS; vG = gated v3.8v kit (kit_rsync + kit_istations) = the candidate, at floorplan.
- 08:3x COORD retraction noted: e5e6 seam PASSES at sign-off TT/FF (TT setup +93.7, FF hold +231.0, spread 24.8/20.1); SS -100.8 is info only. OWNER? 1 now rests on hub_Ei TT evidence only (ft hops 675-727 um on <= M7: TT -44 ps at CTS/placement RC); vF (M8/M9 ft) and vG route will confirm or drop it.
- KV plan v3.8v bc4edcd4 (main; v3.8u geometry identical): PASS-CONDITIONAL (record qwen_kvsys_plan__kv_v38u2__bc4edcd42be7.json). G0/G0C PASS re-run. MAIN FINDING: 1,394 of 4,359 interpolated ft station points land INSIDE hard cores (hgi_v7 252, hgi_v4 240, pv_v4 96, pv_v6 88, ...): the trunk at x~4.8 mm and the hgi rows run over the macro fields, so kits move the stations and hops grow - plan-level cause of your 728-um ft hops (TT -44) and DIE-STA e5e6 -100.8. Before more hgi/pv/hub G3: declared regs_um in core-free channels (or a reserved vertical ft channel next to the trunk), kits honour them; ties to your OWNER? 1. hub_Eo/Wo full bit reversals (1119/300/292 b) are between disjoint windows -> free, OK. hub_Ei vC + 16 core kits tile review running (GR-QK).
- 2026-10-24 09:05 GEOM-REVIEW tile: hub_Ei vC (g4, 4_cts) = FAIL -> stop submitting vC beyond its GRT congestion number (record kv3_hub_Ei__kv3_hub_Ei__5b1cae686903.json, image localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-QK/hub_Ei_vC/review.png). All 5,617 pins with reg > 100 um are ft*_o out pins: last station 500-720 um inside, leg unregistered on <= M7 (pin->reg p90 571 um, gate 30); 15/54 taps have no sinks, clk_t31 > 290 ps; hp_fault 2.2-mm leg (fixed only in v3.8v). For vG/vF: ft out stations at the out face (<= 30 um) and station spacing per the M8/M9 ruling, regs_um in core-free channels (die finding above), empty taps removed. Review vG before it routes.

## KV-TOK
Owner: Codex qwen. Source: lanes/KV-TOK.md
Current / jobs / next / failures (source snapshot):
  (minimal test localhost ~/ot-scratch/kv-tok/hiertest) -> strip_default_params.py (header parameter->localparam, drop the
- BUILD epyc2:/srv/opentallas-scratch/claude/kv-tok/kv42_build (kv42 tree, 79 hier blocks, J=64, started 07:33 PDT): running.
## Next
## OWNER?

## KVG3-CORES
Owner: Codex qwen. Source: lanes/KVG3-CORES.md
Current / jobs / next / failures (source snapshot):
## Running (ORFS finish + abstract + corners), launched ~07:45-08:05 PDT via ot-run
- intel2:/srv/opentallas-scratch2/claude/kv-g3/cores/kits: kv3_astk_{EN,ES,WN,WS}, kv3_head_eighth_e4..e7, qkd_kvs_pc_h_head_p
- intel1:/srv/opentallas-scratch2/claude/kv-g3/cores/kits: kv3_head_eighth_e0..e3, qkd_kvs_pc, kv3_pv_pair
- epyc3:/srv/opentallas-scratch/claude/kv-g3/cores/kits: qkd_ahub
- localhost:~/scratch/kv-g3/cores/kits: qkd_ectlk
- qkd_ectlk: FAIL at plan placement: 1818 S-face pins detour in the 25.92 um gap over head e6/e7 (channel over capacity)
- qkd_kvs_pc: FAIL at plan placement: kvpc2/kvpc3 1107 S pins each detour in 25.92 um gaps (lower 750 um of kv3_pc empty) -> move kvpc0/1 down
- kv3_pv_pair: tile PASS-COND; FAIL at plan placement: p0/p3 1030 pins each detour in 25.92 um gaps (top 450 um of kv3_pv empty) -> spread pairs
Running jobs continue as pathfinding (fixes proposed are placement moves -> core views stay valid); no new submissions until KV-G3 rules.

## KVG3-WI
Owner: Codex qwen. Source: lanes/KVG3-WI.md
Current / jobs / next / failures (source snapshot):
Branch claude/kv-g3-1024 in ~/wt/kv-g3 (commits by explicit path; KV-G3 merges). Scratch localhost:~/scratch/kv-g3/wi.
07:40 PDT: baseline G0 PASS 0 err / 1811 warn; G0C FAIL 22 (hub_Wi hard_cores). Host leaf elaborated (yosys, obsx decl-hoist reading aid). core_pins_hr.py first run in progress.
08:00 PDT DONE @366980c5d9 (claude/kv-g3-1024, not pushed): plan v3.8u. G0 PASS 0/1788w (was 0/1811w); G0C PASS 0 err 49/49 clean (was FAIL 22). 22 hub_Wi host cores pinned (core_pins_hr.py/post_v38u.py/run_v38u.sh), glue:* stay partition glue, 0 missing members. pytest tools/die_plan: 27 env failures (docker socket denied for bind yosys, verilator 5.050 -Wall, docker-only g2/forest tests), none touch qwen_kvsys files.

## PART-CAP
Owner: Codex root. Source: lanes/PART-CAP.md
Current / jobs / next / failures (source snapshot):
Runs (n1/n27 started 07:20; n44 07:26; n14 re-started 07:31 and n4/n7 07:37 after the intel1/intel2 worktree mover deleted /src under a running container, ot-run clients on localhost, logs ~/coord/part-cap-logs/):
- n1  (69k synth) epyc2 DONE 41.5 min, 77.7k placed, DRC 0, TT +214.5 / SS -64.3 / FF +3.6, peak 13.1 GB
- n4_t16 (275k synth, NC=16) epyc2 /srv/opentallas-scratch/claude/part-cap/pc_rep_n4_t16 --mem 48 (thread-scaling check)
- n4  (275k synth) intel1 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n4   --mem 64
- n7  (483k synth) intel1 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n7   --mem 100
- n14 (~0.97M synth) intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n14  --mem 200
- n27 (~1.86M synth) epyc3  /srv/opentallas-scratch/claude/part-cap/pc_rep_n27   --mem 300
- n44 (~3.04M synth) intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n44  --mem 400 (added 07:27: lane8 synthesizes to 69k cells, so n27 = ~1.9M)
Origin of 400k (step 1, done): CORE_CELLS_MAX=400_000 added by c6376fe8a8 (COORD 10-23 19:36 "CORE-KS"); first used in
setup +6.6; no OOM or GPL-0307 on a large flat run; failures >400k are design timing / setup errors / wall-clock timeouts.
Next: when n4 frees intel1, run pc_rep_n27_tns10 (repair_tns 10) to price that knob at scale.

## QC-A0
Owner: Codex qwen. Source: lanes/QC-A0.md
Current / jobs / next / failures (source snapshot):
  clock-port-list fix; equiv bench builds running on intel1 (~/scratch/qc-a0-equiv: nk_asbound, nk_fp1, nl_asbound; pids 94057/111735, not mine to kill).
- 07:15 f41f0cb64 pushed: a0cv7 spec clock port lists (+6 taps), render_a0c7.py, equiv bench tools. Local pre_route_gate NK/NL WARN 0 fail.
- 07:20 A0 v7 routes RUNNING on intel2 via ot-run (16 thr, 64 GB each), launcher tools/qwen_romleaf/a0core/run_a0_route.sh
  (job.json route+collect cmds, loop env TC/mm/HM 0.03): NK intel2:/srv/opentallas-scratch2/claude/qc-a0/run_nk_v7 (src_nk),
  (first NK try failed: no ~/.local/opentallas-pdk-asap7 on new fleet; NLDM now present on intel1/intel2.)
- NEXT: G0C ft_budget fix (gen_plan negotiate with per-partition over-the-top budget), coll_ftc g3h on current tools.
  nl_asbound x {hard, aligned, mut1}: ALL A0EQ FAIL, 6300/6300 (NL 6150/6300) cycles mismatch at best shift d=-3, and the
  OWNER?: A0 G3 "from bound RTL" -- either fix the bench until it proves kit == bound, or re-kit the A0 core on the bound
- 07:55 merged main 4b7b2b3e64 (CP1-R10 gates) into claude/qc-a0-1024 dd3890c4a (tap_balance/clock_taps conflicts resolved on
  waiver does not apply to the A0 routes started 07:20 -> kept running; will report hold from signoff.sdc. COORD: say if
  the plan change invalidates bound_r8 (QC-TOK uses it) -> rebind needed before G3 of the st types from bound RTL. OWNER?
- Qwen compute P6 plan 0028ad53 (main): PASS-CONDITIONAL (record qwen_compute_plan__qc_p6__0028ad5329ca.json). G0C 4 = ft_budget st_a/st_b (yours). New: 252 interpolated column ft station points land inside A0 cores (cbn_q01 96, cbn_q00 48, cbf_q01 46, cbf_*_s2 26, sl*_su_c/su_l1 36) -> declare regs_um in the inter-core channels and re-run hops. Hottest spots: E/W ends of the slice band (sl_E5_*, 5.6 kb/100 um) and coll_f4|sl_W5_fw seam (5.4 b/um): their kits need a GRT congestion picture in review. Lever: ~18 mm2 hatched voids on the W edge. A0 v7 NK/NL tile review running (GR-QK).
- 2026-10-24 09:05 GEOM-REVIEW tile (A0 v7 NK/NL at 3_place, records qfd_tile_n{k,l}_a0c__run_n{k,l}_v7__*.json, images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-QK/qc_n{k,l}/): PASS-CONDITIONAL. 10 ROM leaves 2x5 facing a 67-um central channel, pins = plan a0_nk_pins.json, pin->reg p90 12.6 um. Conditions: (1) channel walls / 35-um LSL gap / 30-um node gap at 0.8-0.98 density -> show GRT overflow before DRT verdict; (2) clock contract mismatch: kit has 38/37 interior M7 tap drops, plan has one E-face M4 ck and the 6 R4 grid taps sit over macros with 0-2 sinks (dead); NL ck_t12 1,792 sinks over cap; per-tap pre-balance latency up to 385 ps -> put the real tap contract in the plan (hard_cores clock taps) or fix the kit; (3) routes are pathfinding only: no G3 credit until kit==bound equivalence is shown or the core is re-kitted on the bound module (your OWNER?).

## QC-TOK
Owner: Codex qwen. Source: lanes/QC-TOK.md
Current / jobs / next / failures (source snapshot):
Branch claude/qc-tok-1024 (worktree localhost:~/wt/qc-tok), host intel1 for heavy runs.
## Current step
 Running: intel2 smoke_cb16_near (bind cb16 chain, lead 8 run, then lead 14 on same binary); intel1 smoke_tree_near
 (tree equivalence), smoke_both (bound_r8 near+far, lead 8 = expected FAIL baseline).
- LINK (bound_r8, kv41): tp8 PASS 3/3 + 9/9 mutants FAIL (after MU calendar recompiled at LS 389: ls-378 fixture
- XT1 near (bind_smoke --local, bound_r8): FAIL nominal near 0/64 (FAULT heads cyc 181, near_cluster 286), mutant FAIL.
## OWNER?
## xt1 (sub-lane, branch claude/qc-tok-xt1-1024, worktree localhost:~/wt/qc-tok-xt1)
  TP8 L0 die0 image build pid 69012 (log build_img.log), pin = results/arch/qwen_tp8_native_dispatch_1014/actual_checkpoint_layer0/die0 matrix_int8 8f48f3f4
  runs on intel1: bound_r8 near smoke (smoke.sh near, log smoke_near.log, work smoke_near); source control stage_xt1 landed pid 77679 (ctl/, ctl.log)
- 2026-10-24 13:53 PDT launched intel1:~/scratch/qc-tok/link/run_all.sh (pid 85413): source assembly = git archive main 3e05af806b;

## S81-CORES
Owner: Codex s81. Source: lanes/S81-CORES.md
Current / jobs / next / failures (source snapshot):
# S81-CORES lane (claude/s81-cores-1024, worktree localhost:~/wt/s81-cores; hosts localhost 64 thr + idle via ot-run)
Goal: S81 G0C completeness 174/174: hard-core definitions for the 91 G0C hard_cores fails (74 leaf, 16 svc, 1 eng).
## Current step
  faces made every ve position fail, vq xf faced E away from the bus). vn/ve(r5)/vsw/rxsf/rxsb closed views unchanged.
## OWNER?
(t74, t63, t64, t49, t48, t8, t9 merged into t10, t24, t25, t40, t44, t72, t73; same orients) -> 7 fewer hard_cores
G0C fails (91 -> 84). The merged instances are MY copies of their canon, so canon cores must land in the mirrored frame
- 2026-10-24 07:48 PDT: branch claude/s81-cores-kits-1024 (worktree ~/wt/s81-cores-kits, base origin/claude/s81-cores-1024 + merged origin/main 4b7b2b3e64 for sdc_lint/face_guard). Generator physical/die_plan/s81/cores/kits_repin/gen_kit_repin.py; sdc_lint PASS at gen for vs_lfp / vq_lfp (macro moved to [55.296, 4.32]: closed site was inside the 4.32 core margin) / hrow_c. r1 launched localhost:~/scratch/s81-cores-kits/r1/<kit> (16 cpu / 40 GB each, finish + abstract + TT/FF/SS STA), pids 870948 hrow, 870952 vq, 870959 vs.
- 2026-10-24 07:51 PDT: r1 face_guard FAIL on vq + hrow: 1 'shared' bit each = the sticky fault output flop (fault <= fault | ...) feeding its own D. RTL unchanged by rule, so face_guard_core.py classifies self-loops (FAIL kept in the record, physical run continues only when every failure is a self-loop). r1 stopped; r2 relaunched all 3 at localhost:~/scratch/s81-cores-kits/r2 (pids 909946 hrow, 909950 vq, 909956 vs). Kits committed 389a1d99a7. OWNER?/COORD: face_guard self-loop on a sticky fault flop: waive or RTL change?
- 2026-10-24 07:56 PDT: vs r2 face_guard FAIL (real, not self-loop): 130 dropped (128 unused ve_oy + 2 s_d input bits), 989 shared (output regs read internally: x_wd/u/sw_d 256 each, ve_ah 128, ve_rh 64, ...), 259 feedthrough (ve_aval merged with sw_d by opt_merge). vs r3 = + closed kit's ot_keep_regs (OT_KEEP_PIN_REGS=1) + pin_reg_split.tcl, face_guard FAIL recorded and physical run continues as PATHFINDING: localhost:~/scratch/s81-cores-kits/r3/ot_s81sl_vs_lfp pid 1007451. vq/hrow r2 past placement.
col_* types unchanged; G0C hard_cores fails 91 -> 91 (same set). New/changed types: lk_*, s_0S_x*, s_0S_LP, s_7N_LP,
- 2026-10-24 08:10 PDT: REVIEW (owner 08:05 order): rendered + read all 3 (kits_repin/results/geom_review/*.json + png). vq r2 FAIL GRT-0183 (boxed-in net 3 um off the SRAM W pin wall; SRAM off-centre, 22.7-um E channel vs the new full-height E u/um face) -> r3 SRAM centred on pin-free S face [38.988, 4.32], rows halo 4.32: review PASS-COND (corner clk pin NW = plan contract, watch CTS) -> r3 launched pid 1231852 (~/scratch/s81-cores-kits/r3/ot_s81sl_vq_lfp). hrow PASS (28% util, ring of face flops, ck N centre). vs PASS-COND (N face 1589 pins ~10/um densest; SW corner clk; x_qd W -> ve_aval N ~280 um one-cycle runs). GEOM-REVIEW second review welcome. commit 715d0b3f91.
- 2026-10-24 08:28 PDT: COORD ruling (no self-loop waiver) applied: kit-local fault port-flop duplicate (keep) in vq/hrow, lockstep PASS (100k cyc, every output every cycle) + mutant caught (results/lockstep_*.json); kit face_guard PASS vq 828/828, hrow 3849/3849 (r4 synth). hrow r2 signoff.py: NOT SIGNED (TT setup -21.5, FF hold -46.6 x1787 = output ports vs fixed 250 ps vclk at FF, DRV 1012 slew on 1 fanout-133 net; DRC 0, spread 68/64, pins 3851/3851). r5 (MCMM tc+bc hold repair, set_max_fanout 24, slew/cap margin 20, last gasp, signoff final step) launched localhost:~/scratch/s81-cores-kits/r5 vq pid 1716762, hrow 1716770. signoff.py gaps reported to COORD (reset ports rst/rst_n not skipped; scalar pins bit None). commit 14aa1a3bac.

## S81-HEAD
Owner: Codex s81. Source: lanes/S81-HEAD.md
Current / jobs / next / failures (source snapshot):
- G2 on intel2 (/srv/opentallas-scratch2/claude/s81-head/g2, docker --memory = --memory-swap): die probe PASS
  RISK: 17 mm root -> tap is a die clock-tree design job (H-tree / grid), not a probe failure.
  synth PASS, face_guard PASS 1,132/1,132. ROUTE RUNNING: ot-run --hosts intel2 unit oth-ubuntu-514688-1792853423,
  dir /srv/opentallas-scratch2/claude/s81-head/g3/hd_tile (run_route.log). r1 died at synth (strap generate-if) ->
  kept at ../g3_fail_strap_r1.
## Next
## OWNER?
  results/geom_review/s81_head_img/hd_tile_r2_global_place_FAIL.png => FAIL: elemB W face + 566-bit bus-i window in one
  intel2 /srv/opentallas-scratch2/claude/s81-head/g3_fail_review_r2.
- Running now (intel2): G2 re-run on r3 geometry (/srv/opentallas-scratch2/claude/s81-head/g2r3: die + 8 types) and
ot_s81hd_mesh_ep, ot_s81hd_host_ep (new / rework); ot_s81hd_ctl(_glue) exists only on the unmerged H10/H11 branch
- BLOCKED on the plan (your gen_plan.py): hd_spn / hd_spn_end have no `sources` for ot_s81hd_spo / ot_s81hd_spr (kit RTL
  hd_mesh / hd_ctl / hd_host: type module == content module + no RTL (as you said); hd_serdes (ot_pdie_serdes) and
- S81 head plan 6b6620d0 (@fa3ada974c; cc7b6206 geometry identical): PASS-CONDITIONAL (record s81_head_plan__s81_head2__6b6620d0e030.json) - independent review, supersedes the self review for G1. Clean: symmetry, no slivers, hops <= 0.31 reach, tile macros 10-15 um channels with the tap in a channel, all 18 bit reversals are corner crossings (free as L-routes). Lever: the 345-um station/spine partitions force 3-4x the stations reach needs (m0S 48 cyc / 16.3 mm, host 38 cyc / 12.4 mm, coll_WN2 20 cyc / 6.5 mm) - wider station partitions would cut tens of cycles on the mesh/host lanes. hd_tile: the revised floorplan after your failed r2 must be rendered + recorded before route; GEOM-REVIEW tile review of hd_tile running.

## S81
Owner: Codex s81. Source: lanes/S81.md
Current / jobs / next / failures (source snapshot):
  window on every die: needs a tool rule for in-band dies (e.g. `host: "in_band"` on the WN2/3 windows) - tooling ask.
## TYPE-DEDUP proposal (2026-10-24 07:45 PDT, lane TYPE-DEDUP, tool merged to main 4a5c3620d8; your plan NOT edited)
  `dedup.py variants PLAN --rtl <bound rtl>` on the next bind to see per-type kit variants (QC 56 -> 80 modules).
  closure happens once. This is the path S81-CORES is already on for the 74 leaf G0C fails (leaf cores) -> S81-CORES
## S81-XDIE (reserve pair + in-band host)  (2026-10-24 08:02 PDT, branch claude/s81-xdie-1024 @cb472fd41f, NOT merged; ffeace5ae4 lacked census_map -> G0 12 census errors, fixed)
- Host: lk_WS0 host:true dropped; WN2/WN3 host "in_band", declared route lk_WN2 -> s_0N_LP -> [ctrl__s_0N_LP__seqhost]
  xdie_io FAIL 130 -> PASS 0 err (2952 circuits); col_* types unchanged; pytest 158 passed 1 skipped.
### OWNER? (S81-XDIE)
4. Retire the f_host/f_ks part of unit__s_7N_LP__seqhost in favour of HOST(b)? (not done)
  If that fails, the options are: x-mirrored pin variants of vs / vq (re-pin + kit), FIRM internal stations (+1 cycle, RTL contract), or fixed-x leaf windows (your call).
- S81-XDIE plan e2299c43 (@cb472fd41f): PASS-CONDITIONAL, BUT my check.py --completeness gives G0C 108, not the claimed 91: +12 census (map still names s_0S_x06/x010/x011/x15, s_7N_x07/x17) +5 complete[cells] (serdes__t11..t14, slice_station__t7). Fix before merging. Corner SerDes stays provisional (your OWNER? 1).
- 2026-10-24 09:35 GEOM-REVIEW tile (GR-S81F, results/geom_review/col_*__{g3k2|elem}_col_*__<hash>.json; images localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81F/<kit>/ (see col_h9_r2__t1/h9_r2_dataflow.png)): **all 7 frame kits FAIL -> STOP the g3k2 frame routes and do not submit these kits again until revised.** Pins/face windows, pin->reg (p90 8-9 um), macro gaps, ft stations, taps-off-macros: all fine now. Blocking:
  (4) Data flow: each ROM row's cfg7_seq sits at the row END, 350-500 um from its far ROMs (that is where the negative slacks are); qbank_S sits 450-680 um from its sequencer. Put the sequencer at the row centre and the qbanks next to it; the 750-um hop rule ignores the macros' 514-845-ps output delays.
  Measured (TT, old runs at CTS): WNS -540..-1,242 ps, skew 371-519. The GEOM-REVIEW8 PASS records for h9_r1 / h10_r1 / h10_r2 / h9_r2 were conditional on TT setup >= 0 at CTS, and that condition is not met. They are superseded by these FAILs. Plan/generator owner + COORD: (1) and (2) are plan fields (hard_cores lib, core clock taps).

## SIGNOFF
Owner: Codex root. Source: lanes/SIGNOFF.md
Current / jobs / next / failures (source snapshot):
Merged: 4ab1ec1399, 0f5176689d (SS-based, SUPERSEDED), f942bf2f72 (TT rule, current). 0 deletions.
## Done
   TT-rule paper screen: 124 PASS, 7 FAIL (all pin-flop spread > 80: dsdv_gunit_l5, qfd_dv_lane_h_safe2,
## Not done / notes
- Coordinator's earlier item (classify the 88 SS failures) is moot under the TT rule; the 7 TT-rule paper FAILs are all
- Run dirs (finished): intel1/intel2:/srv/opentallas-scratch2/claude/signoff, epyc3:/srv/opentallas-scratch/claude/signoff
- 2026-10-24 08:23 PDT FROM ELEM-QK (re-running 33 QC/KV ref_tile kits at their closed commit, then signoff.py --corners tt,ff):
  tools/elem_qk/flatten_sdc.sh) fails the kit vocabulary (needs real tap clock + ONE virtual IO clock w/ latency, period
  exactly 833 not 833.333, no -add_delay); face_guard FAIL unregistered 2 (a,b->q combinational by design).
  OWNER?/SIGNOFF: is a ref_tile re-run ever signable, or must each module be re-kitted in die-plan kit form (G3)? Until

## TOK-DS
Owner: Codex s81. Source: lanes/TOK-DS.md
Current / jobs / next / failures (source snapshot):
- 07:50 fc31 cut_3S_ctl LAYER replays (L0/L2/L14/L20) reproduce the fc30 signature: SCHEDULE_MISMATCH from cycle 294 on o__w_xrW_2S_l0_lnd (port 2248) / o__w_xrE_4S_l0_lnd (2244): column-4 CTL line beats never leave (got 0). Cause = harness: run_layers.py gen passes no --idle-run/--host-boot/--ks and the layer programmes have no prog/host_boot.memh, so u_seqhost never starts the job on the HOST cut. The HOST/control part of a layer is exactly the native entry replay (jobs 15/16/17/20/21/22 = replay_jobK progs) that lane S81 is triaging -> 3S_ctl per-layer verdict BLOCKED on S81 entry PASS_CUT_COMPONENT (also needed by dv_cut_replay check as OT_S81_XRT_RUNTIME_PROOF). CTL-shift mutants stopped (control is meaningless against a failing baseline).
- 07:2x epyc3:/srv/opentallas-scratch/claude/tok-ds/fc31/run_ctl/{L0,L2,L14,L20} (cut_3S_ctl replays on compiled fc31 programmes) + mut_m1/{L0,L20} (shift-kind:CTL:1 negative control); logs fc31/logs/
- epyc3:/srv/opentallas-scratch/claude/tok-ds/fc31 (cuts/out_cut_{0S,0N,7} builds pids 85109/85110/85111; compile pid 85681)
- epyc3 inputs: /srv/opentallas-scratch/claude/{stw-s81d-tok (ep5 layers+fc30), s81-p9-fc-1023 (fc31 + monfc31 build), stw-s81c-cap30}
- MERGED main 2c4e32da32: components on main (results/token_pass/tokds_comp_1024): owner fold PASS 20/20/20, dense XS cap PASS (GO 453, last capture 825), KV VP PASS (done 1028/1133), rstop PASS (egress 7..23); all mutants CAUGHT; cycles = 10-21 record. Composition (results/token_pass/tokds_compose_1024, plan v4.8 lat table): 1u AR 1,495,133 cyc = 802.6 tok/s, MTP 2,564.0 tok/s; measured-current 29.9% / old 49.8% / priced 13.8% / PHY 6.5%; MU AR 50u 40,130 agg, MTP 6u 15,384 (10u fails same-user check). Model only, no token pass.
- fc30 layer runs (10-23, recovered): all 16 cut replays FAIL: data cuts 0S/0N/7 have 0 check lines (nothing compared); 3S_ctl faulted from 155 (203 mismatches); check refused by XRT guard (since fixed 8ec7bc8bc).
## OWNER?
- 2026-10-24 07:03 started: staging ~/wt/tok-ds-comp on epyc2+intel1 (claude/tok-ds-1024 = 8a5d1f3dab). Inputs found: dense vectors intel1:/mnt/old-nvme0/claude/codex-tok-s81-layers/dense_driver/vec_B_kv_landed_current; KV baseline intel2:/mnt/old-nvme0/claude/codex-s81-kv-vp-1021/baseline (its source pins differ on main: ot_reset_sync, ot_s81sl_kv_bank, ot_s81sl_kv_leaf).
- 07:40 owner fold PASS (RB 20/20/20 = 10-21; MUT2 CAUGHT), rstop PASS (egress 7..23 = 10-21; xooff/xoall/xonoflag/tiercol CAUGHT) on epyc2:/srv/opentallas-scratch/claude/tok-ds/comp. KV VP gate building intel2 (same dir); dense XS cap epyc3 (same dir; vectors regenerated on tree_fc31 + fix/L0). Findings: NBA guard not installed on new fleet (scanned explicitly); main xrt 0ec7a8db not in xr_timing.XRT_MODEL; run_dense_xs_cap.sh inventory lacked ot_pl_land_reset_forest.sv.
- 07:45 KV VP PASS (main kv_bank/kv_leaf/reset_sync; R3 vectors; mutant CAUGHT; ages 266..285, elapsed 1028/1133 = R3) intel2:/srv/opentallas-scratch/claude/tok-ds/comp/kv_vp. Dense: attempts 1-3 failed (xrt unqualified in compiler; bench inventory MODMISSING x2, fixed in tool), attempt 4 building.
- 07:53 DONE claude/tok-ds-comp-1024 @3a272239b9 (pushed, not merged): dense XS cap PASS too (fc31 tree regen; cfg390/GO453/ret726..752/CAP825, shift 322 = 10-21; input-corruption CAUGHT). 4/4 PASS, receipts results/token_pass/tokds_comp_1024/*.json (compose-readable, no op binding). Open for owner/other lanes: xr_timing.XRT_MODEL lacks main xrt 0ec7a8db; fleet NBA guard not installed.
- 2026-10-24 07:15 started: worktree localhost:~/wt/tok-ds-compose (claude/tok-ds-compose-1024 from claude/tok-ds-1024 978d80201). Latency table of record = physical/die_plan/s81/lat/s81_latency.json (plan_digest b4ac6d49d5198cd0 == digest of current die_plan.json v4.8, 834 lanes); r8/ = BINDER4 v4.6 as-built bind table (digest b8e46d33, 820 lanes, 13 lanes +1..2) + R8 landing pads on v4.7b bus groups -> not of record.
- 2026-10-24 07:22 DONE claude/tok-ds-compose-1024 @75d8ff675 (pushed, not merged): tools/s81_dv/tokfunc/compose_tok_ds.py (--selftest PASS 14/14 incl. parity with toksim cycles.json, --check SAME) + results/token_pass/tokds_compose_1024/{compose_1u.json,calendar_mu.json,README.md}.
  1u AR 1,353,373 cyc = 886.7 tok/s (DAG) / 1,495,133 = 802.6 on 241-stage map; MTP 1,758,080/step = 2,838.8 (DAG) / 2,564.0 (map). AR measured-current 29.9 % / old 49.8 % / priced 13.8 % (plan lanes 2.9) / PHY 6.5 %; MTP 26.2/55.1/12.0/6.7.

## TOK-HBM
Owner: Codex hbm. Source: lanes/TOK-HBM.md
Current / jobs / next / failures (source snapshot):
- Last results (TOKi 10-24 04:37-09:00, val_toki, component_probe scope): DS L0 t_ds_l0 FAIL 667/4745, _x1 FAIL 672/1785,
  _x2 FAIL 5/3831; L2 FAIL 1305/3234, _x1 38/4217, _x2 5/4062; L14_x3 FAIL 5/5847, L14_x4 PASS 3822/3822;
- epyc2:/srv/opentallas-scratch/claude/{tokg-1023,tokd-hbm2,tokj-1023,hbm-p7-tok-1023} = copies of intel2 old-disk dirs at their
## Current step
- copying old-disk vehicles to epyc2; xdie main_rows256 co-sim next; split rebuild next.
  AR-step (r14_coll_ar): DS PASS on r14 + main RTL (launch->pub 537/542); Qwen running; LEAF_SPLIT=1 direct run running.
- Old TOKi DS failure classes mapped to records (priced_layers 1018 numbering): ALL COLL records PASS; ALL SU.VOP records
  FAIL (res_copy 640 checks = no write; moe_sum/scores_bias/w_scale zeros); ALL HC_MIX FAIL (hleaf_SW target hc_SW
  Diagnostic replays running on epyc2 (diag/su31_*): checks shifted 0/64/256/1024/4096 and we/bank +26.
- Running: ld/{t_qw_l0_r0,r5,t_qw_chain_r0,r5,t_ds_l14,_x1,_x2} (4-13 h each), leaf-split slice build (build_split.sh).
  t_qw_chain_r0/r5 to intel2:/srv/opentallas-scratch/claude/tok-hbm/ld (binary + replays copied to same path).
- 08:30 diag results (DS L0 rec31 attn.res_copy, 640 checks): control FAIL 640 (reproduces TOKi); checks +64 FAIL 640;
  we/bank +26 (config pairing fixed) FAIL 640 with checks +0/+64 -> dest never written. pgp_SW runs serial 4301-4438
  vmstat: SU executes ~55 edges after its scheduled grant). Next diag running: all su_prog drives ADVANCED by 50/55/60

## TOK-QW
Owner: Codex qwen. Source: lanes/TOK-QW.md
Current / jobs / next / failures (source snapshot):
  3317/27981, h16y leaf absent on main); compose 1u 269,452 cyc = 4,455.3 tok/s, 4u 11,811.3, price HELD (head FAIL, tp8 diag,
## Runs (RUNROOT intel1:~/ot-scratch/tok-qw/r1024, assembly = git archive main 8a5d1f3dab; logs localhost:~/wt/tok-qw-logs)
- stg   : ot-run intel1 --mem 240, stage_stg.sh --su-lt 0 --fx recovered tokqw4 stg3/fx (36 layers) -- RUNNING since 07:01
- head  : stage_head.sh --leaf (die-selected leaf h16za native32_1r) -- DONE 07:05 PASS
- xhead : stage_xhead.sh (new) calibrate + per-consumer sweep + 4 cases + 10 mutants -- RUNNING
- s8exp : tb_qfd_dv2 FACE 3 = BOUND die slice row (s8 flat / ce_w5 / ce_l9h / ce_e5 per position) lint/build -- RUNNING
- head PASS (RTL-functional, die-selected leaf, main 8a5d1f3da): img0 123/123, imgh 131/131, bmut3 FAIL as required;
  LM-head stage start->END 3,135 = compiled 3,135 (plan price 3,101, +34). 10-23 FAIL cause: the behavioural h16y family is
  not on main + generic LP lockstep (abandoned LP, not the die parent). stage_head.sh --leaf added.
## OWNER?
2026-10-24 07:30 PDT TOK-QW/xdie_bound: compute->KV D2D co-sim on BOUND link ends, branch claude/tok-qw-xdie-1024 @2dca1cc835 (not merged).
- Run intel1 ~/ot-scratch/tok-qw/xdie_bound/run2 (ot-run unit oth-ubuntu-194042-1792851975, done 07:29); results
  bound compute master x bound KV master FAIL = F6: compute obs1 STATUS v1 extension rejected by KV legacy status RX
  Mutants caught: TXDP_K 66/68, TXDP_C 9, seam KS_RXV/SK_TXP/CS_TXS +1, result bit, status done, PHY bit, run late.

## TOPDOWN-PLAN
Owner: Codex root. Source: lanes/TOPDOWN-PLAN.md
Current / jobs / next / failures (source snapshot):
Toolchain on every host: ~/.local/opentallas-tools/bin (verilator 5.050, yosys 0.68, opensta be771a0), docker +
| S81 | v4.7b PASS (main); v4.8 on s81-p9-r8eq unmerged | COND | v4.8 G2 PASS 31 probes (unmerged) | 6/7 frame kits FAIL review earlier; core-s81* hard cores in progress | not run | FAIL 6/6 entry replay; fc30 entry gaps lowered (tokj-s81-lower merged), fc30 status fault fix on s81-p9-fc (unmerged) |
| Qwen compute | PASS, G0C 52/56 (qc-p6-g0c merged) | COND | PASS | mixed; A0 v6 core clock drops on qc-p6-a0v6 (unmerged) | CP1 pair physically clean, seam timing unproven after grid-tap ruling | 3/4; xt1 0/64 pending re-run on bound_r8 (bind_smoke exists) |
| Qwen KV | v3.8h merged; v3.8s FIRM astk stations on kv-p8-hub (unmerged) + GEOM-REVIEW8 PASS (unmerged) | PASS (v3.8s) | open | IO only; hub_Ei P&R waits for clock variant spread <= 80 | not run | not run; kv41 bound top lint 0; hierarchical Verilator bench on tokj-kvslice (WIP); PV boot constants need W request-lane pads (kv-p7) |
| HBM d4g | fallback plan P7 merged | COND | partial | none | not run | held; HBM-ARCH B2 redesign WIP (hbm-arch, H-tree clock, 5 SerDes); binder4 physical/die_plan/hbm/r8 held back (COORD 23:10) |
| ROOT-MERGE | review + merge the finished unmerged 10-23 branches listed below; keep main green | localhost | (main) |
| S81 | S81 v4.8 -> G3 frame kits with internal stations + core-s81 hard cores; triage 6/6 entry-replay failure | localhost + epyc3 | claude/s81-p10-1024 |
## Merge queue (ROOT-MERGE), unmerged branch tips at loss
- NOT to merge yet: hbm-arch-1023 (WIP), tokj-kvslice-1023 (WIP), kv-p7-v38-1023 (G0 FAIL WIP), core-hbm-1023 (stopped by COORD)
## Queued lanes (waiting for a subagent slot; 20-concurrent cap reached 2026-10-24 07:05)

## TRIAL-HBM
Owner: Codex hbm. Source: lanes/TRIAL-HBM.md
Current / jobs / next / failures (source snapshot):
branch claude/trial-hbm-1024 (main + claude/hbm-arch-1024 @3277b5e78b), worktree localhost:~/wt/trial-hbm
## current step
## OWNER?
- smoke window case running localhost /srv/opentallas-scratch/claude/trial-hbm/fab_win (docker 8 cpu 64 GB).
- FULL die fabric run launched: epyc2:/srv/opentallas-scratch/claude/trial-hbm/fab_full (ot-run --mem 320 --threads 32, local ot-run pid 1051726). 1,360,342 flops / 1,155,477 hop nets. Per-bit hops: max 957 um, 14,397 > 850 um, 506 > 900 um (all L19_2 / L19m_2 into b103: per-bit spread beyond the G0 window-centre hop 849.6).

## TRIAL-QK
Owner: Codex qwen. Source: lanes/TRIAL-QK.md
Current / jobs / next / failures (source snapshot):
Branch claude/trial-qk-1024, worktree localhost:~/wt/trial-qk. Hosts: 1 TB hosts (epyc3 / intel2 first) via ot-run.
  Runs via ot-run on intel1/intel2: /srv/opentallas-scratch2/claude/trial-qk/{qwen_compute,qwen_kvsys}{,_ir}, calib;
  launcher logs localhost:~/ot-scratch/trial-qk/logs/*.log.

## TRIAL-S81
Owner: Codex s81. Source: lanes/TRIAL-S81.md
Current / jobs / next / failures (source snapshot):
# TRIAL-S81 lane (claude/trial-s81-1024, wt localhost:~/wt/trial-s81; die jobs on intel1/intel2 via ot-run)
## Current step (08:25 PDT)
tools/die_plan/die_trial.py kit/clock/render/report written (uncommitted yet). Running: s81 GRT (intel1), s81_head PSM +
- kits localhost:/srv/opentallas-scratch/claude/trial-s81/{s81,s81_head}; mirrored intel1:/srv/opentallas-scratch2/claude/trial-s81/s81,
  intel2:/srv/opentallas-scratch2/claude/trial-s81/s81_head (ot-run clients on localhost, logs ~/coord/part-cap-logs/trial-*.log)
## OWNER?

## TYPE-DEDUP
Owner: Codex root. Source: lanes/TYPE-DEDUP.md
Current / jobs / next / failures (source snapshot):
# TYPE-DEDUP lane (claude/type-dedup-1024, merged to main 4a5c3620d8 @ branch 3700d7ab83)
## Status: DONE (tool merged; proposals posted in S81.md, S81-CORES.md, KV-G3.md, QC-A0.md, HBM-ARCH.md)
(2 pre-existing failures on main too: test_check::test_gen_rtl_lint_and_bench (verilator SYNCASYNCNET),
  STRAP / FT-POP families reported, never merged (R7: no tie-offs). verify(): ports/lanes/latency/census untouched,
| KV | 49 -> 49 (hg_v1_r1..r5 plan-identical but bound RTL differs; plan-only 49->45 FAILS G0 R8, 7 err) | PASS/PASS | 22 -> 22 |
| HBM | 60 -> 60 (7 netlist-identical _v1 pairs blocked by 2-18 mirrored window positions each) | PASS/PASS | 121 -> 121 |
## OWNER?
localhost:~/scratch/type-dedup/dd_s81/{die_plan.json,dedup_provenance.json} (the 161-type S81 copy); rest removed.


## Live Qwen collection 08:58 PDT
- QC-TOK: CODEX took over: collect cb16/+6 fill results and run discriminating near nominal/mutant on codex/qc-tok-1024. intel2 smoke_cb16_near lead8 FAIL 56/64 (GU 0/8); lead14 existing near JSON PASS 64/64. Lead-sweep wrapper fails on absent gold_far.json because this is a near-only vehicle. New own ot-run job intel2:/srv/opentallas-scratch2/claude/codex-qwen/xt1_near14 (log localhost:/srv/opentallas-scratch/claude/codex-qwen/xt1_near14.log), reuses existing binary. Full far vehicle remains to retest. Trees/bound smoke 0/64 expected with old lead/skew.
- KV-TOK: Collected kv42 build: remake2 exit 0; boot nominal/mut_frame and FAR=1 token processes remain live CPU-bound on epyc2:/srv/opentallas-scratch/claude/kv-tok/{boot42,tok42}. No finished verdict yet. Root-disk run dirs are live and cannot be moved; new work will use scratch2. Next collect boot/token verdict, diagnose first fault.
- TOK-QW: Collected completed source stg result: PASS 527/527, ISA 1,032,336/1,032,336, delivery_timing_qualified=true. Head PASS 123/123 + 131/131, bmut3 caught, control span 3135 cycles (+34 vs price). Bound s8exp lint blocked by duplicate SRAM definitions (sram_models_nofatal.sv vs another supplied definition); next remove duplicate harness inventory and continue bound vehicle. Source result does not establish bound-s8 pass. XDIE F6 status-v1 rejection and F7 stale calendar require fixes.
- QC-A0: Route jobs NK/NL still live in intel2 scratch2 run_n{k,l}_v7; no final verdict. Plan/generator mismatch fix exists only uncommitted in paused lane tree, must reproduce in own branch. A0 equivalence remains FAIL/non-discriminating; G3 credit blocked. Next reproduce tap-hook scope correction, G0/G0C and inspect negotiation candidates.
- KV-G3: Collected live hub runs: intel2 scratch2 g4/vC and vF at GRT extra iterations; vG still optimization with TT setup about -6104 ps at ft27 output D (pathfinding FAIL, investigate station pin-to-last-reg geometry). vC independent review FAIL remains binding; no new submissions before revised out-face stations, regs_um/core-free channels and review.
- KVG3-CORES: Existing 16 core runs span intel1/intel2/epyc3/local; results collection ongoing. Plan placement FAILs for ectlk/kvs_pc/pv_pair handled by main KV v3.8w spread revision. Astk/head/pv tile reviews conditional. Next collect routed corners/signoff and fix actual timing failures.
- KVG3-WI: DONE: hub_Wi core pins merged a7e29a44ac; no new job. Remaining broad KV binding/host hardening tracked under KV-G3.
- ELEM-QK: Existing 33 ref_tile re-runs plus KV kit wave must be collected; first hp_or2 timing +441.7/+25.6 ps DRC0 but NOT SIGNED because sdc_lint/face_guard contract fails. QC tt_ctlm/native59 face_guard fails from P5-bound vs P6-plan mismatch; blocked on bound_p6. Next collect rebind and new face_keep kit results; no false closure.
- TRIAL-QK: intel1 scratch2 trial-qk build artifacts both dies exist; QC route_g0 log present, IR power JSON exists. No final report collected yet. Next gather GRT/IR, diagnose resource/tool failures, retain abstract/budget qualification.

CODEX10:38: sharedclockfixmain0231295e92, actualheadTT251..716ps465skew diagnosed; S81/HBMownedredesign. NewreviewedcurrentCP1reach405/grid200 corelesspairjobs local64GB8thr each codex-cp1/reach405/kits, sessions35302/68574; oldr1reportOOM32GB diagnosed. KVcandidate ownbranch6dd64015fd preserved, full-dieadoptionheld. T7currentuniformODBsignofflive128GB8thr session96486; finaltimingfilescomplete. NetlistfastSTAexperimentrejected on actualqkdoutputbufferloops/mismatch. See CODEX-LOG10:38.
