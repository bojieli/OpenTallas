# HEAD plan event CA-OCV-K (DIE-HEAD-10, 2026-10-28 08:0x PDT) -- 12.16b on the kept local spine

COORD 08:0x / CLK-LOCAL-EST-1: HEAD is already the local form (spine + fishbone; 12 spine/service roots feed 298 child regions
one level down). KEEP the spine; no re-tree, no die-wide clock build. The fix is K/DEPTH from the OCV-inclusive plan-time bound
(12.16b(ii)/(iii)) and, when START-TREE-1 lands, a fork start port on the one ambiguous start edge.

## Inputs (unchanged from the CA-OCV-1 sweep, so the numbers compare 1:1)
- ocv rows   intel2:/srv/opentallas-scratch2/claude/die-head-5/sta/ocv_spice.json (landed_phase_ocv, spice x1.0485)
- proof      intel2:/srv/opentallas-scratch2/claude/die-head-5/sta_ival/proof (tap arrivals TT/FF, droop_regions.json)
- plan       die_plan_root_sp5.json (die-head-1 WT = main c95bdf4bf9 content)
- parts map  parts[p].region = p from die-head-7/sta_qc5/bind_idreg.json (HEAD region = partition)
- tools      main (CA-OCV-1 5e8f1cb75 is on main): count_align_plan / count_align_bind / die_sta_related

## Commands (run_ca_ocv.sh)
    count_align_plan ocv_spice.json --mc-chips 2000 --start-skew 57.5,89.7 --sta-proof P --sta-plan J --sta-clock-cal spice
        --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions P/droop_regions.json
        --sta-core-latency-ff 202.5 --out plan_ocv.json
    count_align_bind plan_ocv.json --parts region --out bind_ocv.json   (+ parts from bind_idreg -> bind_ocv_idreg.json)
    die_sta_related P --plan J --corner TT --corner FF --core-latency-ff 202.5 --droop-regions P/droop_regions.json
        --count-align bind_ocv_idreg.json --count-align-key region --clock-cal spice --cppr-lca --clock-ocv table --clock-droop shared

## Result (CHECKED, own runs; NUMBER-CHECK by an independent lane still open)
| run | D4 / D8 / FAIL | TT worst lo | FF worst lo | <100 | start-skew TT/FF | max OCV TT/FF |
|---|---|---|---|---|---|---|
| plan, no OCV (baseline = sta_ival, reproduced) | 427 / 0 / 0 | 134.7 (plan) | - | 0 | - | - |
| CA-OCV-1 gate on the OLD K (reference) | - | 78.6 FAIL (4) | 112.4 | 4 | 1/325 / 0 | 212.9 |
| plan with OCV table (this event) | 420 / 7 / 0 | 132.2 (plan) | - | 0 | - | - |
| gate, clock_variation=table, NEW K | - | 132.1 PASS | 168.2 PASS | 0 | 0/325 / 0/325 | 212.9 / 176.6 |
| gate, clock_variation=none, NEW K (info) | - | 249.7 | 264.3 | 0 | 0/325 | - |
SS-INFO (TT x1.27, never gates): worst lo 70.3, 4 fail, start-skew 20/325 -- info only, as before.

## The delta (7 of 427 crossings, all on the one sp2 <-> sp3 spine edge; every other K/DEPTH byte-identical)
| port | dir | K old -> new | DEPTH old -> new | lat cycles |
|---|---|---|---|---|
| sp_x3__0, m0S_tx__3, m7S_tx__3 | sp2 -> sp3 (tree edge) | -1 -> -1 | 4 -> 8 | 3 (unchanged) |
| sp_b3__0, host_rx__3, m0S_rx__6, m7S_rx__5 | sp3 -> sp2 (1-edge loop) | 4 -> 6 | 4 -> 8 | 2 -> 4 (+2) |
Cause: the start-tree edge sp2 -> sp3 (host_tx__3, fall edge) is the one ambiguous start edge (sync_dist 91.6 ps with OCV,
2 sync values = 1 cycle of ambiguity); the planner covers it by construction with DEPTH 8 and K from the bound. 12.15a: ring
DEPTH stays a per-type parameter (largest any instance needs), so the hd_spn-family bus rings of these 7 buses become D8.

## Reset release (12.16b(iv)): start-skew 0/325 TT and FF with OCV (was 1/325 TT = the same host_tx__3 edge).

## Open (not in this event)
- START-TREE-1 fork start port on sp2 -> sp3: should remove the 1-cycle ambiguity (D8 -> D4 on these 7, sp3->sp2 +2 -> +0/+1).
  Fold in when START-TREE-1 publishes its --start-tree option; the D8 form is safe without it.
- +2 cycles on the sp3 -> sp2 return path: static schedule / token latency UNCHECKED (12.15c accepts added crossing latency).
- 1 crossing (host_tx__3, the tree port itself) is timed by the plan-sync model (source plan-sync), not by an STA pair.
- Apply: compose / landed sidecar regen with bind_ocv_idreg.json (strap ties change only on these 7 buses: strap_ca_k + depth),
  then gen rtl + strap_lec per variant, then the gate re-run on built arrivals before freeze (12.16d).

## Update 2026-10-28 (COORD: START-TREE-1 approved, claude/start-tree-1-1028@91c2e9fec3, --start-tree clock) -- PLAN OF RECORD
Same inputs + `--start-tree clock` (tools from 91c2e9fec3; run_ca_st.sh, outputs start_tree/).  The start (reset-release)
tree now follows the clock tree with one dedicated start port per clock-tree edge; the spine is kept (no rebuild).
| | OCV-K (above) | start-tree clock, --start-clean phase (RECORD) | --start-clean width (stricter, info) |
|---|---|---|---|
| DEPTH hist | D4 420 / D8 7 | D4 427 / D8 0 | D4 427 / D8 0 |
| lat_hist | 2:256 3:167 4:4 | 2:256 3:171 (the +2 is gone) | 2:256 3:171 |
| start tree nodes (stages with a plan home) | - | 42 | 170 |
| start edges / clean / fail | 325 / 324 / 0 (1 ambiguous) | 367 / 367 / 0 | 495 / 495 / 0 |
| retime edges | - | 1 | 16 |
| max start-tree depth | 27 | 9 | 19 |
| min clean sync dist / skew limit | 126.0 / 99.5 ps | 104.4 / 77.9 ps | 119.9 / 93.4 ps |
| gate TT / FF worst lo (die_sta_related, ocv table, droop shared) | 132.1 / 168.2 | 132.1 / 168.2 PASS, start-skew 0/367 | 132.1 / 168.2 PASS, start-skew 0/495 |
| <100 ps | 0 | 0 | 0 |
SS-INFO (TT x1.27, never gates): worst lo 70.3, 4 fail -- unchanged.  All numbers CHECKED (own runs, intel2
/srv/opentallas-scratch2/claude/die-head-10/ca_st_{phase,width}).  K values differ from the OCV-K bind on 367/280 ports
because origin cycles follow the new start tree; DEPTH is D4 everywhere, so the 7-bus D8 delta above is WITHDRAWN.
Record = phase (the CA rule, 42 stages); width costs 128 more stages and 16 retimes for +15.5 ps start sync distance.
Open: the 42 start nodes need their physical home in the plan (START-TREE-1 emits fork_node per edge = clock-tree node);
apply via compose / sidecar regen with start_tree/bind_st_phase_idreg.json, gen rtl, strap_lec, gate on built arrivals.
