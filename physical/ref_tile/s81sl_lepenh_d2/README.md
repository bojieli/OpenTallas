# s81sl_lepenh_d2 -- dsdv_slice_lepe_nh landed parent, DIAGNOSTIC stand-in kit (successor of s81sl_lepenh_diag)

Lane S81-LEPENH2, 2026-10-20. Release tree S81.STA.OWN.11. **Not bindable, never submit**: every child is a
`tools/qwen_dv/slice_standin.py` abstract (`STANDIN_NOT_A_VIEW`). Rebuild as a real kit (new name) once real child views close.

## Why d2 (d1 = s81sl_lepenh_diag, evidence 08f4a85fd: FAIL)
| d1 finding | cause | d2 structural fix |
|---|---|---|
| 5345 stages > 500 um; child -> pin comb 1331 um (xc) | parent ports spread over whole faces, child pins elsewhere | every parent port RANGED on the face its child pin faces: straight 43.2 um abutment hop (S/N/W buses mirror the slice ranges +43.2) |
| slice E line ports span 1382 um vs lep W 475 um | funnel into the lep | slice ro_e / ri_e inside the lep W window, bit i meets bit i (checked on the LEFs: ro_e[0] / ro[0] both y 2639.28 abs) |
| rc[1] 4,424 loads (x2) | one read counter per 1104-b landing | lp.py landing_chunk_bits 24 (kept selector per 24-b chunk) + per-chunk reset forest |
| GPL Error 247 at 25 GB | gate --mem 24 | gate --mem 64 |
| clock coverage / CTS FAIL | CTS never ran (GPL killed) | re-measured in this gate |
| lockstep MUT 1/2/4 PASS (insensitive) | random words never train the UCIe lanes, lri carried no beat | tb_stimulus: lane0 <-> lane1 UCIe loopback + 200 CTL beats after link-up; vacuity check |

## SAFE-DESIGN checklist (owner 10-19) -- parent level
1. Pins: PASS. Parent logic = landing rings / reads, reset forest, 2 fault out_regs. Child pins are registered in the children;
   parent ports are 43.2 um abutment hops to them (no parent combinational path longer than the margin). `fault` comes from the
   lep interior (>= 560 um from any face): 2 K-region register stages (out_regs, +2 status edges). Reset: rst_n -> u_lpr_root ->
   per-region forest (depth 3) -> chunk leaves / child pads.
2. Reach: FIXED by floorplan: landings in the 129.6 um slice-lep channel (pins aligned), lanes 86.4 um from lep, every port hop
   43.2 um, tf (2 b) <= ~350 um, reset/ck entry on the E face beside the landings (forest hops <= ~390 um). Gate confirms.
3. Fanout: FIXED: chunked landings (<= 24-b selectors per kept hierarchy) and the reset forest (<= 32 loads per leaf); the gate's
   mapped native census (main 042+) decides.
4. Depth: PASS: ring write + one D:1 AND-OR read stage per chunk; no parent arithmetic.
5. Storage: WAIVED (landing contract L1-L7): 3 x D=4 rings are fixed-latency flop rings, no runtime-indexed storage beyond D.
6. Floorplan: children on the 43.2 lattice; aspect 2.35:1 WAIVED (slice column 5.7 mm is a die-plan constraint); the empty area
   E of the slice is off every link path (die-plan slot), std-cell band = the slice-lep channel + lane gap.
7. Clock: two regional roots ck_S / ck_K with landed crossings; ck_S / ck_K enter on the E face beside the landings / K region;
   judge u_sl<->landing and u_lep<->u_ln* pairs at child flops TT/FF <= 80 (lep 220 vs lane 419 TT in K: hard-child references).
   io_hold_margin 0.03.
8. Schedule: PASS: static; +3/+3 off-die line edges (RESCHEDULE), +2 on the fault status, reset +4: lp record "compiler".

## Stand-in pin plan = the pin REQUEST for the real views
standin/slice.json (PL-SLICE slice cluster: E face rst_n 2520-2525, clk 2540-2552, fault 2575-2580, ro_e 2596-2828, ri_e 2831-3063
local um; S/N buses ranged), standin/lep_nh.json (E-end lep_nh: W ro 4-236, ri 239-471), standin/lane_e.json (E tf 2-6, rx 10-170,
tx 170-330.96).

## Benches (fleet, Verilator 5.050): tools/s81_slice/lepenh_parent_checks.sh {bind|lockstep|slep|slep_swap}
