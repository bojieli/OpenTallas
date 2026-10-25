# PART-CAP (branch claude/part-cap-1024, worktree ~/wt/part-cap; server worktrees ~/wt/part-cap on epyc2/epyc3/intel1/intel2)
Goal: origin of the 400k cells/partition cap; measure ORFS/OpenROAD scaling ASAP7 833 ps at ~0.4/0.8/1.6/3M cells;
recommend max partition size. Measurement only (no die-plan edits). Results -> results/arch/part_capacity_1024/.

Vehicle: N x closed ot_qkh_lane8 (KV hg/hgi content, ~114k cells each, TT +102 ps closed) in ot_pc_rep (systolic input
delay chain + registered XOR output chain), production tools/ref_tile/ref_route.sh, RLAYERS M2-M7, PD 0.6, 770 ps route
/ 833 ps signoff, NC=48 threads. Kits results/arch/part_capacity_1024/kits/pc_rep_n{1,4,7,14,27}.

Runs (n1/n27 started 07:20; n44 07:26; n14 re-started 07:31 and n4/n7 07:37 after the intel1/intel2 worktree mover deleted /src under a running container, ot-run clients on localhost, logs ~/coord/part-cap-logs/):
- n1  (69k synth) epyc2 DONE 41.5 min, 77.7k placed, DRC 0, TT +214.5 / SS -64.3 / FF +3.6, peak 13.1 GB
- n4_t16 (275k synth, NC=16) epyc2 /srv/opentallas-scratch/claude/part-cap/pc_rep_n4_t16 --mem 48 (thread-scaling check)
- n4  (275k synth) intel1 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n4   --mem 64
- n7  (483k synth) intel1 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n7   --mem 100
- n14 (~0.97M synth) intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n14  --mem 200
- n27 (~1.86M synth) epyc3  /srv/opentallas-scratch/claude/part-cap/pc_rep_n27   --mem 300
- n44 (~3.04M synth) intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n44  --mem 400 (added 07:27: lane8 synthesizes to 69k cells, so n27 = ~1.9M)
Stop: `ot-run --cancel part-cap` (my dirs only).

Origin of 400k (step 1, done): CORE_CELLS_MAX=400_000 added by c6376fe8a8 (COORD 10-23 19:36 "CORE-KS"); first used in
KV plan v3 9292db97f4 (10-23 06:32: "CAP MEASURED 06:1x: 400k std cells per OpenROAD run, 500k ceiling");
physical/die_plan/hbm/collect_cells_v2.py cites "or_capacity_runs.csv from the 06:12 L1-cap study" -- never committed.
Committed history: routed 0-DRC flat runs up to 1.39M cells (nearhbm hub_r7 9.8 h, GRT 24 GB, 20 cores); 832k routed
setup +6.6; no OOM or GPL-0307 on a large flat run; failures >400k are design timing / setup errors / wall-clock timeouts.

FLEET NOTE: ~/.local/opentallas-pdk-asap7 (run_abi3_physical.py liberty root) was MISSING on all 4 servers; installed
lib/NLDM RVT TT/SS/FF from the pinned ORFS image (gunzipped) on epyc2/epyc3/intel1/intel2.

Finding so far (08:20): floorplan `repair_timing -repair_tns 100` (production OT_TNS_END_PERCENT default) is single-threaded
and superlinear: n1 ~120 s, n4 1041 s (2364 violating endpoints, SS-corner route), n27/n44 still in it after 50+ min.
Next: when n4 frees intel1, run pc_rep_n27_tns10 (repair_tns 10) to price that knob at scale.

## CODEX notes
- 2026-10-24 09:01 PDT: CODEX took over N27 TNS10 on codex/part-cap-1024 @49bab34289. Prior failed pilot missing kit on stale remote worktree (kit already tracked on source branch). Driver now supports isolated PART_CAP_WT. Own reviewed kit/source staged intel1 scratch2. Local queue cancelled (no job started) to use idle intel1 headroom.

## CODEX notes
- 2026-10-24 09:34 PDT: Own N27pilot stopped exact container e3961727da9c due inheritedSSdefault; partialfilespreserved, no other jobsstopped. Driver now defaults CORNER=TC, newpc_rep_n27_tt_tns10 signoff833.000ps. OriginalN4/N7/N14/N44stilllive/partial,notclaimedclosed.

## RESUMED 12:15 PDT (after 08:50-12:04 usage limit)
Adopted: Codex pc_rep_n27_tt_tns10 (intel1:/srv/opentallas-scratch2/claude/codex-part-cap/pc_rep_n27_tt_tns10, local
ot-run PID 1888477, CORNER=TC route, TNS10, 48 thr, signoff 833.000) -- will collect, not relaunch. claude/part-cap-1024
fast-forwarded to codex/part-cap-1024 fef34728ce (run_one.sh now defaults CORNER=TC; PART_CAP_WT override).
My originals (CORNER=WC = ref_route default, repair_tns 100): n1 DONE, n4 DONE, n4_t16 DONE, n7 DRT, n14 CTS,
n27 GPL, n44 STILL in floorplan repair_timing after 4h45 (single thread).
- 12:13 launched pc_rep_n44_tt_tns10 on epyc3 (/srv/opentallas-scratch/claude/part-cap/pc_rep_n44_tt_tns10, --mem 300,
  48 thr; Codex n27_tt_tns10 recipe at N=44). Reason: original n44 (WC, repair_tns 100) is at endpoint ~3350/26049 of
  floorplan repair_timing after 4.8 h (n27: floorplan 3h41; n4: 20 min) -> extrapolates to >1 day of floorplan alone;
  kept running (not restarted), its rate is the evidence.
- n4 DONE: 304.7k placed, DRC 0, TT +164.0 / FF +1.55 / SS -14.4, 3.6 h (48 thr, intel1 overloaded) / 2.8 h (16 thr epyc2), peak 38 GB DRT.
- 13:25 NOTE: intel1 load avg 540 on 112 cores (other lanes' docker routes) -> n7 / n27_tt_tns10 wall times on intel1 are contention-inflated; report CPU-s per step alongside wall.

## PARKED 2026-10-24 18:58 PDT
Branch claude/part-cap-1024 @1381120171 (pushed; includes Codex codex/part-cap-1024 fef34728ce). Not merged to main yet (no README/report yet).
Live jobs (keep running; ot-run clients on localhost, logs ~/coord/part-cap-logs/):
- n14   intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n14          (WC route, tns100) in GRT
- n27   epyc3  /srv/opentallas-scratch/claude/part-cap/pc_rep_n27           (WC, tns100) in 3_4 place_resized
- n44   intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n44          (WC, tns100) in GPL (floorplan took ~7.5 h)
- n44_tt_tns10 epyc3 /srv/opentallas-scratch/claude/part-cap/pc_rep_n44_tt_tns10 (TC, tns10) in GPL (floorplan 37 min)
- n27_tt_tns10 (Codex, adopted) intel1 /srv/opentallas-scratch2/claude/codex-part-cap/pc_rep_n27_tt_tns10 (local PID 1888477) in DPL
Results (runs/*.json via results/arch/part_capacity_1024/collect.py RUN_DIR on the host):
- n1  77.7k placed: 41.5 min, peak 13.1 GB, DRC 0, TT +214.5 / FF +3.6 -> closes (SS -64 info)
- n4  305k: 3.6 h (48 thr, contended) / 2.8 h (16 thr), peak 38 GB, DRC 0, TT +164.0 / FF +1.55 -> closes
- n7  535k: 8.5 h (intel1 load ~540/112), peak 44.8 GB, DRC 0, TT +184.2, FF hold -19.5 (181 pins) -> FAIL hold
Findings: no memory wall (DRT peak ~85 GB/M cells, everything else <15 GB); DRT is the only stage using >10 threads;
floorplan/CTS/GRT repair_timing + 6_report are ~1-3 threads and dominate wall time; floorplan repair_timing -repair_tns 100
at the WC (SS) route corner is superlinear (n1 2 min, n4 20 min, n7 53 min, n27 3h41, n44 ~7.5 h; 26,049 violators at n44)
vs 4.4 min at TC + repair_tns 10 (396 violators). 400k cap origin: COORD 10-23 06:1x "L1-cap study" (closed-run census
or_capacity_runs.csv, never committed) -- no failure behind it.
Next: collect n14/n27/n44/n44_tt_tns10/n27_tt_tns10 when done; check n7 FF-hold cause (vehicle chain flops vs size);
write README (stage table, scaling fits, recommendation, plan_census.py seam/type table, knobs) and merge.
OWNER?: none.

## CODEX notes 2026-10-24 21:10 PDT — PARKED for Claude reset
CODEX took over collection on codex/part-cap-collect-1024 from claude/part-cap-1024@1381120171. No new heavy jobs launched.
- N14 intel2 route complete DRC 0, 1,067,746 cells, peak container 57.8 GB; final FF corner STA still live. Physical old WC-route verdict NOT_MET, not SIGNED.
- N27 TT/TNS10 intel1 FAIL before GRT: sparse source missing physical/hbm_accel_die_views/stations/bench/stn_pin_keepout.tcl. Missing 6_final.sdc is downstream, NOT congestion or OOM. Existing 3_place floorplan+density viewed: macro-free square, density near 0.5, no hotspots; source-only checkpoint resume review written results/geom_review/part_capacity_n27_resume_1024.json in own tree. Resume NOT LAUNCHED.
- N7 FF -19.52 is input-to-reg boundary hold; reg-to-reg +3.18, output +45.55. Input q_data/e/row to replica0/input chain; asynchronous reset removal also -3.47ps. Structural capacity is not the cause; next vehicle must use current pipelined reset and proper FF boundary hold repair. No timing/SDC waiver.
- Original N27 epyc3 now GRT; N44 intel2 and N44 TT/TNS10 epyc3 now DPL, all retained. Original top flow.log is buffered; check work/orfs/logs/.../*tmp.log for live progress.
- Fresh collected JSON snapshots and copied inspected images: /srv/opentallas-scratch/claude/codex-part-cap-collect/. Own sparse worktree /srv/opentallas-scratch/claude/wt/codex-part-cap-collect; remote own sparse worktree creation intel1 /srv/opentallas-scratch2/claude/wt/codex-part-cap-collect in progress, no route started.
Next: finish own source checkout, include missing pin-keepout Tcl, resume N27 from copied checkpoint via ot-run; collect N14 final STA and three original live runs, write concise capacity recommendation/report. OWNER?: none.

## CODEX notes 2026-10-25 02:38 PDT
CODEX took over: pending collection and N27 source-only resume on codex/partcap-1025@ee919dc4e (pushed; based on claude/part-cap-1024@1381120171). N14 complete: 1,067,746 cells, DRC0, TT +66.33 / FF -25.29 ps (117 D pins), peak57.8GB; FAIL boundary hold (r2r -0.18, outputs +80.23), not a memory capacity limit. N27 old GRT and N44 WC/TT CTS remain live, no duplicate/cancellation. N27 TT/TNS10 root cause confirmed omitted stn_pin_keepout.tcl. Viewed floorplan+density again (uniform ~0.5, macro-free square, continuous stripes); review results/geom_review/part_capacity_n27_resume_1025.json. LAUNCHED isolated checkpoint resume via ot-run PID3493114 (local client; tool session79911; unit oth-ubuntu-1462271-1792921126), intel1:/srv/opentallas-scratch2/claude/codex-partcap1025/n27_resume, exact container codex-partcap-n27-1025, 128GB/32t; own complete sparse source /srv/opentallas-scratch2/claude/wt/codex-partcap-1025. In-flow hold margin corrected10->5ps per owner; original failed directory preserved. Log local ~/coord-scratch/partcap1025/ot-run.log and remote n27_resume/route_resume.log. Next collect resume and 3 inherited jobs; no owner question. Capacity report on branch; no SIGNED claim.

2026-10-25 02:40 PDT CODEX failure diagnosis: inherited N44 WC (intel2) and TT (epyc3) are RUNAWAY CTS hold loops, NOT normal CTS progress. TT now ~209,630 iterations / 220,477 added buffers, WNS frozen -226.761 ps/TNS -49,557.688; WC ~189,770 / 201,266 buffers, WNS -534.626/TNS -133,074.516. TT initial true hold violations16,753 / WNS-226.76; margin10 adds ~224k targeted endpoints. Both exceed owner's post-CTS structural stop rule and need boundary/reset/clock correction before more repair. Inherited jobs retained under no-kill rule. Original N27 WC GRT also repeats WNS-269.654/TNS-67,737.977. Own N27 TT resume is distinct: completed CTS true hold violations0, WNS+8.80, though setup-234.642 at 770ps routing target; current GRT and TT833 setup decide acceptance. No SIGNED claim.

2026-10-25 02:43 PDT CODEX: global runaway cause fixed on codex/hold-stop-1025@666c6ac70 (pushed; parent/root assigned this shared tool): ot_repair_timing now calls ot_hold_structural_gate before hold repair, true min WNS<-100ps or >2000 negative endpoints -> hard error/report; setup-only unchanged. Gate does not use margin-expanded endpoints. Five real-Tcl/mock-STA fixtures PASS plus existing39 hold-stop tests PASS. Generic kit runner counterpart owned by /root/clock_reset/cp1. N27 checkpoint resume remains live intel1, no inherited jobs cancelled.

2026-10-25 03:16 PDT CODEX N27TT source-only resume stillLIVE pinaccess~300kgroups; sourceinclude faultcleared. Ownwatchguardian intel1PID1406779 reads only n27_resume/route_resume.log; exact ownedcontainer/mountguard stops codex-partcap-n27-1025 on true FFhold<-100 or >2000violators, writesguard_structural.json. No arbitrarytimeout; inheritedN44/N27jobs untouched.
2026-10-25 03:16 PDT INFRA -> PART-CAP: epyc1 root disk (owner: no work on root): your LIVE item(s) still on the ROOT md0: ~/wt/part-cap (ot-run run_one.sh clients). When the job ends, move it to the same path under /srv/opentallas-scratch2 (bash /srv/opentallas-scratch2/claude/infra-pass4/move_one.sh <path> -- copies, checks liveness, git worktree repair, symlink back) and create new run dirs/worktrees only under /srv/opentallas-scratch2/claude/.
