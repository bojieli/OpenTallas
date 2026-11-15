# FABLE-METHOD 2026-11-14 23:5x PST: why setup and hold fail so often, and whether the method is right

Owner questions: why are there often hold and setup failures; can good physical design upfront avoid them; are our
physical designs, layouts and processes correct at all.

Read-only review. Nothing built, stopped or changed. MEASURED = read tonight from a kit log, STA report or record.
INFERENCE is marked. Scratch copies of my extracts: rtx-pro session scratchpad `fm/` (agg_*.tsv, paths_*.tsv).

## 0. Short answer

1. Most timing failures here are not physical limits. In the 51 types that have a violating timing report on disk,
   only 3 fail setup on real logic depth, and those by 62-91 ps. The rest are (a) register-to-register paths with
   almost no logic that are simply too far apart for one cycle, (b) hard cores whose clock depth and interface
   arcs do not fit the clock budget of the type that holds them, (c) input-port hold that the type flow does not
   close and the gate does not count, and (d) tool and view errors (wrong clock edge in a balancer, stale core
   library, missing sink layout).
2. Yes, nearly all of (a), (b) and (c) are knowable from the plan and the signed core views before any build.
   The method document already asks for this (METHODOLOGY 12.9d "predict before build", 3.6 core latency contract,
   6.8 die STA). The checks exist as WARN or INFO lines and the builds run on regardless.
3. The architecture (plan -> bind -> abutted types -> sign-off) is a legitimate hierarchical flow and I would not
   replace it. Three things in it are structurally wrong and are named in section 3: cores were signed bottom-up
   with no clock-depth ceiling; the boundary hold contract is written in the SDC and then waived; and the die-level
   timing check that would close the loop runs on one die of four.

Timing is also the smaller part of the failure picture. Of 247 wave route jobs in 10 h today (FABLE-WAVE-REVIEW,
MEASURED), about 54 ended on timing (hold stop 28, repair time cap 12, routed near-miss 14). About 150 ended on
host memory kills, PG and pin collisions (DRT-0255/0206/0073), congestion and stale kits. Fixing timing alone does
not make the wave sign off.

## 1. Why setup and hold failures are frequent: the population by root cause

Sample: every post-CTS gate record (109, on 54 types), sign-off record (31 type-level) and STA log still on disk under
`kw43-wave-1109n/runs` on intel1, intel2, epyc2, epyc7, epyc8, epyc9, epyc10. For each type I took the worst
violating setup and hold path and read launch clock, capture clock, data delay, buffer count and gate count.
51 types have at least one violating path (QC 26, HEAD 16, S81 9). KV wave kits keep no gate records in that
tree; KV numbers below are from the lane records.

### Setup (TT), by type

| class | types | worst | what the path is | kind |
|---|---|---|---|---|
| S2 long reach, no logic | 18 | -446 | 12-48 buffers and 1-5 gates between two registers; data delay 1,000-1,250 ps of wire | plan error |
| S1 hard-core boundary | 8 | -802 | boundary flop or core to a hard core; core clock pin 100-250 ps off target, core pin setup arc 130-350 ps | plan error (+ view error) |
| S4 logic depth | 3 | -91 | 10-13 gates (sle_hc2 -62, hd_ctl -88, coll_ftc -91) | real limit, small |
| inside the gate (>= -42) | 8 | -33 | | pass |

Measured examples:
- S2: QC slw_fw_v2 -446 (`u_cland_cmd_wi ... u_dsel/y -> u_bin_cmd_wi/q`, 40 buffers, 2 gates, launch 270, capture
  833+222). QC sle_stm_v3 -444 (48 buffers, 4 gates). QC fw_v1 x4 and fw_v3 -236 to -279: one path,
  `u_bin_x_fe_p1_i/q[551] -> u_core.ch_dn_o`, 18-37 buffers. QC sc_v1, sc_v3, st_b_v2 x2 -162 to -202: the reset
  start relay `u_cland_rst_* -> u_cland_rstart_tx`, 17-20 buffers, 3 gates. HEAD hd_spn -145: `u_rrl_118/export_q`
  to port `rst_start_raw_42`, 13 buffers (the 1,261-um reach HEAD-99 already fixed by a pin move). In all of them
  the two clocks are within 30-90 ps of each other. The clock is not the cause; the distance is.
  A buffered wire here costs about 0.65 ps/um (hd_spn: 806 ps for 1,261 um), so one cycle carries a zero-logic
  hop of about 900 um at best. These paths cross a 613 x 1,339 um slot end to end.
- S1: QC slw_su_l1 -802 on 5,775 endpoints (routed). Path `u_bin_x_su_c_i/q[44] -> u_lane7/c_i[45]`: 28 buffers
  (1,400 ps of wire) AND the core: `OT_TAP_CORE u_lane4/clk pin -118 + internal 454 = effective 335 (target 250)
  WARN early core tap still late`; core pin setup arc 328 ps; related-pair skew 555 ps (`pair_skew.tsv`).
  S81 col_h9_r2 -338 (kit generated tonight): core to core, `u_u_s10 -> u_u_e10_u_w`, 2 buffers, 0 gates.
  `u_u_e10_u_w/clk pin -238 + internal 533 = effective 295 WARN`; `u_u_s10/clk[0] pin 166 + internal 271 =
  effective 437 WARN ... needs an early core tap`. Of 79 core clock pins in that type, 39 OK, 40 WARN.
  The launch core's clock-to-output (about 480 ps) plus the capture core's pin setup arc (346 ps) is 826 ps of an
  833-ps cycle before any wire. S81 leaf t25 / t54 -221 / -302: boundary flop to hard core `u_u_lf4_u_rxsf/rxsb`,
  20 buffers, core pin setup 127-132 ps, core clock 78-147 ps early.

### Hold (FF), by type

| class | types | worst | what the path is | kind |
|---|---|---|---|---|
| H1 input port to first flop | 10 (+8 under 25 ps) | -145 | `arst_n`, `start_i`, `ft*_i`, `link_i`, `cland_dn_fault*` into the first register; 1 buffer | contract error |
| cross-tap / core-tap internal | lane records | -441 | flops on different taps or behind a core tap, 5-32 k endpoints | plan error |
| tool artifact | 2 cores | -316 | balancer padded 1,115 flops by 430 ps | flow error |
| small internal | 5 | -77 | -7 to -77, tens to hundreds of endpoints | normal repair |

Measured examples:
- H1: HEAD hd_spn_eshim_rx sign-off: FF hold -95, 2,880 violations, 2,311 of them start at an input port, 0 at
  an internal register. hd_turn_b 2,278 of 2,878; hd_st_n4 2,071 of 4,158; hd_spn_wshim_rx 2,313 of 2,884.
  Path `start_i -> u_run_in/q`: the SDC lets the input arrive 90 ps before the nominal clock
  (`set_input_delay -min` -40 to -90 against the virtual clock), the first flop is clocked at 335-360 ps, and the
  flow puts one buffer on the path. S81 slice_station t17 / t28: `ft1_i -> u_ft_ft1_o_0`, -66 to -78 after CTS.
  R-MINIMAL counts internal hold only, so these types sign off with this open.
- Cross-tap: KV kv3_pc FF hold -385 to -441 on 18,021-31,883 endpoints; canary 1 had 0 of 8 core clock pins inside
  the window (305-974 ps off). S81 col_h9_r2 post-CTS estimate -301 / -312. QC cbn -112 to -237 on 7-30 k.
  QC st_b, sc, stm, fw estimates -100 to -114 after CTS.

### Tonight's five root causes, checked

| | claim | check | verdict |
|---|---|---|---|
| a | balancer read rise arrival on inverted sinks (KV ring hold) | epyc10 `oversize-1/rk2/kv_cland_w269_ns_0fea0`: after STB-EDGE-1 `OT_STB before fclk ... spread 16`, `0 delay buffers`, sign-off TT +161.8 | CONFIRMED. Flow error |
| b | hd_host_e timed against a stale u_epc .lib | epyc2 `type-hdepc/retime`: with the signed lib TT -173.45, non-port FF hold -10.24 (179) | CONFIRMED. View error; -173 still open and it is class S2 (SRAM to core data path, about 130 ps of routing) |
| c | QC su_c variant with no sink layout: 30 taps for 40,453 sinks | QC-CORES-HEAD 21:20 record (kit log: 11 taps over the 1,200-sink cap, average sink wire 522 um); sibling with a sink file is clean | CONFIRMED from the lane record, kit not re-read by me. Plan data error |
| d | core clock taps placed inside cores (PIN_FACE_BLOCKED) | the guard exists since 11-12 and runs in WARN mode by default | NOT VERIFIED for tonight's instance: I did not find its record. The guard being a warning is itself the finding |
| e | Fable estimate of 320 ps u_epc skew was wrong | epyc2 `type-hdepc/diag/ffclk.tsv` (11,586 flops): input flops 418-447 ps, about 50 ps apart from the output flops | CONFIRMED. My predecessor inferred skew from library arcs of a stale library. Do not derive a core's clock depth from its .lib arcs; dump the flops |

### Split by kind

- Design and plan errors (the majority of the ps and of the types): reach of zero-logic hops (18 types), core clock
  depth above the type clock budget (8 types sampled; the S81 col family is 216 types, KV pc and QC su/cbn follow
  the same pattern), tap sets that do not match the sinks (c, KV canary), boundary hold contract not enforced (10+).
- Flow and tool errors: wrong edge (a), stale library (b), SIGPIPE in the ECO loop (all 5 near-miss ECOs,
  NEARMISS-FIX-1), kits generated from old source, the post-CTS gate that prints `setup_est -443.59 ... PASS`.
- Genuine physical limits: 3 types, -62 to -91 ps, on 10-13 gates. Within reach of ordinary repair or one
  retimed stage.

## 2. Can good upfront physical design avoid them? Against industry hierarchical practice

| industry practice | what we have | state | failures it would remove before build |
|---|---|---|---|
| Top-down timing budgets per block pin, checked before P&R | `budget.json` per type holds clock insertion, taps and pins; no per-bus arrival/required budget; AUTO-GEOM computes r2r reach and reports `r2r=FAIL(1244.65)` | PARTIAL, advisory | class S2 (18 types): every one is a station-to-station distance the plan already contains |
| Interface timing models (ETM / ILM) of hard blocks, one version per signed block | signed core .lib exists; kits bundle a copy; `core_latency.txt` is labelled "legacy diagnostic, NOT a ... contract" | WRONG in management | (b), and it makes every S1 number suspect until audited |
| Block built to a clock insertion spec given by the parent | cores are signed bottom-up; the parent then measures I and offsets the pin (3.6 early tap) | MISSING ceiling | class S1 and most cross-tap hold: cores have I = 271-533 ps inside types whose whole budget is 250 |
| Register at the boundary, on both sides | yes: face flops, `face_guard`, feed-through stations | HAVE, and it works: no failing path in the sample is boundary logic depth | - |
| Feed-through planning with a reach rule | stations exist; the reach rule (hop about 360 um) is checked in G0 for lanes but not for reset/start relays, landing-ring control or core-to-bin paths | PARTIAL | the reset-start relay class (5 QC types) and the bin-to-core class |
| Block CTS to a common latency, top clock to block clock pins, CPPR, skew groups | per-type taps balanced to 250 (S81, QC) or 450 (HEAD) +/- 20 on the mean; forwarded-clock landing rings on most buses | HAVE, heavy | see section 3.3 |
| Hold: fix inside the block against a stated IO min-delay contract, plus margin for inter-block skew | the contract is in the SDC (`-min` -40 to -90); R-MINIMAL does not count port hold | WAIVED | class H1 moves from "unknown until die STA" to closed per type |
| Top-level STA on block models at every plan change | METHODOLOGY 6.8 / 12.4a; `die_sta.py` exists; HEAD strict bind + STA passed on rp21z18d; S81, QC, KV: no run, no lane | NOT RUN on 3 of 4 dies | finds S1, H1 and seam skew in minutes instead of after an 8-14 h build |
| One library set per build, hashed, checked against the signed index | receipts are hashed (`libraries.json`) but never compared with the signed index | MISSING compare | (b) class |

Which would remove the most: (1) a pre-build plan check of every register-to-register hop and every core
interface against the clock budget, run as a fail-and-fix step, removes S2 and S1, which is 26 of the 29 sampled
setup failures and the large hold classes. (2) Enforcing the port hold contract removes the largest count of
violating endpoints. (3) The library compare removes a class that otherwise looks like a design failure for days.

What upfront design cannot remove: tool bugs like (a), and the 3 logic-depth paths. Those are normal and cheap.

## 3. Is the method correct at all?

### 3.1 Plan -> bind -> type kit -> sign-off: sound, but open-loop

Abutted partitions with registered faces, hard cores inside, bind-time latency check: this is how large chips are
built and the functional side (bind, LATCHECK, G0) works. What is missing is the closing arc. Types are signed in
isolation against assumed neighbours (a virtual clock at the type's own mean latency and fixed IO delays), and the
assumption is checked only by die STA, which does not run on S81, QC or KV. Until it runs, "36 of 394 signed"
means "36 types meet their own SDC", not "36 types work together". I expect die STA to reopen some signed types;
it is cheaper to learn that now, with 36 + 4 + 5 signed, than at 300.

### 3.2 The gates

- R-MINIMAL (DRC 0, TT setup >= -42, internal FF hold >= 0) is a fair academic sign-off for the inside of a block.
  Leaving port hold out is the one part that is wrong for an abutted design: there are no die-level cells, so a
  port hold failure can only be fixed inside a type, which means re-signing it.
- The post-CTS gate checks only that the mean pin-flop insertion is within 20 ps of the bound. It printed PASS on
  every one of the 109 records, including setup_est -443 and hold_est -312. A kit with a zero-logic path at -440
  after CTS cannot close in route; it then spends 8-14 h and a host slot. The early stops were deleted on 11-13/14
  as conservative limits. FABLE-WAVE-REVIEW measured the result: the same builds fail later and cost more. I am
  not asking for the old limits back. I am asking that a post-CTS result that no router can fix is sent to the
  plan owner instead of to the router (section 4, item 4).
- "Visual and geometry verdicts never block" has the same effect on class S2: AUTO-GEOM already flags r2r reach.

### 3.3 The die clock model: two mechanisms, each paying for the other

The die uses both a common-latency contract (every type balanced to 250 or 450 ps so that neighbours can talk
synchronously) and forwarded-clock landing rings on most buses (so that neighbours need not be balanced).
The rings are 35-75 % of the cells of KV types and 11-64 % of QC types (OVERSIZE-1 inventory), cost about 25 cells
per bit, drive the 400-700 k cell counts, the ring-band congestion, and carried bug (a). The synchronous contract
is still needed for resets, starts, feed-through stations and core taps, and that is exactly where the hold and
core-tap failures sit. This was a deliberate owner decision (12.11, landed clocks as the main path) and it does
buy hold safety by structure on the ringed buses; I would not undo it at this stage. But it should be said
plainly: the design pays for clock-domain-crossing hardware on almost every bus and still has to close a
synchronous clock, with a bespoke tool chain (tap balance, subtree balance, core taps, pair affinity, landing
placement, dozens of scripts per kit) where each script is a place for an error like (a).

Inside a type, the measured boundary-flop spread is 60-160 ps (QC 183-346, HEAD 401-487, S81 142-277 ps
insertion), while the gate looks at the mean within 20. Zero-logic synchronous crossings between two types
therefore see up to about 100 ps of skew with about 40 ps of FF clock-to-output: not safe by structure. That is
what the port hold contract is for.

### 3.4 Structurally wrong, named

1. Hard cores have no clock-depth ceiling. S81 and QC types balance to 250 ps and hold cores with internal
   latency 271-533 ps; the early tap needed (pin at -238 ps) is "still late" in the kit's own log. HEAD balances to
   450 ps, its cores fit, and HEAD is the die with 19 of 26 types signed (INFERENCE that this is a cause and not
   only a correlation).
2. The boundary hold contract is written and then waived (3.2).
3. Parent kits carry private copies of child views with no check against the signed index (b).
4. Warnings that predict failure do not stop or reroute anything: `OT_TAP_CORE ... WARN`, `r2r=FAIL`,
   `PIN_FACE_BLOCKED` in warn mode, `setup_est -443 PASS`. slw_su_l1 reached attempt 16 and cbn_q00 attempt 25 with
   the cause printed in the first hour of attempt 1.
5. Die STA is in the method and not in the loop.

Not wrong: abutment, registered faces, feed-through stations, bind and LATCHECK, hold buffers on data paths,
TT/FF corners for an academic target. Reused types are an asset: one fix closes many instances.

## 4. Ranked changes

| # | change | evidence | expected effect | cost | owner |
|---|---|---|---|---|---|
| 1 | Plan timing audit before any kit launch, one script over plan + signed core views, no build: (a) every register-to-register hop that is not a priced lane (reset/start relays, ring control, bin to core, core to core) against a reach limit of about 600 um or 400 ps; (b) every hard core: internal latency I against the type budget, pin setup and clock-to-output arcs summed along each core-to-core and core-to-face path against 833 ps. Output per type: PASS or the list of hops that need a station or a core move. A FAIL goes to the die owner as a plan item, not to the wave | S2 18 types (-162 to -446), S1 8 types (-221 to -802); 40 of 79 core pins WARN in col_h9_r2; all visible in plan data | removes 26 of 29 sampled setup failures and the core-tap hold class before build; for S81 col it decides 216 types with about 26 builds | 1-2 days of tool work; AUTO-GEOM r2r and `OT_TAP_CORE` arithmetic already exist and can be lifted | PLAN-READERS-1 (tool), die owners (fixes) |
| 2 | Core clock-depth rule: a core is usable in a type only if I <= type budget minus about 50 ps, or the plan carries a deliverable early tap for it (spine arrival checked, not assumed). For S81 and QC choose per die: raise the type budget to 450 as on HEAD, or re-sign the deep cores with a shallower tree. Decide with numbers from audit 1b | u_u_e10_u_w I = 533, u_lane4-7 I = 416-465, budget 250; pair skew 555 ps; kv3_pc 0 of 8 pins in window | ends the "early tap still late" class on S81 col, QC su/lane, KV pc | budget change: re-sign of 36 S81 + 4 QC signed types (owner: re-sign is fast). Core re-sign: per core, 1 build | DIE-S81-92, DIE-QC-103, KV-102 with a Fable review of the choice |
| 3 | Signed-view integrity: at kit generation and again at sign-off, compare the hash of every child .lib/.lef with the signed index (AGIdock INDEX); mismatch = regenerate, never time. Run it once now over every parent kit not yet routed | (b): 222 of 395 ps were a stale library; KIT-OPS-6 stale-lib audit is open; `libraries.json` receipts already hold the hashes | removes false timing failures and stops wrong fixes like (e) | half a day; the receipt exists | KIT-OPS-6 |
| 4 | Post-CTS triage instead of PASS: when the GRT-RC estimate shows setup below about -150 ps on a path with <= 5 gates, or hold below about -150 ps on more than 1,000 endpoints, the kit stops and posts the worst path (start, end, buffer count, both clock arrivals) to the die owner. Not a limit on what may route: a route cannot add a register or move a tap | 109 of 109 gate records PASS, 26 of them (23 types) with setup_est below -150; attempts 16 and 25 of unchanged kits | frees the route slots of builds that cannot close (about a fifth of the wave), and turns each into a plan item within 1 h instead of 14 h | small: the numbers are already printed | KIT-OPS-5 / 6, KIT-WAVE |
| 5 | Die STA on block models in the loop for S81, QC, KV as it is for HEAD: after every bind, with signed views where they exist and budget models elsewhere; report seam setup, seam hold and core-tap arrival per type | HEAD ran it (rp21z18d PASS) and is the furthest die; the other three never ran it; class H1 and seam skew are invisible without it | finds interface errors in minutes; tells us whether the 45 signed types hold together | the tool exists (`die_sta.py`, 6.8); one lane per die for a day | COORD to assign; die owners |
| 6 | Enforce the port hold contract inside the type: count port-start hold in the gate against the SDC `-min` value, with the value set from the measured boundary-flop spread (about -60 to -90 ps), and let hold repair pad the inputs. Forwarded-clock ring inputs are already safe and stay out | 2,071-2,313 port-start hold violations per signed HEAD type; slice_station ft inputs -66 to -78 | closes synchronous crossings per type; no re-sign wave later | hold buffers on a few thousand inputs per type; an ECO on the signed types | KIT-OPS-5 (gate), die owners |
| 7 | Clock tool chain: one regression per script on a small kit with known answers (inverted sinks, negedge flops, core taps, missing sink file), and a hard error when a tap exceeds its sink cap or a type has no sink layout | (a) wrong edge, (c) 30 taps for 40,453 sinks with 11 taps over the cap, both printed and ignored | stops tool artifacts from reaching 8-14 h builds | 1-2 days | KIT-OPS-6, CLAND-MACRO-1 |
| 8 | Stop measuring clock depth from library arcs; where a core's internal clock matters, dump its flop arrivals from the signed database once and store them with the view | (e): 320 ps inferred, 50 ps measured | prevents wrong structural fixes | minutes per core | die owners, Fable reviewers (including me) |

Order: 3 and 4 tonight (cheap, stop waste). 1 and 5 tomorrow (they tell us the true size of the problem). 2 and 6
follow from their numbers. No item needs a new die plan by itself.

## 5. What I did not check

- KV kits directly (no gate records in the sampled tree); KV figures are from FABLE and lane records.
- Whether the S1 core arcs in col_h9_r2 and su_l1 come from current signed libraries. After (b), each S1 number
  should be re-read once item 3 has run. The su_l1 kit is from 11-11.
- Root cause (d) for tonight's instance.
- HBM (parked).
- The sample is what cleanup left on disk: 51 types with reports, out of about 600 open. It is biased toward
  types that got as far as CTS. Types that die earlier (PG collisions, congestion, memory) are not timing failures
  and are covered by FABLE-WAVE-REVIEW.
