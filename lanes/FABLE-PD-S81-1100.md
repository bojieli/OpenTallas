# FABLE-PD-S81-1100 2026-11-17 10:45 PST: S81 D6 plan event and the col hold family

Reviewer: FABLE-PD-S81-1100 (Fable). Read-only on builds and trees. Technical PD only.
Marking: **V** = I opened the file / log / report myself. **I** = inferred from V data. **R** = reported by a lane.

## Summary

- **Col pg3 hold did not get worse.** The two numbers are different populations. Before the ECO the sign-off already read FF hold -13.66 with 164 violators: 107 input-port ends and 57 internal ends (internal worst -7.61). After the 78 HB4 it reads -13.93 with 112 violators: 110 port ends and 2 internal ends (internal worst -0.44). The ECO closed 55 of 57 internal ends. The port ends were never touched.
- **Round 2 was refused for the port ends, not for the end count.** `--max-ends 130` is not the limit: the plan skipped 110 port ends ("the parent's, no cell") and the run refuses when any end is left.
- **The port failure is one late input bank, fixable with one cell per end.** It is not a clock structure problem. The family fix is a larger port margin before the first route (25 ps, not the 15 ps in r579) or port starts included in the GRT hold repair.
- **D6 SEARCH_PIPE 4 changes 0 cycles and no landing, and LATCHECK could not have seen it either way.** Eight bind outputs are byte-identical to C4r3. The die RTL now matches the view that was signed all along.
- **D6 does not carry the ft channel check at all, not even as a warn.** The D6 tree's `check.py` has 0 lines of it and the D6 G0 report has 0 such findings in 11,092. 20 strip types are over 0.70; 9 are at or above the t34 failure point.

## A. D6 plan event

### Evidence (V)

Trees on epyc10 `/srv/opentallas-scratch2/claude/kw45/`: D6 `src_s81_pin_3c913dbdfb23_d6_1117_work`, C4r3 `src_s81_pin_3c913dbdfb23_c4b_1117`. Evidence `rows/f2s5_S81-DIE-R/d6/r3b/`.

| item | result |
|---|---|
| Strict bind (`bind2.log`) | 398 partitions, 395 types, 873 crossings, 606,281 crossing bits, 0 errors, 0 unbound |
| PRE (`pre.out`) | PASS, 0 findings; 51 inherited station sites over hard cores (warn) |
| G0 (`g0/g0_report.json`) | rc 1: 5 errors, all rule `cuts` (same count as the C4r3 baseline); 11,087 warns |
| Hard-core parameters (`hcparam/hcparam.json`) | 10,086 rows checked, 0 mismatches, 86 unresolved values, 3,130 rows allowlisted (13 modules with no built record) |
| Bind outputs D6 against C4r3 | byte-identical: `bind_latency.json`, `bind_latency_consumers.json`, `bind_lane_asbuilt.json`, `bind_clock_landings.json`, `landing_phase_sign.json`, `bind_reset.json`, `bind_core_resets.json`, `native_topology.json` |
| bind.f defines | no `OT_BKQ_ECO3` in D6: quarters stay hq3 (RFH 0), control QRX 0 |
| RTL diff `dsdv_bk_sel.sv` | `u_c` goes from module defaults to OLL 2, SELOH 1, RNF 1, LQH 1 |
| ft channel check in D6 | `tools/die_plan/check.py`: 0 occurrences of `ft_channel_tracks`; plan `plan_h2_2249.json`: no `ft_channel_track*` budget key; G0 log and report: 0 findings |

### Does SEARCH_PIPE 4 change a die path latency or landing?

No, in cycles: 0 on 873 of 873 crossings.

- SEARCH_PIPE 4 is SEARCH_PIPE 1 with the one-hot group select (`SELOH`) inside `ot_s81ph_sel_ctl_pipe`. The one-hot is registered beside the value it replaces. No stage is added. LQH is the one-hot landing FIFO count, also 0 cycles.
- The fixed wait `XDX = 1 + ceil((RC + RS + QRX) / 2)` is unchanged because QRX stays 0 in default mode.
- The physical view is the same signed core (bksel_c3_1104, odb 11f32154). Its outputs were already negedge-launched (OLL 2) and its reset already negedge-sampled (RNF 1). Die STA sees the same lib and pins as C4r3. (I)

What LATCHECK should have caught: nothing. But note it is blind to this class by construction. Its inputs did not change by one byte while four parameters of a bound core changed. A core-internal depth change would pass LATCHECK 873 / 873 in the same way.

Two things the RTL model now shows that the old default model hid (0 cycles, half-edge behaviour):

1. OLL 2: every control output (367 + 4 x CB + 4 bits) is launched on the falling edge. Any die-side bench or token run that sampled these on the old rising-edge model has T/2 = 416.5 ps less modelled margin. The silicon view always had this.
2. RNF 1: the control's reset is taken through a falling-edge flop. Release moves by half a cycle in the model.

The check that covers this class is the parameter check plus a functional run, not LATCHECK: `hcparam` reads 0 mismatches with `dsdv_bksel_c` off the allowlist (R: S81-CORES-R3), and the bench reads base PASS (R). I did not see a die-level token run on the D6 RTL.

The later ECO3 step is different: RFH 2 adds one input edge per quarter and QRX 1 adds 2 edges to the fixed waits. That one must not go out on a LATCHECK pass alone.

### Which strip types hit ft overflow at kit time?

Census `d6/ft_channel_census_c4r3.json` (V): 25 channels in 20 types over 0.70. Util = ft bits / (45.6 usable tracks per um x channel width). The only measured point is t34: util 1.12 failed GRT with overflow 3,516. The raw-track limit (64.3 tracks per um) is util 1.41.

| class | types (worst util) | count |
|---|---|---|
| Over raw tracks, cannot route in any form | t22 (2.18), t2 (2.09), t9 (1.50) | 3 |
| At or above the t34 failure point | t71 (1.33), t17 (1.31), t13 (1.28), t23 (1.26), t67 (1.26), t34 (1.12) | 6 |
| Between 1.0 and 1.12, expect failure | t73 (1.07), c1x t8 (1.04), t57 (1.02) | 3 |
| 0.70 to 1.0, not known | t28 (0.97), t46 (0.91), iq t1 (0.87), c1x t9 (0.87), t43 (0.79), leaf t8 (0.76), t14 (0.75), t44 (0.73) | 8 |

The inner gaps (VE_m to VE_s, VE_s to vq) have a macro on both sides, so spill over M7 has two edges, not one. On t34 spill carried about 23 % of the demand. That may save a type near 1.1. It does not save t22, t2 or t9.

### The single check before kits

Run the ft channel census on the D6 plan and use it as the kit release filter: no GEN, GRT or route for a strip type with any channel over 0.70. That is 20 types held, t34 among them. Today nothing in the D6 tree does this, so the warn is silent. Calibrate the 0.70 to 1.0 band with one GRT-only run on t73 or t28 before releasing those 8.

## B. Col hold, family of 203 types

### Evidence (V)

epyc8 `/srv/opentallas-scratch2/claude/fable-fix-s81-col/`: original kit `pg3/col_h9_r2__t1__clce45cab5__pv7a260fc0`, ECO `pg3_hei_route1117`, round 2 `pg3_hei_route1117/r2`.

| item | before ECO (`pg3/.../signoff/signoff.json`) | after ECO (`r2/hold_endpoints.tsv`, `dump/ff/sta.log`) |
|---|---|---|
| FF hold WNS, all ends | -13.66 | -13.93 |
| Violators, all | 164 | 112 |
| Input-port ends (`frame_int_i0`) | 107 | 110, worst -13.93, mean -4.90 |
| Internal ends | 57, worst -7.61 | 2, worst -0.44 and -0.29 (`u_s13` cfg[35], f_prog[21]) |
| Output-port ends | 0 | 0 |
| TT setup | -39.25 | -39.36 |
| TT setup room on the failing hold ends | 690 or more (internal) | 559 or more |

Worst port path, FF (V, `sta.log`):

| term | ps |
|---|---|
| vclk latency (mean of 1,491 pin flops) | 361.82 |
| input external delay (overlay in_min) | -40.00 |
| data path: port, HB4 36.0, BUFx2 14.8, HB4 37.7 | 89.66 |
| data arrival | 411.48 |
| capture clock at `u_bin_frame_int_i0/q[854]` (clk_t18, 5 tap buffers, 6 delay buffers, leaf 68) | 412.83 |
| uncertainty | 12.50 |
| required | 425.40 |
| slack | -13.93 |

- 107 of the 110 port ends are bits 822 to 949 of `frame_int_i0`, one bank on one clock leaf group. Its clock lands 51.0 ps after the mean that vclk stands for.
- Pre-GRT pass (`run_route.log` 2789-2790): port_in 0 violators, WNS +4.90 at margin 5, on placement RC.
- GRT hold repair excludes input-port starts by design (`OT_GRT_NONPORT installed native_ff`, line 2829; "port hold remains visible", line 4174). Nothing repairs port hold after placement RC.
- Round 2 (`r2/RESULT.json`): 112 negative ends, 2 plan rows, 110 skipped, exit 4 "plan could not pad every end".

### Why hold looked worse

It is none of the four candidates as a real degradation.

| candidate | verdict | number |
|---|---|---|
| Sign-off port overlay in_min -40 | This is the whole difference, but as a counting change, not a new failure. The "57 ends, -7.61" was the internal-only probe; the "112 ends, -13.93" is all ends with the overlay | 107 port ends were already in the first sign-off |
| Post-route extraction delta | Small | port worst -13.66 to -13.93 = 0.27 ps after 133 nets re-routed and fill |
| HB4 delay model | Works as priced | 55 of 57 internal ends closed; HB4 gives 36 to 38 ps in FF |
| Useful skew | Not in play | clock was frozen in the ECO; pair skew FF 451.2 to 452.1 |

The 2 internal ends left (-0.44, -0.29) are hard-core `u_s13` outputs that the first plan padded with one HB4 less than they needed after re-route.

### Is it a clock-skew structure problem that padding cannot fix?

No. One input bank sits 51 ps late against the vclk mean; the contract allows 40 ps early data plus 12.5 ps uncertainty; the path already has 2 HB4 and is 13.93 ps short. One more HB4 per end (36 ps) closes all 110 with 559 ps of setup room. The TT setup of -39.36 is on other paths and does not move with these cells. It is 2.6 ps inside the -42 gate, so the ECO must stay off clock nets, as it did.

The structural part is in the flow, not the tree: port hold is closed once at placement RC to +5 ps, is excluded from GRT repair, and then loses 18.6 ps to sign-off (+4.90 to -13.66).

### Fixes, ranked

| # | fix | numbers | owner |
|---|---|---|---|
| B1 | pg3 now: one more route-only round that pads the port-start captures at the flop D pin (the net between the existing hold cell and the flop, inside `u_bin_frame_int_i0`; not the port net), plus the 2 internal ends | 110 + 2 = 112 HB4, target +10; setup room 559 or more; expect about 112 nets re-routed against 133 last time | S81-TYPES-R3 (tool option in `hold_eco_internal.py`, with TOOLS-CONVERGE) |
| B2 | Family, members not yet at GRT: include input-port starts in the GRT hold repair at the same 10-ps margin as internal ends | Internal loss GRT to routed is 7.9 ps; 10 covers it. Removes the 18.6-ps unrepaired gap | S81-TYPES-R3 (flow) |
| B3 | If B2 is not in by the next release: pre-GRT port margin 25, not 15 | 15 leaves 4.90 + 10 - 18.6 = about -3.7; 25 leaves about +6. Cell cost by the kit's own note: about 1,000 cells at a 25-ps uniform margin | S81-TYPES-R3 (item_env on the 76 released items) |
| B4 | Sign-off line prints the split every time: port-in N / worst, internal N / worst | The JSON already has it (`std_min_start`: port 107, nonport 57, -7.61) | S81-TYPES-R3 with TOOLS-CONVERGE |
| B5 | pg3 finish: take the ECO route's `hei_drc.rpt` (0) in place of the stale `5_route_drc.rpt` (2) | DRC 2 is stale (R) | S81-TYPES-R3 |

To check when r579 lands: the kit on disk reads `OT_PREGRT_HOLD_PORT_MARGIN` and `OT_HOLD_FF_MARGIN`; the item_env sets names ending in `_PS`. I did not read the branch.

## Stop list

- Stop raising `--max-ends`. The refusal is 110 skipped port ends; any value gives exit 4.
- Stop another internal-only round on pg3. It can pad 2 ends and the sign-off stays at -13.93.
- Stop comparing internal-only probes with the all-ends sign-off number.
- Do not change the col clock tree, taps or delay buffers for hold. The failing bank is 14 ps short on data, with 559 ps of setup room.
- Do not release the 76 col items on port margin 15 expecting hold to pass; use B2 or 25.
- Do not full re-route pg3. The route-only form converged to DRC 0 and held TT setup within 0.11 ps.
- Do not release D6 kits for the 20 strip types over 0.70, and do not tune GRT on them.
- Do not treat LATCHECK 873 / 873 as cover for a core parameter change. Use the parameter check and a functional run.

## Not checked

- The r579 branch source, and whether its variable names match the kit scripts.
- Whether the D6 G0 was run with a checker outside the tree that has the ft channel rule; the report on disk has no such finding.
- The census model for inner gaps (two macro edges); only the t34 west seam is calibrated by a GRT run.
- A die-level token or bench run on the D6 RTL with the new control parameters.
- Whether the other col members share the late bank on bits 822 to 949; pg3 is the only routed DB read.
- Die STA on the real parent arrival for `frame_int_i0`; the type sign-off uses the -40 overlay.
