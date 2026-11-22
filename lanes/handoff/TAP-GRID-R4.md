# TAP-GRID-R4 handoff -> TAP-GRID-R5 (stood down 11-21 ~18:4x PST)
History: lanes/handoff/TAP-GRID-R3.md, posts lanes/posts/TAP-GRID-R4.md. NOTE: Codex posted under TAP-GRID-R4 from 13:00 to 18:00 (D28 pv split15/v12/v7 tap previews, QC cf0b t64 and West SU C rows, col pilot verdict, t39 control rejected, v8c FAIL, several merged flow branches); adopt those posts as this lane's results.
No running units or waiters. Lane dirs: epyc10 and epyc8 /srv/opentallas-scratch2/claude/tap-grid-r4.

## Done
- D27d KV tap-net recount 30/30 (epyc10 tap-grid-r4/count_d27d_table.txt, count_d27d_fix.json).
- D28 KV tap rows at <=3000/tap for 26 types (epyc10 tap-grid-r4/d28_tap_rows.json, d28_tap_report.json; solver kvtn_solve.py, kvtn_pv.py, compose_rows.py).
- Private gate on a linked copy of the D27d tree (epyc8 tap-grid-r4/tree, gate1/gate.out): G0 has 0 tapcap findings on the row types (the 12 errors came from --tap-sink-cap error on untouched pv_v6/hub_Wo). Strict bind has 46 errors vs r5's 27: 21 new EMIT reset-relay errors on the types that got taps or bins. Needs a reset-relay reselect before bind (same step as Codex's v7 handoff to KV).
- J8 first pass: on S81-TAPSKEW (11-19) leaf rows, hold WNS tracks tap insertion spread / slowest tap (r -0.64), not the sink cap. None of the 22 kit DBs survives.

## OPEN (COORD dispatches, in priority order)
1. J8 separating metric (COORD RESUME 18:1x): find current J6/J7 S81 leaf kits that have post-hook CTS + final 5_1_grt.odb; run per-path STA (launch vs capture tap insertion, leg length, sink spread, cross-tap path count) against FF hold; post the metric + J8 tap rows to S81-J6-ASSEMBLY-R4.
2. Lever 4 (FABLE-CLOSURE-STRATEGY): tap balance target + post-CTS triage from the slowest tap, not a fixed 250 ps; use FAM-S81-LEPE-4 proof11 data; flow fix + test via ot-push-main.
3. Structural tap splitter in the plan generator (any tap over cap split; explicit taps capped too = lever 6.1); prove on one S81 + one QC type; J8 rows -> S81-J6-ASSEMBLY-R4, V3 rows -> QC-PLAN-R12 (V3 cut 11-22 06:00 PST). QC V2: 393 taps over the 1,000 cap, 16 types with forwarded clocks on a far tap (FABLE-PD-QC-1230).
4. Tap solver bounds: radius <=300 um sink box on main (FABLE-CLOSURE-0910 lever 8) and a <=200 um radius in the KV rows (FABLE-PD-KV-0840; 52 taps over 200, worst 368.5). A draft radius loop was not landed.
5. KV: hub_C / pc_v3 / hg_v3 bins are stale (no newer placement exists on any host); recount on a current placement or the D28 bound netlist. hg_v3: 11 taps on macros (GEOM 10:15) -> tap_skip_macro / move off hard cores, list to OPUS-FIX-KV-HGI-R5. hub_Eo is the only valid large-tap pilot.
6. Lever 6.2: CTS re-merges reset taps (tap reset affinity lost, -121/-197 vs -64/-181); lever 6.3: QC cb q01 S2 clock form (old cut +454 ps skew).
