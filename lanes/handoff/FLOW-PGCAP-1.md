# FLOW-PGCAP-1 handoff (EXPERT-REVIEW-4 item: one flow fix for DRT-0255 at PG stripe pairs)
Updated 2026-11-13 PST.

## Fix
Branch `claude/flow-pgcap-1-1113` @ af98cc6b3d (READY re-posted for train L after the helper-order fix; first READY 20:50 PST to ROOT-MERGE-63, COORD-approved on post; evidence HEAD-98 ctl_n DRC 0 / antenna 0, HEAD-99 RESULT 19:55) (off origin/main 4702c3c43a6), pushed. Clone: intel1 /srv/opentallas-scratch2/claude/flow-pgcap-1/wt (sparse: tools, physical/common_flow, rtl).
- tools/die_plan/pg_track_truth.tcl (generalized HEAD-98 hook): temporary GRT obstructions over spacing-illegal tracks of every PG stripe M4..MAX; real track grid; min spacing (width-dependent spacing opt-in OT_PG_TRACK_TRUTH_WIDE_SPACING=1, unproven).
- grt_pre.tcl adds them last when OT_PG_TRACK_TRUTH=1; grt_post.tcl removes them first (before route.guide use / 5_1_grt.odb). DRT/PG/sign-off geometry unchanged.
- gen_phys RFLOW: `export OT_PG_TRACK_TRUTH = 1` for s81, s81_head, qwen_compute, qwen_kvsys (rflow_cfg). HBM off. OT_RFLOW=0 = old kit.
- kit_resume: OT_PG_TRACK_TRUTH is a grt-stage var. core_flow copies the file (off).
- tools/die_plan/pg_track_census.py: read-only census (ODB=..., NETS=...).
- Tests: test_rflow_defaults/test_grt_capacity/test_place_fanout_cap/test_kit_resume 60 pass (epyc7 wtcopy, pytest not on intel1).

## Evidence
S81 leaf__t6 (LEAF-HOLD-1 t6p2 5_1_grt.odb): failing net u_bound.u_ft_ft0_o_5/net199927 M6 guide row y161.88-162.45 has 1 legal track of 9; 3 M7 column guides x68.97-69.54 1 of 9; kit-wide 547 M6 + 178 M7 guides on 0-legal rows (708 nets). Log intel2 ~/tmp/pgcap_t6_census.log.

## Proofs (private, DO_NOT_COUNT, stage-resume grt from the same 4_cts.odb, route->signoff, intel1)
- S81 t6: intel1 /srv/opentallas-scratch2/claude/flow-pgcap-1/proof/t6/gen/ot_s81sl_leaf__t6, log intel2 ~/tmp/pgcap_t6_route.log (unit oth-ubuntu-2041680-1794623505). Before: DRT-0255 at 1:21 h.
- HEAD hd_spn_end (copy of head-97 kits21hfp_rows2, failed DRT-0255 net65853 on M6 pair row): intel1 .../proof/spn_end/hd_spn_end, log intel2 ~/tmp/pgcap_spn_end_route.log (unit oth-ubuntu-2071657-1794623633).
- Kit installs via proof/install_form.sh (same lines as the repo form).
- HEAD-98 runs ctl_n (epyc8) / host_e (intel1) with its own per-kit copy of the hook: not relaunched.

## Proof results (both posted as RESULTs)
- HEAD hd_spn_end (coord 1447591b32a): DRT-0255 gone; DRT 100% with DRC 3, all "Rect Only" on M7 at net rst_start_raw_5's own pin (io.tcl place_pin 318.688 887.784, 0.080 x 0.432): pin-shape class, owner HEAD-98. Sign-off NOT SIGNED: TT +39.14, FF hold -4.32 on 81 (R-CLOCK), antenna 0.
- S81 leaf__t6 (coord 01c82eb9b6b): NOT PROVEN. Iteration 0 at 90% had 97,897 violations vs 115,082 in the reference run, then the process was killed at 5:14 h (make Error 241, intel1 load 362/112). The leaf needs its R-STREET / plan form first.
- Both proofs ran the wide-spacing superset. The branch default is the HEAD-98 min-spacing form (ctl_n DRC 0).

## Status
ENDED (OWNER: after the proofs and READY). Nothing is running. Any rollout, the WIDE_SPACING default decision and the t6 street form go to Sonnet lanes.
