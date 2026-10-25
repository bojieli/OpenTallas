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
