# FABLE-PD-QCHOLD-1915: QC "GRT hold-repair stall" class (11 types, 15 hold keys)

2026-11-15 19:55 PST, FABLE-PD-QCHOLD-1915. Read-only. Nothing launched, stopped, held or edited.
MEASURED = read by me tonight from a kit log, kit script or sign-off file on a build host. INFERENCE is marked.
Kit root on every host: `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/` (written `K/` below).
Log times on the hosts are UTC; this note gives PST.

## 0. Answer

1. **The stall is real but it is over. It happened only on event S kits (11-14 12:54 to 18:26 PST) and has not recurred
   in any of the 47 GRT logs of 35 types built on S3R or later.** The hold keys hold types for a failure that the plan
   removed 20 h ago.
2. **What stalled: the GRT hold repair was padding output ports, not internal paths, at 11 to 15 s per buffer.** It never
   diverged; it was a linear grind that needed 26 to 53 more hours per kit.
3. **One cause, in two parts.** (a) Plan: event S timed the output min delay without the tap window, so 1,063 to 7,989
   output bits per kit failed hold; S3R moved it to contract + window and the count is 0 since. (b) Flow: the "non-port"
   hold scope of the GRT repair excludes input ports only, so output-port hold stays inside the repair although the gate
   is non-port hold.
4. **A second flow fault is live now and is the reason these types still leave GRT and route with negative non-port
   hold:** the cross-tap route guard of the pre-GRT hold repair is silently off on every kit since S3R.
5. **The types are blocked by `DRT-0255` today, not by hold.** 33 of the 47 S3R+ runs stopped with `DRT-0255` after a
   clean hold repair.

No extra hold-repair pass is proposed anywhere below.

## 1. What the six stall logs show (MEASURED)

All six are `5_1_grt.log` of event S, non-port scope active (`OT_GRT_NONPORT begin native_ff input_ports=7180..8714`),
`-max_buffer_percent 100`, margin 0.

| type (kit under `K/s29q103S/items/`) | host | start: worst / endpoints | end of the one chunk | buffers | run time | per buffer |
|---|---|---|---|---|---|---|
| sle_fw_v1__cl9d029624 attempt_8 | epyc8 | -59.34 / 6,875 | -41.29 / 6,198 | 1,328 | 4.8 h | 13.1 s |
| sle_stm_v1__cl27746664 attempt_6 | epyc9 | -85.22 / 5,838 | -18.88 / 4,229 | 1,701 | 6.9 h | 14.6 s |
| slw_fe_v1__clfe325744__cldb4efe33 attempt_6 | epyc9 | -123.59 / 6,909 | -82.70 / 6,491 | 1,139 | 3.6 h | 11.3 s |
| slw_fe_v2__clf110fab2 attempt_7 | epyc10 | -53.59 / 6,558 | -41.05 / 5,973 | 1,155 | 4.4 h | 13.8 s |
| slw_stm_v1__cl05fc43f7__cl2086fa2c attempt_6 | epyc9 | -81.07 / 7,678 | -42.37 / 6,853 | 1,651 | 6.9 h | 15.1 s |
| slw_stm_v2__cl9beb65e6 attempt_6 | epyc9 | -115.39 / 8,534 | -30.78 / 7,144 | 1,633 | 6.4 h | 14.0 s |

- Each ends `RSZ-0060 Max buffer count reached`, then `OT_HOLD_STALL NEEDS_RTL stage=grt reason=hold repair over 3 h`.
- **Not divergent.** Worst slack improved 12 to 85 ps and total negative slack 15 to 58 % in every kit. The buffer count
  equals the chunk cap (1,326 for fw_v1). Endpoints fall by one per 15 to 31 s.
- **The endpoints are output ports.** The repair table prints the worst endpoint every 10 iterations: 487 of 537 samples
  over the six logs are output ports (`st_eo`, `dd_eo`, `x_fw_fe_p1_o`, `x_fw_p1_o`, `x_su_l0_ctl_o`, `x_ctl_p1_o`, ...);
  50 are internal pins.
- Setup-critical: no. The repair kept gaining on every endpoint it visited. (The setup-locked class is the input-port
  residue of FABLE-TRIAGE-QC M3; it is outside this scope and did not stall GRT.)
- Clock skew on these pairs: flop to output port against the IO virtual clock, so no launch/capture pair. The debt is
  the output min contract, see section 2.
- "Identical numbers per attempt" is determinism of the same kit on the same database.

The other 5 of the 11 types have no stall log on any host. Their last GRT hold repair closed in one chunk:
sle_stm_v1__clbe630b9c (33 endpoints, 517 s), slw_stm_v1__..cl389df4e9 (142, 1,598 s), slw_stm_v2__cl1ca9c415 (637,
9,371 s), slw_fe_v1__..cl08d14f0d (54, 824 s), sle_st_b_v1__pv0e7b1dcc (19, 116 s). slw_hc3 x2 never reached GRT on S3R
(place: LEC NOT EQUIVALENT on cld86a7ad4, banner-only reason on clccfc3e6b).

## 2. Cause (a): output min delay without the tap window (plan, already fixed)

MEASURED from 44 `pregrt_ff_hold.log` class lines (`class before port_in / same_tap / cross_tap / port_out`):

| kits | `OT_HOLD_OUT_MIN` | port_out endpoints (worst) | cross_tap endpoints (worst) | hold cells | repair time |
|---|---|---|---|---|---|
| events B0, S, S2 (13 logs) | -25 or +1 / +27 | 1,063 to 7,989 (-52 to -165) | 70 to 12,069 (-62 to -180) | 17,875 to 53,110 | 2,473 to 12,096 s |
| S3R, S4C, S4P, S4Q2, S4Q3B (31 logs) | window - 25 (22.8 to 197.8) | **0 in all 31** | 4 to 2,007 (-29 to -104) | 514 to 23,925 | 72 to 3,530 s |

- When the pre-GRT repair of an event S kit fell back (old accept rule, fixed by QC-HOLDGRT-1 on 11-15 00:16), the
  whole port_out debt went to the GRT repair. That is the stall.
- Since S3R the GRT repair starts with 0 to 637 non-port endpoints, worst -58.22, and ends at 0.00 or better in one
  chunk in all 47 logs: 31 to 9,371 s, 1 to 666 buffers. With the accept fix in the kit (S4C and later) it is 0 to 161
  endpoints and 31 to 1,354 s.
- INFERENCE: the S3R output-min form is the correct one (the kit hold gate refuses `out_min - window > 0`, and the kits
  are at exactly window - 25). I did not re-derive the seam contract.

## 3. Cause (b): flow faults, ranked

### F1. Cross-tap route guard is off on every S3R+ kit (live, costs a post-route hold miss)

- MEASURED: `pregrt_ff_hold.tcl` lines 229-242 build the list of tap ports to guard and skip every port named in
  `core_taps_ff.sdc`. That file used to hold the core taps only. Since the plan `clock.tap_offset` overlay (R-CLOCK-7)
  it holds every grid and edge tap: on `slw_sc_v1__cl63e5a7a2` (S4Q3C attempt_12) 84 of 84 tap ports are skipped.
- MEASURED: all 31 S3R+ logs print `cross-tap guard not applied (no tap window lines in the kit SDC)` and
  `cross_tap_wns nan tap_ports 0`. All event S logs print `cross_tap_wns 45.00 tap_ports 83..127`.
- Effect, MEASURED: cross-tap pairs are padded to +5 ps on placement RC instead of +45. GRT then finds them negative
  again (same types: hc2 on S2 with the guard 3 to 10 endpoints at -4 to -8; on S3R / S4Q2 without it 33 to 88 at -19 to -21).
  GRT repairs to margin 0, and the two kits that routed clean lost it again in detail route:

| routed kit (DRC 0) | GRT end | routed FF hold, non-port | routed FF hold, all paths | TT setup |
|---|---|---|---|---|
| sle_fe_v1__cl8210183c S3R attempt_3 (intel1) | +0.02 | **-9.98, 205 endpoints** | -116.76, 3,761 (3,556 port) | -60.62 |
| sle_fw_v3 S3R attempt_3 (epyc10) | +0.16 | **-19.72, 145 endpoints** | -109.10, 664 (519 port) | +53.1 |

- Fix (flow, one file): skip only the core tap ports (the `CP2 FF core tap` lines, `clk_c*`); for the other taps take
  the FF early value from the overlay as the base, widen it by guard - margin for the cross-tap pass, restore it.
- Proof: re-run `pregrt_ff_hold.tcl` on the `4_cts.odb` of one kit; pass = `tap_ports > 0`, `cross_tap_wns 45`, and the
  `OT_HOLD_BUDGET` line. Then one routed kit with non-port FF hold >= 0 and no ECO.
- Cost, INFERENCE: more cells on cross-tap pairs. The measured GRT to route loss is 10 and 20 ps, so if the 45 ps guard
  exceeds the 10 % budget, set `OT_PREGRT_HOLD_GUARD` to 30, not a second pass.

### F2. The "non-port" GRT scope still contains output-port hold (latent; it is the measured stall)

- MEASURED: `grt_nonport_hold.tcl` sets `set_false_path -hold -from <input data ports>` only and prints
  `hold input starts only; reg-to-output/internal retained`. The gate is FF hold >= 0 on non-port paths.
- Fix (flow): the GRT scope also excepts paths ending at output ports, and prints the residue as one advisory line
  (`PORT_SEAM out N ws X`) for die STA. The pre-GRT repair keeps padding port_out to +5 (it does that in minutes on
  placement RC). Any later plan event that makes the output min bind again then costs minutes, not 50 h.

### F3. Pre-GRT accept test still vetoes on the kit worst slack (latent)

- MEASURED: line 151 of the S4Q3C kit copy is still `if {$w1 < $w0 + 1.0 && $n0 > 0} { return "no hold gain" }`,
  on the worst slack of all classes. FABLE-TRIAGE-QC M3 fix 1 did not land.
- It fired in 0 of the 31 S3R+ logs. If it fires, up to 2,007 cross-tap endpoints go to GRT at 15 to 31 s each (8 to 17 h).
- Fix: judge the gain on same_tap + cross_tap (+ port_out) only.

### F4. Port-in padding spends cells and TT setup for a contract that stays open (decision for DIE-QC-103)

- MEASURED: sle_fe_v1 S4Q2 attempt_15: 23,925 hold cells (+5.7 % instances) for 3,556 port_in and 286 internal
  endpoints; TT setup 41.6 -> -9.0; 680 port_in endpoints still at -49. sle_sc_v1 cl115da35f: 5,960 cells, 19.6 -> 5.9.
  slw_sc_v1 cl4590432d: 4,301 cells, -3.6 -> -13.4. Residue after padding: 508 to 2,952 port_in endpoints per kit.
- This is M3 (setup-locked relay inputs). It is not in the gate and does not stall GRT. The padding should not take TT
  setup below 0; whether the -85 contract is needed is a die STA result.

### F5. Hold guard gives no progress line for hours (report only)

- MEASURED: the first chunk cap is 0.25 % of instances (1,035 to 1,330 buffers). At 11 to 15 s per buffer that is 3.6 to
  6.9 h before the first `chunk` line, and WF-1 removed the wall cap. Start with 200 buffers so the rate is visible in
  45 min, and print the port / internal split of the violators at start. No new stop.

Not a cause (MEASURED): the FF library, station placement, and the repair arm itself. The repair closes 1 to 666
non-port endpoints to >= 0 in one chunk on every S3R+ kit.

## 4. Overlap with the DRT-0255 families

MEASURED, S3R and later: 33 of 47 runs and 24 of 35 types stop with `DRT-0255`; 3 routed with DRC 0.

| hold-key type | last route result on S3R+ | DRT-0255 hold key covers it? |
|---|---|---|
| slw_stm_v2 (cl1ca9c415; siblings sle_stm_v2 x2) | DRT-0255 (clock net clknet_3_0_0_clk_t54) | yes, `sl?_stm_v2*` |
| slw_stm_v1__..cl389df4e9 | DRT-0255, S3R attempt_4, epyc2 | no |
| slw_fe_v2 (sibling cle312294d) | DRT-0255, S3R attempt_3 | no |
| slw_fe_v1 x2 (sibling sle_fe_v1__cl8210183c) | sibling: DRC 0 once (S3R), DRT-0255 twice (S4C, S4Q2) | no |
| sle_st_b_v1__pv0e7b1dcc (siblings pvc5a85fd4, slw cl6357f1cc) | siblings DRT-0255 on S4C | no (held by `*_st_b_*`) |
| slw_hc3 x2 | no route yet; hc0 and hc2 all DRT-0255 | no (hc2 yes) |
| sle_fw_v1__cl9d029624, sle_stm_v1 x2 | no route result on S3R+ | fw held by `*_fw_*` |

- So 8 of the 11 types sit in a family whose last route result is `DRT-0255`. Unchanged relaunch after the hold keys
  lift would stop there.
- One observation for DRT0255-PROOF-1115, INFERENCE only: sle_fe_v1__cl8210183c routed DRC 0 when the pre-GRT pad fell
  back (291 hold buffers in the kit) and stopped with `DRT-0255` twice with 23,925 pre-GRT hold cells. The plan event
  also differs, and sle_fw_v3 routed clean with 8,141. Check where the failing boxes sit against the HB4 pads.

## 5. Ranked fix list

| # | fix | kind | evidence | owner | unblocks |
|---|---|---|---|---|---|
| 1 | Re-key the 10 hold-stall patterns: drop the "hold-stall" reason; put `sl?_fe_v1*`, `sl?_fe_v2*`, `sl?_stm_v1*`, `sl?_hc3*` under the DRT-0255 family hold (release with the PG form) | wave hold list | MEASURED (sections 1, 2, 4) | COORD / KIT-OPS-5 | 4 S4Q3C types held today: sle_fw_v1__cl9d029624, slw_fe_v1 x2, slw_fe_v2__clf110fab2 |
| 2 | F1 cross-tap guard: skip core taps only | flow, `tools/die_plan/pregrt_ff_hold.py` | MEASURED fault; effect on routed hold from 2 kits | QC-SRC-CLOSE-1115 | every QC type: no post-route hold ECO for cross-tap pairs |
| 3 | F2 output-port ends out of the GRT hold scope, advisory line | flow, `grt_nonport_hold.tcl` | MEASURED cause of all 6 stalls | QC-SRC-CLOSE-1115 | removes the stall for good |
| 4 | F3 accept test on non-port classes | flow, same file as 2 | MEASURED line; did not fire since S3R | QC-SRC-CLOSE-1115 | latent |
| 5 | F4 port-in pad must not take TT setup below 0; contract decision after die STA | flow + plan | MEASURED cost | DIE-QC-103 | TT setup on fe / sc types |
| 6 | F5 first chunk 200 buffers + class split line | flow, `hold_guard_grt.tcl` | MEASURED | QC-SRC-CLOSE-1115 | visibility only |

Fixes 2, 3, 4 and 6 are one branch and one proof kit: sle_fe_v1__cl8210183c from its S4Q2 `4_cts.odb`
(epyc8, `K/s29q103S4Q2/items/sle_fe_v1__cl8210183c/attempt_15`). Pass = `tap_ports > 0`, GRT start under 20 endpoints,
routed non-port FF hold >= 0. Kits carry the script from gen, so only kits generated after the install have it.

## 6. Stop list

1. No relaunch of the 11 types "to see if hold stalls". It does not on S3R+; they stop at `DRT-0255`.
2. No second pre-GRT pass, no post-route hold ECO pass, no larger buffer percent, no `-allow_setup_violations` for
   these types. The two routed misses (-9.98, -19.72) are the missing guard (F1), not a missing pass.
3. No RTL change, split or re-floor for "HOLD_STRUCTURAL / NEEDS_RTL" on these types. The line was output-port padding.
4. No GRT hold margin above 0 as a substitute for F1; a uniform margin pads every zero-logic pair.
5. No change to the output min contract back to a flat -25; that form made 1,063 to 7,989 port endpoints per kit.
6. No waiting on QC-HOLDGRT-1. Its accept fix is installed and works (0 fallbacks in 31 S3R+ logs); the lane is gone.

## 7. Not checked

- The 145 / 205 routed non-port endpoints were not split into cross-tap and same-tap; F1 assumes cross-tap from the
  pre-GRT class tables.
- The cell cost of the 45 ps guard on S3R+ kits was not counted; the proof kit gives it.
- Whether die STA needs the -85 input contract or the output min at all (F4, F2 residue): no die run read.
- Kit copies moved between hosts can appear twice in the 47 logs; the type counts are distinct.
- slw_hc3: no GRT log on any host for S3R or later.
