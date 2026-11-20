# FABLE-PD-QC-1955 2026-11-19 19:55 PST: QC events N46Q / N46R / N46S, structure check + open failure classes

Reviewer: FABLE-PD-QC (Fable). Read-only: no job launched, stopped or patched; no plan edited. Technical PD only.
Marking: **V** = I opened the plan, report, log or kit file this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Sources (V), all epyc9 `/srv/opentallas-scratch2/claude/qc-plan-r3-n41p/` unless named: `n46/plan_n46_e6.json` (N46P = N46Q plan),
`n46/plan_n46_r.json` (cd014b8d62ac), `n46/plan_n46_s.json` (a244272e7da7), `n46r/out_all/{strap_resite,n46r_report,sidecar_n46r}.json`,
`n46/n46s_report.json`, `bind/bind_s29q103S4Q9N46*`, `gates/latcheck_*`, `pkits/pk46_s2b`, `pkits/pk46_cbf1`,
`fable-fix-qc-collcore/opus/pkits/pkw2b_coll`, epyc7 `qc-ttctlm-1119/r2a,r2b`, hub `lanes/handoff/QC-PADLEG-rows.json`.

## 0. Headline

| event | bind state 19:52 PST (V) | structure verdict |
|---|---|---|
| N46Q (tools d2c3111be068) | BIND_RC 0, LATCHECK 1921/1921 PASS, G0 = control (4 kit_fit) | sound, nothing to add |
| N46R (strap + fall fold) | first bind FAILED (BIND_RC 2, "legacy landing added_cycles must be 4"); retry N46R2 running, 0 errors so far | geometry and latency tables sound; two caveats (1.3, 2.3) |
| N46S (PADLEG 59 rows) | first bind FAILED on the same line; retry N46S2 running | sound as an estimator; 7 rows miss the lane's own first-hop budget (3.2) |

1. **The 498 moved strap pins all land on free legal sites (V).** But 408 of them were never on a hard core: they were blocked only by a
   stale `contents[]` reference box. 376 ID pins of cbn_q11 / cbx_q10 left the tile edge and now sit 1,170 to 1,542 um away at the type centre.
2. **The fall-aware fold agrees with the lane latency table on every lane (V).** Its proof clock is n46ct_e, which predates f3 / f4a / e4 / e5.
3. **N46S: 0 nominal hops over 405 um, no station in or next to a hard core (V).** x_ctl_i on the 7 fw types still has a 378 um first hop
   under a 109 um bit window.
4. **The cbf_q00_s2 -1972 ps path has a plain structural cause (V):** its three landing status children point at collector nodes
   2,669 / 1,313 / 2,960 um away. The sibling cbf_q00__cl1b5a6458 has the same node names 0 / 39 / 6 um away. No event fixes it.
5. Not judged, no result yet: coll_core pkw2b (in global placement at 19:44), pkw3 (kit RTL), tt_ctlm r2a (early route flow).

## 1. N46R strap pins (17 types, 498 sites)

### 1.1 Checks (V, my own script on plan_n46_r.json, independent of region_form)
| check | result |
|---|---|
| new site on the 4.32 um lattice | 498 / 498 |
| inside a `hard_cores[]` or `contents[]` box + 5.4 um | 0 |
| inside a clock reserved site + 1.08 um | 0 |
| outside the outline (4.32 um margin) | 0 |
| within 1 um of a station reg, relay site, ft station or clock tap anchor | 0 |
| duplicate strap sites in a type | 0 |
| whole plan, strap sites in a core / content halo | N46Q 498 of 9,121; N46R 0 of 9,136; N46S 0 of 9,136 |
| strap width = number of sites, all 1,599 straps | yes |
| strap ports false-pathed in the kit SDC (pk46_s2b constraint.sdc line 262) | yes, so a moved pin changes no timing |

### 1.2 What blocked the old sites (V)
| group | sites | blocked by | move (median / max um) |
|---|---|---|---|
| slw_su_l1 x2 (count straps) | 70 | `hard_cores` u_lane5 (pins inside the core body) | 34 / 56 |
| sle_stm x4, slw_stm x2 (count straps) | 20 | `hard_cores` ot_rom_4096x266_m8 m3 (inside the body) | 771 to 966 |
| sle_su_c, slw_su_c x2 (count straps) | 32 | `contents` u_suvm_u_vm8q_u_ch only | 52 to 55 / 61 |
| cbn_q11 x2, cbx_q10 x4 (tile_id 16 bit, sidx 3 bit) | 376 | `contents` u_tNN qfd_tile_nk_romleaf_rpf only | 1,170 to 1,179 / 1,542 |

- The 90 `hard_cores` cases were real: an M5 pin inside a hard-core body. The move fixes them.
- cbn_q11 / cbx_q10: the old pins were at x 79.9 and 1155.6. The real hard core (`hard_cores` u_t23 qfd_tile_nk_a0c, x 86.4 to 544.3;
  u_t33 x 691.2 to 1149.1) plus 5.4 um ends at 81.0 and 1154.5. So the old pins were 1.1 um outside the real halo, legal. They only
  touched the `contents[]` copy of the same tile, which is 8.64 um off (x 77.8 to 535.7 and 699.8 to 1157.8) and carries the old module name.
- The old 0.864 um pitch at the tile edge was pin abutment to the tile ID pins (I). Each of the 16 + 16 + 16 bits is now a static net of
  about 1.2 mm from the type centre to its tile.

### 1.3 Verdict and fix (P)
Sound to bind and ship. No timing effect (false path). Two follow-ups, neither blocks N46R:
1. **Rule (QC-PLAN-R3, `region_form._strap_lattice_free`):** when an instance is in `hard_cores[]`, use that box and ignore its
   `contents[]` copy. Then re-run the scan: expected 90 real cases, not 498. Do this before any other die uses the scan.
2. **Proof (wave, no new kit):** the first cbx_q10 / cbn_q11 kit on N46R reads max slew on the 48 to 70 strap nets after repair_design.
   If they cost repair buffers in the tile channels, put the 376 ID pins back at the tile edge in the next event (one row).
Do not revert inside N46R.

## 2. N46R fall-aware count-align fold

### 2.1 Consistency with the lane latency table (V)
| check | result |
|---|---|
| `cycles = stations + boundary + fixed + clock_landing + pad`, plans Q / R / S | 1921 / 1921 each |
| `lanes[].fixed_cycles` = `latency.lanes[].fixed` | all, Q / R / S |
| report lane old / new = plan Q / plan R cycles | 1026 / 1026; no changed lane missing from the report |
| lane `clock_landing` = sum of its ports' sidecar `added_cycles` (R and S) | all lanes |
| sidecar `count_aligned.ports` sched_lat / K / depth = report port rows; sched_lat = port added_cycles | 2525 / 2525 |
| 14 latency groups (su_vmw_ctl) equal inside the group | yes in Q, R, S |
| totals | Q 21,737 cycles, R 20,571 (-1,166), S 20,626 (+55) |
| lane delta Q to R | -3: 9, -2: 166, -1: 829, +1: 22 |
| margins | lo min 108.1, hi min 116.8; 146 ports lo under 150 ps, 31 ports hi under 150 ps |
| K straps | 19 widened 6 to 7, 4 narrowed; new sites pass section 1.1 |

### 2.2 The bind failure (V)
`sl_W5_ctl__x_ctl_fw__1` is the only count-aligned port with `output_qreg` 1. The fold moved it from sched_lat 4 to 3 (K 22 to 21,
m_lo 222.3). The legacy price check (3 + FREG + QREG) refused it. The tools fix (main a2fb7e625dd) skips that check for count-aligned rows.

### 2.3 Caveats (P)
1. **Proof clock is older than the plan.** The intervals come from n46ct_e (plan_n46_ct). N46R also carries f3 (cbf_q00_s2 own START +
   landing remap), f4a, e4, e5. K is right only where the landed phases did not move. QC-PLAN-R3: re-time the N46R2 bind with
   `--ca-write-fall` (TT + FF) before calling the fold proven; read the cbf_q00_s2 crossings first.
2. **QREG port.** On N46R2, LATCHECK must show as-built 3 cycles on `sl_W5_ctl__x_ctl_fw`. If it shows 4, the ring still has the output
   register and the row must stay at 4 (one K step back), not the check loosened.
3. 146 crossings have under 150 ps on the low side. That is inside the rule (none under 100), but it is the first place a clock change shows.

## 3. N46S QC-PADLEG rows

### 3.1 Checks (V, plan R against plan S, matched by position because conn names repeat inside a type)
| check | result |
|---|---|
| station sets changed | 59, on 22 types, only `regs_um` differs |
| stations added | 48; lanes +1: 47, +2: 4 (51 lanes, +55 cycles) |
| nominal hops (from, regs, to), Manhattan | 244 hops, max 386 um, 0 over 405 |
| reg inside a hard core + 4.32 um, inside a `contents` box, or outside the outline | 0 |
| straight leg crossing a hard core | 0 |
| new reg within 12 um of another station or ft station anchor | 0 |
| `bit_sites_um` group count against reg count | consistent |

### 3.2 Findings
1. **x_ctl_i on 7 fw types keeps a 378 um first hop (V).** Rows changed the tail (… 189, 235, 59) but not the head. The bus is 631 bits in a
   109 um window. By the lane's own rule (main 1841dad39c4: reach - span/2 - 33) that hop is 378 + 54 + 33 = 466. It matches the open kit
   class slw_fw bin->pad 440 legs (R, QC-PADLEG). Types: sle_fw_v1 x2, sle_fw_v2 x2, slw_fw_v1 x2, slw_fw_v2.
   Fix (P, QC-PADLEG row, QC-PLAN-R3 composes): re-space the first three hops 378 / 189 / 189 to 252 each. 0 regs, 0 cycles.
2. **slw_fw_v1 x2 x_fe_p2_o: new first hop 386 um from the core leaf (V).** Borderline once the producers spread. Watch in the first kit.
3. **Rows keep `from_um` / `to_um` / `leaf_um` (V).** The estimator hops are measured to anchors the lane itself calls wrong (leaf at core
   centre, consumers y 500 to 1190). The 405 um result above is necessary, not proof. Proof = one fw kit to GRT TT (r712).
4. **Plan-wide after N46S (V):** 216 of 1,233 station sets exceed the generator budget on a face hop: sle_ctl 56, slw_fw 27, sle_fw 22,
   sle_fe 20, slw_fe 17, cb* 34, su 24, stm 7. 54 sets have a nominal hop over 405 (cb* bc_i 614 to 637 um).
   Do not act on the cb* bc_i number: pk46_s2b measured bc_i00 / bc_i10 at +246.5 / +245.3 ps (R, QC-PLAN-R3), so that anchor is not the leg.

## 4. Failure classes none of the three events fixes

### 4.1 cbf_q00_s2 landing status collect, -1972 ps TT (owner: QC-PLAN-R3 for the plan, clock_landings / bind owner for the check)
- V, path in `pk46_s2b … 4_cts_final.rpt`: `u_cland_monitor_2/ready` -> `u_cland_collect_rst_n_t29/ready_o`, 28 buffers, one segment with
  1,358 ps slew and 429 ps delay, single cycle.
- V, `landing_placement.tcl`: monitor_2 at (1194, 2349); collector rst_n_t29 at (64, 549).
- V, `landing_contract.json collector_children` against the kit collector boxes:

| child | node | cbf_q00_s2 child -> collector | cbf_q00__cl1b5a6458 (pk46_cbf1, same runtime) |
|---|---|---|---|
| 0 | rst_n_t30 | 2,669 um | 0 um |
| 1 | rst_n_t28 | 1,313 um | 39 um |
| 2 | rst_n_t29 | 2,960 um | 6 um |

- V: cbf_q00_s2 has 147 taps, the sibling 101. The node names are the same in both. In s2 those names are taps at (1158, 549), (679, 540),
  (64, 549). `bind_reset_anchor.json`: cbf_q00_s2 "anchored 39 kept 39": relays are re-anchored by position, children are not.
- Root cause: the f3 own-START form kept the sibling's child node names. Not a wire, not f4.
- V, scan of the 9 QC types with a kit on epyc9 (13 child rows, 35 local rows): only cbf_q00_s2 has a remote child. Worst local source
  420 um (sle_st_a_v2 x_ctl_fw_i). The other hosts were not scanned (find timed out).
- Fix, ranked (P):
  1. Re-pick the three child nodes by position (nearest reset-tree node to the child xy at the needed depth). 0 cycles.
     Expected: the three legs fall from 1.3 to 3.0 mm to under 50 um, as on the sibling. Proof: pk46_s2b again to CTS TT.
  2. Extend the reset-anchor check to `collector_children` and `local_sources` with the same 405 um tolerance, as a G0 row.
  3. Run the same child / collector distance scan on kits of the other hosts before the next QC event.

### 4.2 tt_ctlm, 24-level cone, GRT TT -167 (owner: QC-TTCTLM-1119)
- R: 49 of the worst 50 are logic depth from one flop u_75259; R2 (un-keep bmath + 4 copies) expected about 100 of 200 ps.
- V: r2a is in the route flow since 19:29, no timing line yet. r2b's client log ends "ot-run: interrupted (signal 15 …)"; check that it runs.
- Fix order (P): R1 (+1 cycle retime, pre-approved) is the only row sized to the miss; start it now, in parallel with R2, not after.

### 4.3 coll_core (owner: OPUS-FIX-QC-COLLCORE)
- V: pkw2b at global placement iteration 366, overflow 0.194 at 19:44. No place TT, no GRT round. pkw3 at kit RTL.
- V, pkw2b log: landing rings rec_rx_s0 / s1 / s2 (3,164 flops each) need 3 strip rows and the band fits 3; in_data needs 3, fits 4. No spare.
- Pass marks stay as set at 12:30: GRT round-5 sum under 5,000, inside-core share under 30 %.

### 4.4 PADLEG section 2 and 3, in no event (owner: QC-PADLEG-1119 rows, QC-PLAN-R3 composes)
| class | size (R) | state |
|---|---|---|
| sle_ctl internal, anchors off the macro pins | 13,120 legs | 38 rows B ready, +16 regs; my scan: sle_ctl is the largest family over budget (56 sets, V) |
| fw pass-through l9_wi -> x_st_a_o / x_st_b_o | 1,177 / 1,897 um | 18 rows A ready, +5 / +3 regs |
| stm core-internal spread | 1,374 legs | 4 placement guides, need main 1841dad39c4 or later in the event tools (N46Q tools are older) |
| cland ring -> bin | 500 to 840 um, 16 types | section 3 rows, not checked against hard-core footprints |
Rank: B, then A, then C with a tools refresh, then section 3 after a footprint check. One event (N46T), one fw + one sle_ctl proof kit.

### 4.5 su / st macro legs 800 to 1,222 um (QC-SUST-MACRO-1119; no post on the hub yet)
- V, plan S: every SRAM / ROM hard core in the su / st types has a registered site (station, relay or ft) within 290 um
  (su_c 63, st_a 89, st_b 277 to 290; 319 macros, 0 over 405).
- So the floorplan has room. The long legs are connections with no station row in the plan (24 skipped, R). Fix = add those conns as
  macro-anchored rows. No macro move.

### 4.6 Waiting only for a kit on the new event (V in plan or tools, unproven)
- cbn_q11 OT_XSTN_STRETCH: x_3_3 b_d now at x 1194.48, no longer on the d6 sites at 1159.92. The private relaunch on the old kit measures the old plan.
- su_c x3 DRT-0073: `OT_LEF_OVERRIDE qfd_dv_s8x_vmr.lef applied` in the N46S G0 log.
- slw_st_a_v2 cl9f076a5c TRUNK-CHAIN: needs the N46Q bind, now green.

### 4.7 Die level (R, DIE-LEVEL-1119; untouched by Q / R / S)
QC intra hold -334.7 TT; qfd_tile_nk_a0c core taps planned 483 to 568 ps early against a tree that delivers less (1,081 of 1,461 taps over
25 ps short). Owner: QC-PLAN-R3 clock / DIE-CORETAP-1119.

## 5. Small flow item (V)
chain_n46q / r2 / s2 run in parallel and share `plan_n45_pre_merge.json`, `gates/merge_n45a.txt` and `gates/final_bind_n45a.txt`. The
MERGE_NOOP / MERGE_CHANGED line and the final-bind tag can come from the other chain. Read the tag from each chain's own CHAIN_DONE line.

## 6. Stop list
1. No further cbf_q00_s2 timing kit until the three child nodes are re-picked. A rerun repeats -1972.
2. No multicycle or false path on the landing ready / fault collect paths.
3. No strap scan on another die with the `contents[]` rule. No revert of the 498 moves inside N46R.
4. Do not call the fall fold proven on the n46ct_e clock. Re-time on the N46R2 bind.
5. Do not loosen a check if LATCHECK shows 4 on `sl_W5_ctl__x_ctl_fw`.
6. No station rows from nominal cb* bc_i hops (kit shows +246 ps).
7. No tt_ctlm rerun without R1 or R2; no station or core-move row for it.
8. No coll_core verdict before GRT round 5; no new coll_core row before pkw2b / pkw3 read.
9. No section 3 cland rows before a footprint check; no stm guides on tools older than 1841dad39c4.

## 7. Not checked
Renders of the three plans (none exist yet: binds were running); N46R2 / N46S2 bind results; kits on epyc7 / 8 / 10 for the collector
scan; the tile ID pin positions in the NK tile LEF; whether r2b is alive.
