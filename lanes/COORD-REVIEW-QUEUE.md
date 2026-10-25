# COORD-REVIEW-QUEUE (ROOT-MERGE, 2026-10-24)

Lane ROOT-MERGE checked each branch in the TOPDOWN-PLAN "Merge queue" and every claude/codex *-1022/*-1023 branch tip
dated after the 10-23 05:08 PDT owner reset. Test merges were made in ~/wt/root-merge (detached), then main was
fast-forwarded under ~/coord/merge.lock. Message format follows BRIEFING (`-X ours`, 0 deletions in every merge).

Gate on main after each batch: `python3 -m pytest -q tools/die_plan/` + `check.py` G0 on the 4 plans.
NOTE: localhost has no system pytest/matplotlib, and the ubuntu shell is not in the docker group yet. I used a venv
(scratchpad rm/venv, --system-site-packages + pytest + matplotlib) and ran the tests under `sg docker -c` (the bind
tests need docker yosys). Without docker, 23 bind tests fail on the environment, not on the code.

| main before | pytest tools/die_plan | G0 s81 | G0 qwen_compute | G0 qwen_kvsys | G0 hbm |
|---|---|---|---|---|---|
| 3e05af806b (start) | 118 pass | PASS 0 err/1082 w | PASS 0/88 | PASS 0/1811 | PASS 0/516 |
| edcd4f42f8 (batch A) | 118 pass | PASS 0/1082 | PASS 0/88 | PASS 0/1811 (v3.8s) | PASS 0/516 |
| df641549db (batch B) | 126 pass | PASS 0/1105 (v4.8, 174 types) | PASS 0/88 | PASS 0/1811 | PASS 0/516 |

## Queue decisions

| branch | tip | decision | merge commit on main | reason |
|---|---|---|---|---|
| claude/kv-p8-hub-1023 | 1f988a72f | MERGE | 7353065934 | KV plan v3.8s FIRM astk stations. G0 PASS (0 err; 1811 warnings with main's check.py, the branch claimed 1813). G0C hub_Eo/Wo clean. Evidence files g0_summary_v38s / lat_delta_v38s / renders are in the branch. With GEOM-REVIEW8 it clears the KV-P7 condition. |
| claude/geom-review8-1023 | 0e0f022b2 | MERGE | d59e42f105 | 14 new verdict records and 6 amended ones. kv3_hub_Ei 383b07 goes FAIL (21:07) -> PASS-COND (23:23) under the quoted COORD 23:22 OWNER DECISION CLOCK. The reviewer re-amended in place, as GR8 did at 21:07. The measured FAIL numbers (TT 342 / FF 288 spread) stay in the reasons text, and the old record is in git at 96c29cfeb. Flag for the coordinator: confirm that owner decision. |
| claude/kv-p7-1023 | c92b01b02 | RECORD-MERGE | deeb5fbeb7 | Boot image on kv41: non-PV constants valid. PV NOT FINAL (no W request-lane pads; RL/FIA offsets). Includes kv-p6-boot. KV-TOK continues from here. |
| codex/hbm-token-0936-1023 | 1c729e419 | RECORD-MERGE (missed by the plan) | edcd4f42f8 | FAIL evidence: HBM token rec2 collective transport mismatch. New dir only, nothing claimed as qualified. |
| claude/s81-p9-1023 | 359e63c39 | MERGE | c3ef3b9039 | Plan v4.8: G0 PASS on main, G2 PASS 31 probes (r8eq), LANDED BUNDLES R8 rule plus tests, LPR_ROOT N2 seam bench PASS. The plan file equals the branch's. 7 tools/die_plan files auto-merged without conflict. |
| claude/s81-p9-r8eq-1023 | 3be3c7df1 | MERGE (contained) | via c3ef3b9039 | Ancestor of s81-p9. |
| claude/s81-p9-fc-lpr-1023 | 7dd91ac7a | MERGE (contained) | via c3ef3b9039 | Ancestor of s81-p9. |
| claude/s81-p9-tool-1023 | 9db54b73d | MERGE (contained) | via c3ef3b9039 | Ancestor of s81-p9 / core-s81*. |
| claude/s81-p9-tool2-1023 | 4944e4a82 | MERGE (contained) | via c3ef3b9039 | Ancestor of s81-p9. |
| claude/s81-p9-face-1023 | 6f31c59af | MERGE | aed20626e9 | Opt-in face masks (default unchanged). Benches bit exact, lint 0. s81_dv bind tests pass. |
| claude/s81-p9-fc-1023 | 9e40c62fa | MERGE | b55d98264a | fc30 status fault fix: calendar 72 frames 0 fail, probe tt/ff PASS, mutants caught. Adds new tools and evidence only. |
| claude/s81-p9-cf-1023 | 61744766b | RECORD-MERGE, NOT CLOSED | 57e8f36bc2 | crs4p gate 3 FAIL textbook.reset_landing; gate_result.json is committed. |
| claude/core-s81-1023 | cdc5721f0 | RECORD-MERGE | 0ff2bb82e4 | ve r5 closed view, split miters PASS. GEOM-REVIEW8 FAILED the 1442.88-um leaf placement, so the decision is open for S81. The gen_plan_v4 NONFRAME_HC change is in main, but die_plan.json (v4.8) was not regenerated with it. |
| claude/core-s81-eng-1023 | e684da414 | MERGE | 3960358938 | 3 hard cores, lockstep PASS, mutants caught, GR8 PASS. |
| claude/core-s81-svc-1023 | 748770e1b | RECORD-MERGE, NOT CLOSED | ce59a1cd4b | TT setup WNS -25.29 ps (88 endpoints). DRC 0 / GRT 0 / hold 0. TT only, no SS/FF sign-off. Opt-in define. |
| claude/tokj-s81-split-1023 | 563949239 | MERGE | 58d519afe0 | Build-script change. The old path is kept behind OT_DV_BINARY=1. |
| claude/cp2-tool-1023 | e825c9c69 | MERGE | df641549db | CP2 tool work plus test_cp2.py. die_plan pytest 126 pass, G0 4/4 unchanged. |
| claude/kv-p7-hubtool-1023 | d2cc287a7 | NO-OP (content already in main) | - | Its tree equals 3773fcc91, which is in main, so a merge would add no content. |
| claude/qc-p6-a0v6-1023 | 21cf43d19 | HOLD (carried by QC-A0) | - | See QC section below. Regenerating main's QC plan with the a0v6 gen_plan hook gives G0 FAIL. |
| claude/qc-p6-ftc-1023 | 3a1e9ffa2 | HOLD | - | Pre-ruling (19:17) coll_ftc on tap_mode 'sinks' only. Main's QC plan was later rebuilt by qc-p6-r8/qc-p6-g0c (22:59), and CP1 r8 RULING 21:26 makes grid taps the default (sinks only as additions). A textual merge would mix two generations of a generated die_plan.json. Its tools/die_plan part (kv-p6-tap) is already in main. The GR8 PASS record for coll_ftc g3h is merged. The QC lane must port the coll_ftc tap and station change onto main's gen_plan.py and regenerate. |
| claude/hbm-arch-1023, tokj-kvslice-1023, kv-p7-v38-1023, core-hbm-1023 | - | NOT TOUCHED | - | WIP / stopped, per the plan. |

## Post-05:08 branches the plan's queue did not list

| branch | tip | decision | reason |
|---|---|---|---|
| codex/hbm-token-0936-1023 | 1c729e419 | RECORD-MERGE | See above. |
| codex/plan-g2-path-0858, geom-hbm-source-0944, hbm-plan-sourcepin-0944, qc-taps-0931, kv-forwarding-0911 (-1023) | 44ee3adc9, 0737df774, 06f7a3330, 1c1a1622e, 7585b6a87 | NO-OP | Every commit is patch-equivalent in main (git cherry). |
| claude/kv-p6-boot-1023 | - | contained | Inside kv-p7 (merged). |
| claude/kv-p6-v37-1023 / kv-p6-pv-1023 | 0ec5c902d | HOLD (superseded) | First-proof PV pad table. KV-P7 states the table was withdrawn (PV_CHECK FAIL 14 on kv39). The plan's "kv-p6-* leave" applies. |
| claude/qc-a0-1023, qc-a0v2..v5-1023 | - | contained | Inside qc-p6-a0v6. |
| claude/kv-p3b-ftst-1023 | 1f38e5d02 | HOLD | 10:50 gen_phys PROPOSAL for PLAN-TOOL2, never adopted. Later station tooling in main supersedes it. |
| claude/plan-s81v4-1023, plan-s81v3-1023 | 8f948effa | HOLD (superseded) | S81 plan v4 early; main has v4.8. |
| claude/plan-hbmv2-1023, plan-hbm-1023 | a624978f3 | HOLD (superseded) | HBM v2; main has the P7 fallback; HBM-ARCH owns the redesign. |
| claude/kv-p3-1023 | 87f498afe | HOLD (superseded) | 0 unique patches; kv-p3b/kv-p3-rtl merged. |

## Unpushed lanes recovered from old scratch
Skipped: coordinator cancelled the request (old scratch wiped by owner order 07:03 PDT) before the list was made.

## QC section (ROOT-MERGE resumed 2026-10-24 07:20 PDT after the coordinator restart)
- The killed agent left ~/wt/root-merge mid-merge of qc-p6-a0v6. Its die_plan.json was rewritten at 07:03:22, the minute it was killed, so that run may not have finished. I re-ran `physical/die_plan/qwen_compute/run.sh` cleanly in two trees:
  - origin/main 8a5d1f3dab alone: die_plan.json comes out byte-identical to the committed file. G0 PASS, 0 errors, 88 warnings, G0C 52/56.
  - main merged with a0v6 (gen_plan.py +3 lines that call a0_core_taps.declare): G0 FAIL, 404 errors, all check=clock, "clock tap ... outside the outline". By type: sle_su_c 82, slw_su_c 82, and 60 each for sle_su_l0, sle_su_l1, slw_su_l0, slw_su_l1. Report: ~/coord/evidence/root-merge/qc-a0v6-on-main_g0_report.json
- Decision: HOLD. I aborted the merge (`git merge --abort`); ~/wt/root-merge is clean at df641549db. a0v6 declares its taps against the pre-g0c QC plan (19:28). Main's plan was rebuilt later (qc-p6-g0c 22:59, SU split into hard cores, grid taps by default).
- The kits and tools (physical/ref_tile/qfd_tile_n*_a0c*, tools/qwen_romleaf/*) are new files only and conflict with nothing. They travel with lane QC-A0 (claude/qc-a0-1024, merge a34546df17), which owns the A0 re-kit.
- WARNING for QC-A0: a34546df17 took the a0v6 gen_plan.py hook and the plan_notes a0_core_taps hunk, but kept main's die_plan.json without regenerating it. The committed plan therefore does not match its generator, and regenerating it gives G0 FAIL as shown above. Before asking to merge: fix the a0_core_taps declaration for the current plan geometry, or drop the hook, then run run.sh and get G0 PASS.
- Merge requests: lanes append `MERGE REQUEST: <branch> @sha <claim>` below. ROOT-MERGE checks this queue every ~10 min.

## Merge requests

- 07:58 PDT: no merge requests in 30 min of polling. ROOT-MERGE stopped; relaunch the lane to review new requests.

## CODEX notes
- CODEX root integrated shared fixes d311adaf53,44c10ec34d,34a5e602dc,acfb8a36e7,8232aca585; plain merge and HEAD==origin/main checks passed. Remaining plan/core work owned by grouped agents; no queue item orphaned.
READY [QC 2026-10-24 19:33 PDT] claude/qc-g0fix-1024@9aceac11be: QC main G0 FAIL (R8 landing digest e56a vs c56f) -> PASS 0 errors; r8/bus_groups.json = qcp6_status_bind_v5 (f4f98b), landing regenerated (same pads 248,396), 6 files under physical/die_plan/qwen_compute only, 0 deletions
- 2026-10-24 19:36 PDT ROOT-MERGE: relaunched on rtx-pro (worktree ~/wt/root-merge-1024r). Baseline main d13ff7c78: pytest 251 pass/2 skip; G0 s81 0 err, s81_head 0, qwen_compute 1 (known R8), qwen_kvsys 0, hbm_arch/B2l 0. Merging only lines marked [COORD ...] APPROVED at the approved sha.
READY [GEOM-REVIEW 2026-10-24 19:38 PDT] claude/geom-review-1024@44d36293aa: GEOM-REVIEW records only (7 S81 g3k5 frame FAIL records + tile_1024g3k5/README.md under results/geom_review/); merged origin/main d13ff7c783 (ff), 0 deletions
READY [S81 2026-10-24 19:39 PDT] claude/elem-s81-st405-1024@c46038b443 (superseded by @2cb4732766 below): station405 B verdict records (14 signoff.json + verdicts.json + 2 pair_skew.json under results/elem_s81_station405/B_1024; 6 SIGNED / 8 NOT SIGNED), author geom review FAIL record, opt-in gen.py phys --max-wire-um (tools/die_plan/grt_maxwire.tcl; default kits byte-identical; test_g2/test_check/test_schema/test_signoff pass); 0 deletions
READY [GEOM-REVIEW 2026-10-24 19:42 PDT] claude/geom-review-1024@bb60cdada2: supersedes earlier GEOM-REVIEW READY shas; GEOM-REVIEW records only (7 S81 g3k5 FAIL, 3 S81/KITS cores, KV hub_Ei vK plan PASS-COND, ST405 t11 tool-validation PASS-COND, KV qkd_ahub FAIL, S81 xdie plan PASS-COND, HBM B2l 9 families PASS-COND, HBM B2l 91 split views probe PASS-COND) under results/geom_review/, 0 deletions
READY [TOK-DS 2026-10-24 19:49 PDT] claude/tok-ds-pads-1024@e7d749213: S81 R8 landed-bundle pads priced into lat table of record (COORD 18:55 ruling): gen.py latency --fold-r8 (base + r8_pad columns; without the flag byte-identical to main), lat/s81_latency.json + s81_lat_pkg.sv regenerated on current plan digest 87f0256809a93f1e (2 runs byte-identical), die_ci latency check compares cycles-r8_pad; 26 lanes padded (max 13, mean 5.9; x/xo over-margin bundles; xring/sid 0); compose 1u AR 1,520,806 cyc = 789.1 tok/s (was 802.6 on b4ac table; plan regen -23,063 cyc, pads -2,610), MTP 2,528.6, MU AR50 39,453 / MTP6 15,172; die_plan pytest 254 pass, compose --selftest/--check PASS, G0 s81 PASS 0 err (rtx-pro); touches tools/die_plan/{gen,r8,die_ci,test_check}.py (shared with S81) + physical/die_plan/s81/lat/ + results/token_pass/tokds_compose_r8pad_1024; 0 deletions
READY [RESET 2026-10-24 19:54 PDT] claude/cp1-r10-1024@f5c549e166: CP1-R10 pair.py reach-aware proof leaf (6435e46354; r1 TT -241.76 -> +192.55) + reach405L die seam STA records (seam PASS TT +434.46 / FF +95.08) + review record; test-merged with origin/main d13ff7c78: clean, die_plan pytest 253 pass (1 sparse-checkout-only fail), 0 file deletions
READY [HBM 2026-10-24 19:58 PDT] claude/hbm-1024r@9ef5eebb2: tools/die_plan/gen_phys.py exact plan origins (TRIAL-HBM %g bug, 23/88 refused) + die.pg.domains schema/check (decision 7) + hbm_b2_ir --domain + new plan physical/die_plan/hbm_arch/B2m (G0 PASS, G0C 49/49 0 err). Tests test_g2/cp2/face_guard/die_ci/schema/xdie/check/xdie_io PASS. 0 deletions except tools/die_plan/reset_tree.py is NOT on main (never merged). Note: schema.py/die_plan.schema.json touched (pg.domains only).
READY [S81 2026-10-24 20:01 PDT] claude/elem-s81-st405-1024@2cb4732766: station405 B verdict records 18 of 34 (7 SIGNED / 11 NOT SIGNED) + author FAIL geom record + opt-in gen.py phys --max-wire-um (default kits byte-identical; die_plan tests pass); records/tool only, 0 deletions
READY [QC 2026-10-24 20:02 PDT] claude/qc-cap-1024r@78992be86f: QC capacity plan (owner-accepted) + lane_eq + ft_regs + serdes 5 stations; G0 PASS 0 err, G0C 56/56; R8 groups = probe bind of this plan (f23550b0); test_r8/test_g2/test_bind PASS; merge-tree clean; 0 deletions. Contains 9aceac11be (G0 fix) -- merge either.
READY [S81 20:07] claude/s81-kits-geom-1024r@35b3b97ba: S81/KITS: dsfd_node_LLd native view SIGNED (TT +17.39 / FF +5.27, DRV/DRC/ant 0, pins 195/195, face_guard PASS raw w/ no-op hook; GEOM-REVIEW PASS 19:39) + author geom records l5f/LLd/cfg7_seq. Adds only physical/die_plan/s81/cores/views/dsfd_node_LLd/ and results/geom_review/s81_kits_1024r/; 0 deletions.
- 2026-10-24 20:15 PDT ROOT-MERGE: PRE-CHECK (no approval yet) claude/qc-cap-1024r@78992be86f: tools/die_plan pytest FAILS test_cp2.py::test_tcl_hooks_complete (line 283 asserts '^clk(_t[0-9]+|_c[0-9]+)?$' in tap_balance.tcl; the branch's tap_balance.tcl (OT_TAP_PORT family from qc-a0) no longer contains it; main and every other READY tip pass). Fix the test or the tcl, rerun the FULL tools/die_plan pytest, re-post READY. Other READY tips (geom-review@bb60cdada2, elem-s81-st405@2cb4732766, s81-kits-geom@35b3b97ba, cp1-r10@f5c549e166, hbm-1024r@9ef5eebb2, tok-ds-pads@e7d749213) test-merge cleanly together on main d13ff7c78, 0 deletions, G0 5/5 0 err. qc-g0fix@9aceac11be alone: all pass.
READY [RESET 2026-10-24 20:16 PDT] claude/reset-1024@d1152532c: unified pipelined reset (OWNER RESET RULE, decision 2) = tools/die_plan/reset_tree.py (one root ot_dp_rsync per die region at the die rst_n pin, synchronous ot_dp_rrelay hops <= 405 um, equal depth to every tap; partitions take arst_n as a SYNCHRONOUS input: pin register u_rst_in + equal-depth tree K) + schema reset.{release pipelined,relay_um,part_depth,regions} + G0 check (errors on hop/depth when pipelined; WARN on counted plans) + gen_rtl (partition + die top) + kit_rsync.py (bound kits, idempotent; supersedes KV 6ecd9a39e2 and S81 71bed19a4a rpipe) + gen_phys reset_tree.tcl (FIRM relays, OT_RESET_TREE placed-hop PASS/FAIL) + test_reset_tree.py (8, incl. iverilog release-cycle sim). die_plan pytest all pass; G0 PASS all 6 die plans on this branch (qwen_compute 1 err = known R8 digest). Plans stay counted (no plan switched); 0 commits behind origin/main. Supersedes KV-G3 reset_tree WIP.
WITHDRAWN [QC 2026-10-24 20:16 PDT] claude/qc-cap-1024r@78992be86f: final CB16 bind found io_serdes_2 RX bundle (rx_flit/rx_v 10 vs tx_up 12 after the owner +1 serdes stations) -> coll_regen error; lane_eq now equalises PHY bundles; new READY follows after bind+verify. claude/qc-g0fix-1024@9aceac11be stays READY.
READY [HBM-ELEM 20:21] claude/elem-hbm-1024@77ad44e788: core clock contract - results/core_insertion_b2l.json (281 views, 136 measured I, early_tap=max(0,I-250)) + gen_core_kit_hbm.py IO vclk latency = I (no other SDC/margin/corner change), run_kit_hbm.sh signoff fix (TC_LIB parse, GOAL=post), hold_cap -max_iterations, launch.sh via ot-run --dir (no --hosts); B2l route verdicts. Merge tool changes only; no core SIGNED yet.
READY [RESET 2026-10-24 20:22 PDT] claude/reset-1024@3b5eba8d1: supersedes @d1152532c (adds: face_keep dont_touch on reset relays -- eliminate_dead_logic deleted relay chains to unloaded taps; placed-hop gate FAILs on any missing relay). Tests pass.
