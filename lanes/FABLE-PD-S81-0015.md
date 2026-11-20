# FABLE-PD-S81-0015: S81 physical-design review (11-19 23:37 to 11-20 00:10 PST)

Reviewer: FABLE-PD-S81-0015 (Fable). Read-only. No build, bind or tree was launched, stopped or patched.
Gate used: DRC 0, routed TT setup >= -42 ps, hold >= 0, bind + LATCHECK, hops <= 405 um. Nothing here is a new gate, hold or freeze.
Every number was read from the named file during this review. Section 2 (per-family table) and section 4 were read by two sub-agents of this review; I re-opened the files marked "re-read".
The only files I wrote are estimator outputs in epyc9 `/tmp/fable-pd-s81-0015/` (PRECHECK runs, 2 min each).
Leaf and serdes are with FABLE-FIX-S81-LEAF-2140 and FABLE-FIX-S81-SERDES-0000 and are not redone here.

## 0. What changes the plan tonight

1. **J3 r6 bind failed at 23:54 on one tap pair.** `slice_station__t51` (new soft form) has explicit taps clk_t21 (13.068, 366.636) and clk_t22 (17.868, 366.636), 4.8 um apart against a tap clearance of 8.64 um. It is the only violation in the 73 taps. S81-DIE-R3 found the same cause and moved clk_t22 at 23:59; r7 is binding on plan_j3b 5bed28a94d9d. PRECHECK on plan_j3 reports this error in 2 minutes, against 53 minutes for the bind.
2. **Do not bind plan_j4a 5090069a4c41 or plan_j4b 3dc05566d640 (the J4 base since 23:59).** Each has 491 station rows (29,014 bits, 15 leaf types) with a hop over 405 um, up to 626 um. plan_j3 has none. The site tool reports "REFUSED final hop" but still writes the moved sites; the 23:35 post says those rows kept their old site, and they did not.
3. **cw8 is measured and is not better than cw6.** Intra hold TT / FF -314.97 / -278.32 against -309.05 / -265.95. The clusters are geometric, so they hold only 12 % of the window-limiting tap pairs, and they are too wide to share within 5 stages (median 10). cw8 also adds new errors that repeat on every instance of a family.
4. **The 100 to 165 ps range inside a kit tap is a kit-CTS defect**, a late tail of a few leaves that exists before padding. The balancer then stops padding when the latest sink reaches target + 20, so the bulk of that tap stays 60 to 90 ps early against its neighbours. That is what makes 1,334 cross-tap hold ends at -120 on col_h9_r1.
5. **D8i closes setup at CTS on every col family that has a number, except col_h10_r1** (-270 after repair, one 769 ps net lpl_9_r -> n24). This is the WATCH item COL-H10-1119 said it would write rows for if it failed.
6. **Three of the four repeat-fail classes outside leaf and serdes cannot pass on the plan they run on** (t51 natives, svc memory slice, flat svc kit). Event J answers them, so the J3 rebind is the unblock.

## 1. (A) Plan events

### 1.1 J3 (plan_j3 f925a42b1336), r6 on intel1

**State.** `intel2 ~/s81-die-r/build_j3_r6.log`: ELAB_RC=0, then BIND_RC=1 at 23:54: `ValueError: slice_station__t51: explicit tap clk_t22 violates outline/halo/tap spacing`. LATCHECK_RC=1 and G0_RC=1 follow only because the bind emitted nothing. The 23:57 STOP post quotes a traceback line, not the cause.

**Root cause (plan_j3 on epyc9 `s81-die-r3-e8/d8j/plan_j3.json`, checked with the tree's own `schema.type_tap_clear` and `placement_obstacles`).**
- t51 in J3: hard_cores 0, `child_root_taps` removed, tap_mode explicit, 73 taps, clearance 8.64 um.
- Tap pairs closer than the clearance in both axes: 1, clk_t21 / clk_t22 (dx 4.8, dy 0). Taps outside the outline clearance: 0. Taps inside a placement box: 0.
- The other 76 types whose clock or hard cores change in J3 pass the added-tap rule (`s81_hi_corridor.added_tap_errors` on plan_j3: 0 errors).

**Ranked fix (S81-DIE-R3).**
1. Done by S81-DIE-R3 at 23:59: clk_t22 moved to (21.708, 366.636), plan_j3b 5bed28a94d9d, bind r7 on intel1 (`intel2 ~/s81-die-r/build_j3_r7.log`). My check agrees that this was the only bad pair. Everything in the table below was read on plan_j3 and holds for plan_j3b, which differs by that one tap.
2. Before each bind, run `tools/precheck/precheck.py --die s81 --plan PLAN` and read its TAP-ERROR lines. On plan_j3 it prints this exact ValueError after 121 s (`epyc9 /tmp/fable-pd-s81-0015/j3_leaf/findings.tsv`). r6 took 53 minutes to reach it. This is the second bind today lost to a tap-spacing row (cc3: 126 banks on a keepout edge). It is a read, not a gate.

**What I checked on the rest of J3 (static, against the D8i C6 plan 05b98332 in `d8i/plan_d8i_c6.json`).**

| Item | Result | Evidence |
|---|---|---|
| Reach, col face buses, worst bit of the pin window | 0 of 822 rows over 405 um; max 390.4 (col_h9_r2 frame_int_o0). The C6 base has 300 rows over, max 512.2 | my script `j3e.py`; PRECHECK REACH on the 84 changed types: C6 162 findings, J3 0 (`/tmp/fable-pd-s81-0015/{c6_col,j3_col}`) |
| Reach, centre measure | max 400.5 (col_h9_r1) | `j3d.py` |
| Macro site, c12_6 on 60 col_h9_r2 | origin (466.56, 501.12) on pv11b6518d; 0 overlaps, 0 halo gaps under 8.64 um on all 60; no clock tap inside the old or the new ROM box | `j3b.py` |
| Clock | The clock block is identical to C6 in all 216 col types. J3 adds 221,868 station flops in 84 types and no tap (66,996 in the 12 col_h9_r0_p5, the same in p6, 33,498 in p4; 5,583 per type against `tap_max_sinks` 1000) | `j3b.py`, `j3e.py` |
| Latency | 873 lanes: `fixed_cycles` +1 on 150, +2 on 12, 0 on 711, as posted. LATCHECK did not run, so the die side of the frame_int +1 is still unmeasured | `j3d.py`; build log |
| svc H8 | plan_j3 still names `wq_mem.g_m[2]` (6 mentions each in svc_hi rs t2, svc_lo rs t3 and t6, the same count as g_m[0] and g_m[1]) | `j3a.py`; see section 4 |

**Risks to read on r7.**
1. Tap load. The new stations land on existing taps. A 1,104-bit station is more than one tap's cap by itself, and an overloaded or sparse tap is where the in-tap tail of section 2 comes from. PRECHECK TAP-CAP could not run: the tap check stops on the t51 error for the whole plan. Run it on r7's plan for the 84 types; added-tap rows go into J4.
2. svc `g_m[2]`: if the H8 bound netlist has two memory slices, the MPL-0020 failure returns on J. Check the bound netlist before any svc kit.

### 1.2 J4a / J4b (plan_j4a 5090069a4c41 and plan_j4b 3dc05566d640, leaf form C sites)

**Finding 1: 491 rows over 405 um that J3 does not have.**
- Measured on the plan (`j4c.py`): 19,080 leaf station rows, 16,856 moved. Rows with a hop over 405 um: J3 0, J4a 491 (29,014 bits) in 15 types. plan_j4b (J4a plus the t51 tap move) has the same 491 rows, max 626.4. Worst: leaf t68 626.4, t38 611.2, t5 594.1, t17 591.8, t2 542.3, t1 537.9, t3 516.3, t74 462.3, kv_leaf t5 457.8.
- PRECHECK REACH on the leaf types agrees: J3 3 findings, J4a 219 (`/tmp/fable-pd-s81-0015/{j3_leaf,j4a_leaf}/findings.tsv`).
- Example, leaf t68 `g_ln[10]` hq_d, 256 bits. Stations (1019.52, 259.2), (1188.0, 168.48), (1196.64, 146.88) became (933.12, 406.08), (1166.4, 743.04), (1196.64, 146.88). The second to third hop is now 626 um.

**Root cause, in `tools/die_plan/s81_hi_corridor.py` f9e4dc8cec7, function `sites`.**
1. The final hop check only appends a "REFUSED final hop" row. The stations were already rewritten in place and the plan is written afterwards. The run exits 1 (`j4a_sites.sh` prints SITES_RC and continues).
2. For stage 1 the limit is `max(LIMIT, before)`, and `before` is measured after stage 0 has moved. The limit therefore takes the temporary long hop that stage 0 just created.
3. `hi_rows` puts every vn -> lane row of a quad into the shared bank, including rows with three stations whose second station is not at the bank (the t68 row above).

**Finding 2: form C alone leaves 59 types over.** `j4a_check.json` against `j4a_base_check.json`: banks inside a core 296 -> 3 (t35 q3 s1, t43 q3 s1, t45 q0 s1 remain). Worst bits per over-core track, median 18.7 -> 6.4. t28: `g_ln[13]` vertical, 7,322 bits over 1,145 tracks, ratio 6.39. Four types get worse (t68 13.7 -> 24.67, t33 10.96 -> 13.7). So the sites take the banks out of the cores, and the bus still crosses a core at six times its tracks. Expect GRT overflow to stay on those types until form A.

**Finding 3: a site is a point with no area.** One shared bank is up to 4,184 flops (4 lanes x 1,046; max 4,707) at one coordinate. Minimum clearance to a core is 8.6 um (median 10.8) and two banks may sit 21.6 um apart. 4,184 flops are about 1,220 um2 of cells, about 49 x 49 um at 50 % use. This is the same class as the t21 / t60 / t42 DPL-0033 stops.

**Finding 4: the clock block is unchanged** while 16,856 rows move (median 56 um, p95 162, max 455). `added_taps` and `sink_sites_um` were made for the old sites. Not measured: the tap check is blocked by the t51 error.

Latency: unchanged (`lanes` and `latency` are identical to J3; station counts equal).

**Ranked fix (S81-DIE-R3 for the tool; FABLE-FIX-S81-LEAF-2140 for the form).**
1. Tool: keep a copy of each quad and restore it when any member fails the final check; take the limit from the original hops; group only rows whose stage sits at the bank. Re-run the sites on plan_j3b and accept the new plan when PRECHECK REACH on the leaf types equals J3 (3 findings).
2. Give each site a box sized from its bits and check it against cores and other banks.
3. After sites, run TAP-CAP and regenerate added taps for the moved banks.
4. Form A corridor on the 59 OVER types (leaf lane's call, as in FABLE-PD-S81-2040 section 3).

### 1.3 D8i C6 r13 (plan 05b98332, epyc9)

`intel2 ~/s81-die-r/build_d8i_c13.log`: ELAB_RC=0 at 23:24, strict bind running, no result at 23:57 (epyc9 load 219 to 370 on 96 cores). Static read of its plan: the 300 face-bus rows over 405 um (worst bit) and the t51 native cores are still in it; J3 fixes both. Nothing else found. Its col kits are the 114 in section 2.

### Stop list (A)
- Do not bind plan_j4a 5090069a4c41 or plan_j4b 3dc05566d640, and do not put START-TREE on top of either.
- Do not read "REFUSED" in the site log as "row unchanged".
- Do not start a whole-plan bind before PRECHECK has run on that plan.
- Do not launch svc kits from J before the `g_m[2]` slice is checked in the bound netlist.

## 2. (B) D8i col results (plan f2ec5ffc3bda, 114 builds)

No build has a GRT TT, a routed number or a signoff.json. All numbers are post-CTS at placement RC. Stage census from `intel2 ~/s81-geom-opus-d8i-watch/cur.sorted` (23:31). Kit root: `<host> /srv/opentallas-scratch2/claude/s81-geom-opus-d8g/d8i/tree6/kb_d8i/kits/<type>/gen/<type>/`.

| Family (builds) | Stage | CTS TT before -> after repair | FF hold gate (ends) | Tap mean spread | What limits it |
|---|---|---|---|---|---|
| col_h9_r1 (60) | place 6, CTS 16, GRT 38 | -15.4..-16.0 -> -13.5..-13.6 (45 kits) | -92.6..-120.8 (3,603 to 3,673) | 91 to 150 ps | Setup: half-cycle bank hops bs7 -> e7_u_w -15.39 (BANK-IN), e6_u_w -> bn6 -13.48 (BANK-OUT). Hold: zero-logic cross-tap chain |
| col_h9_r0_p2 (12) | place 1, CTS 10, GRT 1 | -60.0 -> 0.0 (7 kits) | -57.7..-65.1 (about 4,960) | 70 to 91 | cfg core s0/s1/s3 -> e*_u_w half cycle, closed by repair. Worst hold end is port-start |
| col_h9_r0_p4 (6) | CTS 3, GRT 3 | -82.4..-89.8 -> -16.3..+0.4 | -62.2..-84.2 (3,317 to 3,364) | 52 to 57 | Same s* -> e*_u_w class |
| col_h9_r0_p5 (12) | place 3, CTS 8, GRT 1 | -88.3 -> -10.8 (2 kits) | -90.1 (2,516) | 91 | s2 -> e2_u_w; one reset end -52 before repair; clk_t14 in-tap range 190 ps |
| col_h10_r0_p1 (6) | place 5, CTS 1 | -89.9 -> -13.8 (1 kit) | -85.8 (5,322) | 127 | Path not read (the kit restarted floorplan) |
| col_h10_r1 (12) | place 1, CTS 8, GRT 3 | -298..-317 -> -270..-289 (10 kits) | -42.1..-56.8 (about 3,500) | 43 to 69 | **HOP, not fixed by D8i**: u_lpl_9_r.u_y_q.q -> u_n24/fi[0], one unbuffered net, 769 ps of wire, -298.42 |
| col_h9_r0_p1 (6) | place 5, CTS 1 | none yet | | | |

Re-read by me: epyc9 `col_h10_r1__t1__cl95b37463__pv0713a75a`: `tt_setup_repair.log` "wns -269.94 -> -269.94", 115 cells, tns -19,454; `4_cts_post_hook.rpt` line 218 slack -298.42; `OT_TAP_CHECK WARN trees over 470 ps` on 17 taps; `OT_HOLD_GATE PASS FF wns_ps -42.13 endpoints 3480`.

Other points.
- col_h9_r1 is two netlists, not 60 measurements: e3f8a86c (epyc8) and 4593e8e5 (epyc7) give the identical -120.21295 on 3,603 ends.
- `OT_RELAY_POLY WARN` in `run_finish.log` names relay chains over 405 um as placed: h10_r0_p1 12 of 64 (worst 746 um per hop), h10_r1 9 of 60 (worst 867), h9_r0 p2/p4/p5 416 to 535, h9_r1 one at 495. Not checked against the plan's own measure.
- Build failures: 65 builds stopped at GRT on `OT_GRT_NONPORT native session must explicitly select FF` (the watcher's GOAL=route resume works on kits that kept a CTS DB). 20 builds died with make Error 247 (11 in CTS, 5 in place_dp, 4 in place_gp), not 4; cause not found. 5 builds (epyc9 h10_r0_p1, h10_r1 pv1a6ec9c2 / pv799da6f8 / pv86f5e3b9, epyc10 h10_r1 pv6a7ae122) restarted floorplan after a finished CTS with no error line; `stage_odb_cap.py` in the kit has an mtime two hours after `config.mk`, which is a candidate cause, not confirmed.

### The in-tap range: a kit-CTS balancing defect

Evidence: epyc8 `col_h9_r1__t1__...pve3f8a86c`, `run/logs/.../4_1_cts.log` lines 2262 to 2342 and 2603 to 2652.

| Tap | Sinks | Before pad: mean (min to max) | After pad: mean (min to max) | Range | (mean - min) / range |
|---|---|---|---|---|---|
| clk_t14 | 1,015 | 180 (173 to 273) | 388 (382 to 482) | 100 | 0.06 |
| clk_t27 | 1,216 | 266 (253 to 360) | 392 (380 to 487) | 107 | 0.11 |
| clk | 1,084 | 244 (234 to 325) | 388 (378 to 469) | 91 | 0.11 |
| clk_t9 | 98 | 264 (193 to 358) | 389 (318 to 483) | 165 | 0.43 |
| clk_t10 | 797 | 290 (247 to 351) | 408 (365 to 469) | 104 | 0.41 |
| clk_t25 | 2,999 | 339 (321 to 359) | 479 (461 to 499) | 38 | 0.47 |

- The range is there before padding. The pad is one buffer chain at the tap root, so it shifts the whole tap and keeps the range.
- On clk_t14, clk_t27 and clk the mean is 6 to 12 ps above the minimum: the bulk is early and a few leaves are about 100 ps late.
- The pad rule is `d = min(tgt - mean, target + OT_TAP_WINDOW_PS - max)` (repo `physical/die_plan/hbm/tkm_noid_kits/shared/tap_balance.tcl` line 239; the kit copies carry the same line), with target 450 and window 20 in the kit `config.mk`. Padding stops when the latest sink reaches 470, so a tap with a 100 ps tail keeps its bulk near 385. That is why tap means read 388..479 while every tap's maximum is 457 to 499.
- Where the tail comes from: TritonCTS path depth differs inside a tap (5 to 6 on clk_t14; 4 to 6, 6 to 9, 8 to 10 on others). `OT_CLK_LEAF_REPEAT` adds a stage on some leaves only (71 nets, 121 repeaters) before the balance. clk_t9 is a sparse tap: 98 registers over 171 x 200 um, no leaf buffers, ten leaf nets at 85 to 173 ps slew.
- It is not core pins (measured apart: `OT_TAP_CORE`, 78 of 85 within 20 ps of 450), not forwarded clocks, and not span (clk_t14 covers 118 x 176 um).
- 11 of 31 register taps have a range over 60 ps, 3 over 100.

**What it costs.** `pregrt_ff_hold.log` on 4593e8e5: cross_tap 1,334 ends at -120.21; port_in 1,168 at -74.43; port_out 1,018 at -30.24; same_tap 83 at -30.17. The worst end is the zero-logic transfer u_bin_frame_int_i1/q[1078] -> u_lpad_frame_int_i1.r[0][1078], launch clock 338.8 ps, capture clock 497.6 ps (TT). So the range itself costs little hold inside the tap; the damage is that whole taps sit early against their neighbours.

### Ranked fixes

1. **Kit balancer (owner of `tap_balance.tcl` / `clk_leaf_repeat`; S81-GEOM-OPUS has the kits to prove it).** Remove the tail first: the leaf repeater keeps cousin leaves at equal depth (repeat all leaves of a tap or none), and sparse taps such as clk_t9 get leaf clustering. Then the root pad follows the mean, because no maximum caps it. Estimator before any build: from the `OT_TAP_BALANCE` lines of the D8i kits, count taps with max - mean over 40 ps per family.
2. **Zero-logic chains (COL-CENSUS-1119 rows; S81-DIE-R3 applies).** u_bin_* -> u_lpad_* on one tap, or a lockup at the tap boundary (KV form C, main 29d0a6105e4c). No hold buffers for this class.
3. **col_h10_r1 (COL-H10-1119).** The lpl_7/8/9_r -> n24 rows it held back (per-bit west trunk through `relay_sites`, or a relay at n24). The condition it set is met at CTS: -270 after repair on 10 kits.
4. **Read at GRT TT (S81-GEOM-OPUS)** whether the s* -> e*_u_w half-cycle ends on h9_r0 survive routing RC; CC-BANK-2S only for a family that reads under -42 there.
5. **Flow (S81-GEOM-OPUS / flow owner).** Find the cause of Error 247 on one build before the resume repeats it, and do not rewrite kit files of a running build.

### Stop list (B)
- Do not treat the in-tap range as a plan (tap pitch) problem on col; the taps cover under 200 um.
- Do not add hold buffers for the bin -> lpad class.
- Do not quote col_h9_r1 as 45 results; it is two netlists.
- Do not relaunch D8i kits from synthesis for the GRT FF stop.
- Do not wait for GRT to write the col_h10_r1 n24 rows.

## 3. (C) Die hold

### cw8 result

`epyc10 /srv/opentallas-scratch2/claude/s81-clock-window/die/runs/s81/cw8/ca/sta_ca.log` (23:43, same chain, real views):

| | cw6 (control, ca_m) | cw7 | cw8 |
|---|---|---|---|
| Intra hold TT / FF | -309.05 / -265.95 | -336.23 / -288.46 | **-314.97 / -278.32** |
| Kit-contract FF | -99.99 | -268.93 | -135.00 (W 40, need 175) |
| Intra setup TT | +216.6 | +58.0 | +157.7 |
| CA crossings TT / FF | 0 / 2330 | 0 / 2330 | 0 / 2330 (lo 109.9 / 115.9) |

cw8 is slightly worse than cw6 on each line.

### Why, from the routed tap arrivals (`cw8/proof/tap_arrivals_{TT,FF}.json` against cw6; my scripts `cw8a.py` to `cw8d.py`, 393 partitions)

| Measure (TT) | cw6 | cw8 |
|---|---|---|
| Partitions with regular-tap range <= 40 ps | 28 | 36 |
| Partitions with all-tap range <= 40 ps (core taps at plan early) | 17 | 18 |
| Range median: col_h10_r1 / col_h10_r2 / col_h9_r0 | 70 / 58 / 60 | 119 / 165 / 72 |
| Range median: col_h9_r1 / col_h9_r2 / leaf / slice_station | 58 / 60 / 61 / 50 | 58 / 50 / 63 / 53 |
| Unshared stages inside a cw8 group, median / p95 / max | 14 / 18 / 24 | 10 / 12 / 20 |
| Regular-tap range inside a group, median / p95; share over 40 ps | 30 / 61; 30 % | 24 / 54; 14 % |
| Pair skew at 12 to 14 unshared stages, median / p95 | 16.5 / 48.2 | 16.8 / 53.3 |

Three causes.
1. **The groups are not the related taps.** `mkgroups.py` bisects each partition by position into groups of 16 or fewer. Of the 9,318 ports with a cw6 window need over 40 ps (`cw6/kwpairs.json`, TT), 1,100 have their worst partner in the same cw8 group. 88 % of the limiting pairs straddle two groups.
2. **The groups are too wide to share within 5 stages.** A 16-tap group covers about 500 x 500 um (col_h10_r2: 523 x 531 to 756 x 549 um) and its taps still part 10 stages up. Where a group is compact the form works: fW1_p1_b2 group 1 holds 9 taps within 8 ps.
3. **cw8 adds errors that repeat.** Group means sit apart (fW1_p1_b2: -30, +55, +16, -23 ps), and single taps fall far early: clk_t27 in col_h10_r2 at -120 ps on average over the 12 instances, clk_t9 in col_h9_r0_p1 at -66, clk_t21 / t29 / t24 in col_h10_r1 at -37 to -44. The part of the tap error that repeats across a family goes 8.9 -> 30.5 ps (col_h10_r2), 10.7 -> 22.4 (h9_r0_p1), 9.9 -> 15.3 (h10_r1). The random part is unchanged, 12 to 17 ps per tap in both trees.

One caution on reading any new tree. The cw6 worst pairs improve on cw8 whether or not they share a group (same group median 55 -> 21 ps, different group 56 -> 23). A pair picked as worst on one build is mostly noise and falls back on the next. The rv4 worst pair s_7S_x05 clk_t18 -> clk_t15 is 452 um apart with 70 ps on cw6 and -14 on cw8; the TT worst s_7S_x16 clk_t22 -> clk_t46 is 1,939 um apart. Neither says anything about the form.

### Is cw8 the right structural form?

The principle is right and cw8 does not implement it. Related flops must share the last stages of the tree; cw8 clusters by position and by count. The data also sets a physical bound: 5 unshared stages reach roughly 200 um. Related taps further apart than that cannot be matched by sharing in any tree.

### Ranked fixes

1. **Time related pairs only (DIE-LEVEL-CHECK-1119).** `die_sta_related --related-pairs` is on main (9d7bbe4c81, 9021c382ae, f29f0219cd). Export `related_pairs.json` for the 36 signed S81 type records and the D8i kits as they sign, and re-time cw6. The worst pairs today are 452 and 1,939 um apart with no known data path, so -302 / -309 is still a bound. This sets the real target for everything below.
2. **cw9 = clusters built from the relation, bounded by span (S81-CLOCK-WINDOW-1119).** Groups from the related tap graph (`related_pairs.json`, `tap_pair_affinity`), each at most about 200 um across and about 8 taps. Pairs further apart are left out. First on the pairs with no setup margin: cfg ROM and its s-station (59 um apart after the J3 c12_6 move), bank and ROM halves.
3. **Before cw9, fix the two cw8 tool errors on one region.** fW1_p1_b2 (col_h10_r2) shows both: the group latency seen by the partition DME (group 1 lands +55 ps with 8 ps inside it) and a far member that is not delayed (clk_t27, -120). Both repeat on every instance, so one region build with `only: [fW1_p1_b2]` proves the fix without a die run.
4. **Same-tree trim for the random part (S81-CLOCK-WINDOW-1119).** 12 to 17 ps per tap is the difference between the stage model and the routed tree, and it is new on every build. Measure routed arrivals, change only the last leg, keep topology and routes. After items 2 and 3.
5. **Related pairs too far apart to share: fix them in the kit.** Zero-logic transfers get one tap or a lockup (section 2 fix 2). For the rest, a hold-only per-port window from the measured need on families other than col and slice_station (COORD ruling stands for those two).
6. **The kit balancer of section 2 is on the die-hold path too.** A type view carries its own in-tap and tap-mean spread (91 to 150 ps on col_h9_r1) into every measured pair. Until it is fixed, a better die tree will not show in the measured number.

### Stop list (C)
- No further build of the cw8 form (geometric groups of 16) on S81, and do not port it to KV pv or QC cb / hc / su_l0 as FABLE-CLOSURE 23:15 lever 1 proposed "if the marks hold". They do not hold.
- No tree verdict from the previous build's worst pair.
- No -302 / -309 / -315 quoted as the S81 die hold before the related-pair run.
- Still no per-pin offset round and no CORE-EARLY-v2 on a tree that was not built for it.
- Do not widen col or slice_station windows.

## 4. (D) Types with two or more failed attempts in one class (outside leaf and serdes)

| Family | Class | Attempts | Evidence | In flight | Owner |
|---|---|---|---|---|---|
| slice_station__t51 | Plan macro with no bound instance | 3 x KIT_INPUT_MISSING on 3fa87b84b18; place FAIL on b05c98f7919 attempt_29 | epyc8 `.../b05c98f7919/items/slice_station__t51/attempt_29/gen/slice_station__t51/preflight.json`: `PLAN-SRC-MACRO placed macro ..._native_w: ... neither an instance nor a generate block` | J3 soft form (re-read: plan_j3 t51 has 0 hard cores, no child_root_taps); blocked by the tap pair of section 1.1 | S81-DIE-R3 |
| svc_hi rs t2 / t4 / t5, svc_lo rs t3 | MPL-0020: plan memory slice not in the netlist | attempts 13 to 15 on 3fa87b84b18 | `run_place.log`: `[ERROR MPL-0020] Couldn't find a macro named ...u_wq_mem.g_m[2].g_32.u_mem`; g_m[1] is placed | H8 rows in J; plan_j3 still names g_m[2] (re-read) | S81-SVC-SPLIT-1119, S81-DIE-R3 |
| svc_lo rs t6 / t7, rs_w t1; svc_hi rs t6 | Flat 3.5M to 4.9M cell kit | attempts 11 to 14, 13.6 h each | intel1 `ot-jobs/svc_lo_dsdv_svc_rs_w__t1-place-key-cardinal-885502-1795111198/work/run_place.log`: `OT_NATIVE_CELL_CAP actual_std=4892805`; floorplan repair flat at WNS -2,821 from iteration 59 to 1,095 on reset recovery pins | H8 rows in J; the b05c98f7919 relaunches are the same flat form | same |
| slice C: c1x_C t1 to t10, iq_C t1 | Kit tap spread, cell count, cross-tap hold | c1x_C t9 attempt_16, t6 attempt_46, iq_C attempt_44 | epyc9 `ot-jobs/dsdv_slice_c1x_C__t9-route-renewed-glider-2888571-1795133100/work/run_route.log`: tap mean 217..490 (spread 273), 36 trees over 270 ps (clk_t28 733), 494,769 cells, TT repair -1,422.28 -> -1,422.28, pre-GRT FF hold cross_tap 19,394 ends at -403.46 | None found (`S81-SLICE-C-TAPS.md` last written 05:56) | unowned: needs a lane |
| lepe mu_LP__t2 | In-GRT setup repair stuck | proof4 (-530 at CTS), proof5 (killed at -270.3 on `rid[834]`), wave attempt_22 | epyc9 `fable-lepe/proof6/r2/.../run_grt.log` | proof6/r2 (RIP1) in placement, 162,105 cells at floorplan, no TT number yet; opus-p7 (r2 + reset relay + 122 taps) admitted | FABLE-FIX-S81-LEPE |

bk_sel, gunit, eng, iqf and the other slice_station types do not qualify: their repeats are flow or infrastructure.

**Root causes and ranked fixes.**

- **t51.** The plan type declared two native hard cores with the die clock on their child roots; the bound wrapper is the soft form. Fix: the J3 rebind after the clk_t22 row. Its first J kit is the first physical read of t51; read `OT_TAP_BALANCE` and FF hold there.
- **svc MPL-0020.** The plan places a third wq_mem slice the netlist does not have (cause inferred: a depth parameter or define differs between plan and bind; the RTL was not compared). Fix: on the J3 bound netlist, compare the wq_mem slices with the plan rows before any svc kit; correct the plan row or `OT_SVC_ATT_MEM_MACRO` in the same event.
- **svc flat kit.** The wave kit is the old H16 form at 9 to 12 times the size of anything that has closed. H8 (10 provider cores signed, synth estimate hi rs t2 432,791 -> 228,760) is the fix and it is in J. No H8 cell count exists for the svc_lo types (58 boxes); read it at the first J census. Flow: stop the floorplan repair when WNS has not moved for about 50 iterations; each attempt holds 18 GB for 13 h.
- **slice C.** The kit's own line says "re-pitch taps to <= 221 um". Tap means 273 ps apart with trees to 733 ps put hundreds of ps on cross-tap paths, and the repair does not move the -1,422. Ranked: (1) a tap table row per C type at 221 um pitch or less, the lepe "122 taps" form; (2) read the -1,422 start and end points in `tt_setup_measure.log` to separate skew from a real long path before any RTL row; (3) 495k cells needs a split or a core: check whether capc5r and norm_finish are bound as cores in J. This is the kit-tap class of section 2 in its worst form.
- **lepe.** Same cause twice: the `rid` register that RIP1 pipelines. Read proof6/r2 at CTS TT and GRT TT by class; rows 4 and 5 are decided there. `proof6/dsdv_slice_lepe_mu_LP__t2` (not r2) holds proof5 inputs; do not read it as proof6.

### Stop list (D)
- No wave relaunch of t51 on b05c98f7919 or 3fa87b84b18.
- No further flat svc wave attempts on the D8h plan, and no MPL-0020 retries. The three stagnant intel1 jobs and the six relaunches in yosys cannot sign; stopping them is a COORD or svc-owner call.
- No more wave attempts of c1x_C or iq_C on the unchanged tap table; do not let iq_C run 30 GRT iterations at -1.3 ns.
- No lepe LP relaunch without RIP1; the wave attempt_22 form cannot close.

## 5. Owners

| Item | Owner |
|---|---|
| J3 r7 (clk_t22 row done 23:59); PRECHECK before each bind; svc g_m[2] check on the bound netlist | S81-DIE-R3 |
| `s81_hi_corridor.py sites` revert / limit / grouping fix, sites re-run on plan_j3b; site area check | S81-DIE-R3 (tool), FABLE-FIX-S81-LEAF-2140 (form A on the 59 OVER types) |
| TAP-CAP on J3 (84 col types, 221,868 new station flops) and on the re-run J4 sites plan; added-tap rows | PRECHECK-1119 with COL-CENSUS-1119 and the leaf lane |
| Kit balancer: leaf-repeat depth, sparse-tap clustering, pad on mean | owner of `tap_balance.tcl` (flow); S81-GEOM-OPUS proves on D8i kits |
| bin -> lpad zero-logic chains on one tap or lockup | COL-CENSUS-1119, S81-DIE-R3 |
| col_h10_r1 lpl -> n24 rows | COL-H10-1119 |
| Per-family GRT TT; Error 247; floorplan restarts | S81-GEOM-OPUS |
| Related-pair re-time of S81; related_pairs export for signed records | DIE-LEVEL-CHECK-1119 |
| cw8 tool errors on one region; cw9 relation clusters; same-tree trim | S81-CLOCK-WINDOW-1119 |
| slice C tap table and size | no live lane; S81-OWN-1119 to raise NEEDS-LANE |
| svc H8 kits, lo cell census | S81-SVC-SPLIT-1119 |
| lepe proof6/r2, p7 | FABLE-FIX-S81-LEPE |

## 6. Not checked

- J3: no bind result exists beyond the r6 tap error (r7 started 23:59), so LATCHECK, G0 and the die side of the frame_int +1 are unmeasured. I checked t51 against three sub-rules (pair spacing, outline, placement boxes); the bind may apply more.
- TAP-CAP on J3 and J4a: not evaluated. On plan_j3 and plan_j4a PRECHECK's tap check stops on the t51 error (it should run on plan_j3b; I did not re-run it), and on the C6 plan it stopped on a pin-table path error that comes from my running it outside the bind tree. My own nearest-tap estimate was not valid for leaf (grid taps are not listed in the plan) and I dropped it.
- Whether the H8 bound netlist has the `g_m[2]` slice; why the plan and netlist differed before.
- D8i C6 r13: no bind result at 23:57.
- D8i col: no GRT TT, routed or signed number exists. The late sinks of the in-tap tail are not named by instance (no per-sink arrival table in the kits; no STA was run). Which taps u_bin_frame_int_i1 and u_lpad_frame_int_i1 sit on. The kit `config.mk` window value 20 and the 20 x Error 247 count were read by the sub-agent only.
- cw8: the composite-sink code itself; I read its effect in the arrivals. The repeat test uses family tap names, since 390 of 393 partitions have their own type. The 200 um bound for 5 stages is read from group span against unshared depth, not from the stage model.
- Related pairs for S81: no list exists yet, so "88 % straddle" is against cw6 worst partners, not data paths.
- Section 4: the three KIT_INPUT_MISSING logs of t51; the -1,422 path in c1x_C; c3x_C, kv512_C, lepe_mu_C and lepw_*_C logs; attempts already cleaned from disk are not counted.
- Leaf and serdes builds (owned by the two Fable fix lanes).
