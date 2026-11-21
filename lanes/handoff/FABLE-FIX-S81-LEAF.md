# FABLE-FIX-S81-LEAF handoff (Fable, restarted 2026-11-20 21:20 PST; owns ot_s81sl_leaf__t*, rep t39)

Read order: this file, then lanes/posts/FABLE-FIX-S81-LEAF.md. The 11-19 sections are in lanes/handoff/archive/FABLE-FIX-S81-LEAF-1119.md.
Work root: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-r3 (B). Lane clone B/repo. Rows: intel2 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-rows-1120 (R).
State at 2026-11-20 23:00 PST. Nothing is signed. No t39 kit is past CTS with a fix in it.

## What sets t39 (post-hook reads only)
- D8i b05c (the old "baseline"): setup -424, hold 14,251 cross-tap ends. Both came from the D8i SDC tap window (68-208 ps per tap) and unbuffered legs. Do not use these numbers for J5.
- J5 wave row t39 a3 (control, epyc7 ot-jobs/ot_s81sl_leaf__t39-route-loved-redfish-1218124-1795237605): post-hook setup -73.73 / tns -1,278, after TT repair -50.61 / -223 (gate -42). Hold before repair 4,660 ends (cross_tap 1,414 ws -79.9, port_in 2,577, port_out 668, same_tap 2); the pregrt passes reach +5 / +30 with about 6k cells.
- Setup, ranked on J5: (1) vp driver_dodd_q -> vp_cf native_memory -73.7; (2) u_rrl_282 -> u_cland_fstart_ft4_o -67.1 (the FSTART face flop at (5,135) takes rst_raw_n and start_d from the start block at (17,1210), 1,130 um); (3) leaf reset bit u_lpad_leafdn_i0.q[594] is +63 (legs 334 / 550 um, over the hop cap but not failing; COORD: not chased).
- Hold, ranked on J5: cross-tap pairs around clk_t6 (the one tap of the vp hig bank, about 6,000 sinks, window 78), then port-in ft*_i. Lockup latches are not needed on the ft chains.

## Rows handed to S81-J6-ASSEMBLY
1. Relay-site keys (J6, plan only, 0 cycles): R/j6_delta_leaf_relay_sites_keys.json. 47 leaf types have all 25 relay_sites keys unmatched ('u_u_crr_rxsb/q' against bound 'u_u_lf1_u_crr_rxsb'), so the crr core reset relays and vp u_rr flops are not seated. 1,175 keys renamed, 0 unresolved. 11 leaf types had no placed kit and are not checked. Tool R/relay_sites_keyfix.py (not on main).
   - Proof p2 (B/p2, launch.sh, run.log): J5 t39 kit with only these keys renamed. Place log: 'OT_RELAY_SITES placed 25 flops FIRM (plan keys unmatched: 0 of 25)' (control: 0 placed, 25 of 25 unmatched). Running to route; read its post-hook CTS against a3.
2. CFX (needs an elaboration, so J7 unless J6 takes the define): lanes/handoff/S81-VP-CFX-ROWS.json, 75 leaf types, define OT_S81SL_VP_CFX, +1 cycle on the vp hc_post write-back. Tree overlay tools/die_plan/s81_vp_cfx_overlay.py on main b651bffd011. Bench on the overlaid J5 tree vp: B/cfx/out/summary.log (no-define form all PASS, control fails as it must; XR / SRAMREG variants were still running: read them).
   - CFX is in NO kit. The kit vp is flattened in the bound module; the define needs as-built elaboration + die bind + kit-rtl. Asked S81-J6-ASSEMBLY whether J6 takes it or I build a private tree (candC2d + overlay + define) after their C3 gate. Unanswered at write time.
3. Parked, not a J6 row: R/reset_legs_PROVISIONAL (reset_leg_plan rows for 69 types, legs over 300 um 414 -> 7, reset_legs_index.tsv, delta PROVISIONAL_j7_delta_leaf_reset_legs_nolk.json built against the J6 keys before the key rename).

## Proof p1 (B/p1, unit oth-ubuntu-2178345-1795239930, goal route)
J5 t39 kit + reset_leg_plan rows (same-edge stages) + OT_TAP_PAIR_UM 200 / OVERFULL_GROW 0.3 / PAIR_CAP 1500. In CTS at 23:00. Tap pair pass moved 2,111 clock pins. Known defects of this proof: OT_RELAY_SPLIT moved 38 sink pins and missed 38 (u_vp_u_rr sync_q / relay_q / rst_n sinks: RESET-RELAY-GEN-R3 tool); OT_TAP_CAP_RECHECK was not set to 0 as the plan key would. Read with `bash B/rd.sh <kit>`; compare hold class counts with a3.

## Open, in order
- FSTART leg (class 2 above) has no row and no owner answer: RESET-RELAY-GEN-R3 form S; reset_leg_plan does not handle cland_fstart.
- CFX private tree and a t39 kit from it; then route to sign-off, LEC, AUTO-EXPORT. Not started.
- Tap ports for the hig bank (TAP-GRID-2130): no reply; p1 only tests pair sharing.
- Waiter helper B/w.sh; background jobs post DONE / DIED under OT_LANE.
