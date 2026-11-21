# CORE-PIN-RELAY-R2 handoff (2026-11-20 late PST; successor of CORE-PIN-RELAY-1930)

## Results (col_h9_r1__t1__cl49d7a23e, epyc9 /srv/opentallas-scratch2/claude/core-pin-relay-1930/kits)
Kits: col_A control, col_B pin relays + OT_CORE_IN/OUT_LAND on kit tap, col_C2 = B placement + cpr_c_taps.tcl (136 pin flops of
the 14 early-tap cores -> their clk_c<k> port; 126 landing, 10 driving), col_O = original kit 4_cts.odb. col_C = first C run with a
hook that missed buffered inputs (superseded by C2). Class slack: cpr_slack.txt (core-pin-relay-1930/cpr_slack.tcl via run_slack.sh,
4_1_cts.odb, kit setRC_rcx, propagated). Legs: cpr_legs.txt (run_legs.sh, placed_hops_or.py OT_REACH_UM=300 + legs.py).
| | A | B | C2 |
| legs>300 core_in/out/c2c | 2416/1517/694 | 2420/1516/694 | (B placement) |
| place WNS | -75.5 | -297.2 (cland_monitor glo0) | = B |
| setup flop->core | +156.9 | +124.6 | +152.1 (relay->core +436.5) |
| setup core->flop | +294.4 | +291.5 | +270.4 (core->relay +747.6) |
| hold flop->core | -32.6 (1) | +25.0 | +25.0 (relay->core +157.1) |
| hold core->flop | +23.1 | -23.5 (63, -940) | +8.0 (core->relay -9.9, 22) |
| hold into core-tap relays | - | - | -77.9 (78 ends) |
| flow 4_cts_final WNS/TNS | -226.9/-24452 | -227.3/-25615 | -210.5/-1708 |
Verdict: flop->core setup never fails (lever-1 premise false); tap choice = hold trade. Recommend kit tap default, withdraw J6 stop item.
Side finding: -227 class = u_u_s6 -> u_u_e6_u_w negedge; tap_balance ETAP hangs s6/s9 on port clk_c8/c12 and under-delivers
(effective 422 vs 450 WARN); C2 sourced a tree delaynet and got 453 OK -> TNS -24k -> -1.7k. Needs an ETAP top-up fix (tap_balance owner).

## Padded-tap check (COORD, cc FABLE-FIX-KV-HGI): not the S81/QC cause
S81 col clk pins on the core edge, port 6 um away, pads 2 um from pin; tap_balance pads clk_c by ~140 ps on purpose, effective 447-468.
QC cbn_q01 cld9ff4c40: ck interior but port right above it, not padded; core genuinely LATE (effective 404-413 vs target 250),
constraint.sdc l206-207 override clk_c* source to -425.1/-404.9 vs contract -483.25, internal 818 vs insertion 733.

## Posted
- QC cb station-site row form to FABLE-FIX-QC-CB (cbn_q01 y_o12 2->4, nb_i12 4->6 regs_um, pin-end reg at channel x / pin y).
- S81 rows NOT posted to S81-J6-ASSEMBLY (B did not win without rows). Next: B + rows/s81_core_pin_relay_rows.json proof kit.

## Open
- B+rows proof on col_h9_r1 (merge rows with relay_depth.py merge, regen kit). - ETAP top-up for clk_c-hung pins.
- cpr_c_taps.tcl is a private hook (not on main). Nothing pushed to main. No jobs of others touched.
