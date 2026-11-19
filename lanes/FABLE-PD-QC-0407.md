# FABLE-PD-QC 2026-11-19 04:07 PST (0407): structural review of QC plan event N4.5

Reviewer: FABLE-PD-QC-N45 (Fable). Read-only: nothing launched, killed or patched. The N4.5 bind (S4Q9N45B) was in elaboration while I read.
Plan: epyc9 `/srv/opentallas-scratch2/claude/qc-plan-r3-n41p/n45/plan_n45_b.json` (sha b27995d32a4e), control = N4.4 (`event_tree/.../zz_s29_qc103_s4q9n44.json`).
Rules applied: FABLE-CLOSURE-STRATEGY 03:30 (a) tap = sink region W+H <= 300 um, no spill, cap 1,000 secondary; (b) no +cycle from distance alone.
Marking: **V** = I computed or opened it this round. **R** = reported by the named lane. **I** = inferred. Nothing here is a hold (r703).

## 0. Headline

1. **All 52 ft station rows are distance-only, and the distance is wrong (V).** Every one of the 52 slots is a corner slot (in and out on adjacent
   faces). `cbc_pass.ft_span` prices a corner slot at (w+h)/2. The real in-pin to out-pin length is 23 to 830 um, the hard-core span is 0 um on all
   52, and the N4.4 station count already covers the real length at 405 um per hop on all 52. All +1/+2/+4 on the 119 lanes can be dropped.
2. **The plan latency table does not carry the cycles (V).** `latency.lanes` is identical in N4.4 and N4.5 for all 119 lanes (pad 0 on every one),
   and no `fixed_cycles` changed. The 4 coll_core tx lanes also have pad 0, so "the far-end pad absorbs" does not hold; their table must grow.
3. **The three coll_core rx legs over 405 um should close (I, estimate).** They are 420 / 433 / 501 um; two are core-free. Estimated slack +70 to +165 ps.
   The open risk is the centroid aim, not the leg length.
4. **Two of the five tx station cycles come from a detour, not from the wire (V).** The path search treats SRAMs and fold slices as walls for wires.
5. **The tap rows set the cap only (V).** `tap_radius_um` stays 200 to 250 (W+H to 800 or more). 6 types have fewer taps than occupied 150-um tiles.
6. **The four copied tool files match rt 913e191a0b77 byte for byte (V); `rt/current` has since moved to 2d6e20435e34 (V).**

## 1. Do the ft +cycles survive leg classification? No (V)

Method: in pin = the upstream partition's out-bus window, carried through the abutment into the slot's own frame (partition origin + orient);
out pin = centre of `out_window_um`; core span = hard-core length on the better of the two L paths. Check: cbx `a22` has explicit `in_window_um`
and gives the same 98 um. Stations needed = ceil(L / 405), the cbc_pass convention.

| slot | family (types) | lanes | N4.4 -> N4.5 stations | CBC span (w+h)/2 | real pin-to-pin | core span | needed at 405 |
|---|---|---|---|---|---|---|---|
| a22 | cbx_q10 (4) | 48 | 1 -> 5 | 1,884 / 1,901 | 98 | 0 | 1 |
| cmd_free, fault, fltc, fltvc | coll_ftm (1) | 4 | 1 -> 3 | 1,128 | 27 | 0 | 1 |
| x_hc3_ctl | sle/slw_hc2 (6) | 12 | 1 -> 2 | 665 | 23 | 0 | 1 |
| x_su_l1_stm | sle/slw_su_c (3) | 12 | 2 -> 4 | 1,313 | 307 | 0 | 1 |
| x_st_a_fe | sle_su_l0 / su_l1 (4) | 12 | 2 -> 3 | 1,011 | 301 / 350 | 0 | 1 |
| x_fw_ctl_p2 | sle/slw_st_b v1, v2 (12) | 12 | 2 -> 3 | 981 | 531 | 0 | 2 |
| x_hc1_st_b | sle_ctl (7) | 12 | 3 -> 4 | 1,283 | 734 | 0 | 2 |
| x_fw_st_b | sle/slw_fe_v1 (5) | 6 | 2 -> 4 | 1,227 | 769 / 780 | 0 | 2 |
| x_st_a_fe | slw_fw_v2, v3 (3) | 3 | 2 -> 4 | 1,227 | 740 / 758 | 0 | 2 |
| x_st_a_fe | slw_fw_v1 (3) | 3 | 3 -> 4 | 1,227 | 830 | 0 | 3 |
| out_data_rd_wi | coll_ftc (1) | 1 | 2 -> 3 | 933 | 797 | 0 | 2 |

- 52 of 52 slots: N4.4 stations >= stations needed. 0 of 52 span a hard core. Four are 1-bit or 8-bit control slots with 23 to 27 um of wire.
- Tightest hops if nothing is added: coll_ftc 797 / 2 = 399 um, fe_v1 780 / 2 = 390 um, fw_v2 / v3 379 um. All core-free, so in the 550-um class.
- The CBC recount of 03:37 (epyc8 `cbc-rules-1119/runs/qc_n43_ft`, 25 slots, 85 lanes, a22 +3) uses the same (w+h)/2 span and only re-prices it
  at 550 um per hop. It marks every row `buffered`, `core_span_um 0`. It is also wrong, for the same reason.
- Cost carried by plan_n45_b for these rows (R, CBC summary): +26,276 flops, token rate down 0.05 % to 3.7 %.

## 2. Do the tap rows meet the region rule? Not encoded; 6 types short (V)

- The fold writes `clock.tap_max_sinks = 1000` on 129 types and nothing else. `tap_radius_um` stays 200 (coll_core 230, coll_ftc 250).
  The CBC run that produced the rows had thresholds `{hop 405, depth 13, tap_sinks 1000, reset_leaf 32}`: no region term.
- The `split` / `add_taps` part of the CBC tap rows is not folded (`n45_fold.py` applies `set` only). For the 126 density types the kit re-derives
  taps (R, fold comment; not verified by me). For explicit types it does not: the N4.4 G0 log prints
  `coll_ft__cla4a25d77 explicit tap clk_t3 1091/1000, clk_t4 1132/1000, clk_t5 1091/1000` (V). That is the spill form.
- Region test from the placed sink bins (`sink_bins_file`, 127 types): count the 150 x 150 um tiles that hold sinks and compare with the tap count.
  121 types have at least one tap per occupied tile. Short:

| type | taps | occupied 150-um tiles | sinks |
|---|---|---|---|
| coll_ucie | 20 | 32 | 3,727 |
| sle_fe_v3 | 21 | 32 | 12,390 |
| sle_su_l1__cl5ea486db | 36 | 46 | 16,149 |
| coll_core | 43 | 47 (97 with the cap) | 65,949 |
| coll_ftn | 12 | 14 | 3,616 |
| coll_ft__cl78c7b300 | 22 | 23 | 9,348 |

- coll_core: cap went 4,800 -> 1,000 with 43 planned taps for 65,949 sinks (five taps at 2,777 to 3,524). It needs about 66 taps by count alone.
  It is the pk_coll proof type, so read `OT_TAP_INSERTION` there first.

## 3. Will the coll_core legs over 405 um miss timing? Estimate: no (I)

Wire model from the lane evidence in the 03:30 strategy: buffered core-free legs close to 550 um (col_h9_r2, 30 of 30), which is about 1.27 ps/um
against a 700 ps wire budget; an unbuffered leg over a core fails near 400 um, about 4.4e-3 ps/um^2. Fixed part 70 ps (clk-to-q + setup), 60 ps
clock uncertainty, 833 ps period.

| bus | worst leg | hard core on the leg | wire delay | slack estimate |
|---|---|---|---|---|
| rec_rx_s1_i (chunks 6, 7) | 433 um | 0 | 550 ps | about +150 ps |
| rec_rx_s2_i (chunks 6, 7) | 420 um | 0 | 533 ps | about +165 ps |
| fltv_s_i (26 bits) | 501 um | 216 um of fold slice | 565 to 636 ps | +70 to +140 ps |
| rec_rx_s0_i | 222 um | 0 | 282 ps | about +420 ps |

- The fold slice LEF blocks M1 to M5 only (V), so the fltv leg can cross it on M6 / M7. The SRAMs block to M4.
- s1 / s2 stage points sit at x = 30 to 35 um and x = 225 to 245 um, core-free. Inter-stage legs are 225 to 433 um over the 9 chunks.
- Not shown by any of this: the first and last leg of each chain are measured to a centroid per 64-bit chunk. QC-COLL-CORE-1118 reports
  bin -> srr at up to 1,476 / 1,504 um on 297 bits (R, placed scan), and the strategy reports srr scattered over 700 to 1,100 um. If the reader
  bits of one chunk are themselves scattered, the last leg is longer than the table. I could not find the attempt_7 `geom.tsv` to measure it.
- fltv: the chain is 4 legs of 501 um, a 2,004 um path for 26 bits. That is a detour around the fold-slice wall, see 5.

## 4. Tool-file copy: skew risk (V)

- `event_tree/tools/die_plan/{bind,schema,reset_port_relays,relay_branch}.py` = rt 913e191a0b77, 4 of 4 identical.
- `rt/current` on epyc9 now resolves to 2d6e20435e34. Against it: `schema.py` differs (adds `place_regions`, `landing_relay_tx_stages`) and
  `relay_branch.py` differs; `bind.py` and `reset_port_relays.py` are the same.
- 30 other files of the event tree's `tools/die_plan` differ from 913e (check.py, gen_phys.py, kit_istations.py 75 lines, relay_depth.py,
  die_plan.schema.json, signoff.py), and cbc_pass / bank_reset_delta / tap_resolve are absent there. Import check of the 4 copied files against
  the event tree's other modules: 0 missing names (V, AST scan; static only).
- `run_cbc.sh`, `run_reset.sh`, `g0pre.sh` resolve `rt/current` at run time. The rows were made on one rt and PRE will run on another.
- `reset.bank_taps` is read by bind.py, schema.py and reset_port_relays.py only, in both rt versions. No kit-side reader exists, so no physical skew there.
- Consequence for the fixes below: a `place_regions` row fails the event tree's schema until schema.py is synced again.

## 5. Whole-die structural risks

- Die level: none from the 4,462 sites. coll_core has one instance and the sites are inside it. The only die-level changes are the ft stations of 1
  (to be dropped) and lane cycles.
- Inside coll_core (V): 29 hard cores cover 46 % of the outline. Eight fold slices form a wall at y 1,106 to 1,318 from x 9 to 596 with gaps of 4 and
  13 um, and a second row above it. The path search (`n45_coll.py`, 5-um grid) treats every core as a wall for wires, so:
  - rec_tx_s0: direct 620 um, planned path 1,044 um through the 13-um gap (x 393 to 406, 212 um long). 548 bits do not fit in 13 um of M5 + M7
    (about 470 tracks at 100 %). The router will go over the slice on M6 / M7 instead; the leg (413, 1105) -> (280, 1320) then spans 212 um of core.
  - io_collective__out_data: direct 607 um, planned 1,053 um. Its launch centroid (261.5, 1169.4) lies inside fold slice g_xf_1, so the launch
    flops are scattered around that core and the first leg (278 um) is not a real distance.
  - rec_tx_s2: direct 248 um, 108 um of it over an SRAM that blocks M4 and below. Planned path 447 um, 1 station.
- West channel: s1 and s2 chains (1,096 bits, 3 registers each) run at x = 30 to 35 um beside the SRAM columns. M5 / M7 over the SRAMs carry it.
- Site legality (V): 710 of 4,462 sites are inside a 4.32-um hard-core halo (`push` uses edge + 2 um) and 256 are at x <= 0.5 um on the
  partition edge. The kit legaliser will move them a few um; not a timing item. Many bits per coordinate is existing practice (cbf_q01: 10,584 on 206 points).

## 6. Latency / K consistency (V)

- 119 of 119 k_delta lanes: `latency.lanes[lane]` unchanged from N4.4 (example `c_W5_bf_00__a22`: cycles 11, stations 1, natural 11, pad 0,
  while the slot now has 5 stations). 0 `fixed_cycles` changed in `lanes[]`. None of the 119 is in a plan `latency_groups` entry.
- So the K change exists only in the bind: pass 1 is seeded with the N44BBR R8 table, is expected to fail R8_STALE, and the chain derives a new
  table. LATCHECK at the end of `chain_n45.sh` is the only check. The plan of record and the bound RTL will disagree on 119 `LAT_*` rows unless
  the pack regenerates the table.
- coll_core tx lanes: `coll_core__crec_tx_s0 / s1 / s2` are 21 / 21 / 21 with pad 0; `coll_core__out_data_rd_wi` is 15 with pad 0. The new
  stations make them 23 / 21 / 22 and 17 (18 with the coll_ftc slot row). Whether the three sectors must stay equal: not checked.
- No token run and no die GRT / crossing STA exists on this plan (strategy lever 4; V by absence).

## 7. Ranked fix list

| # | fix | evidence | owner |
|---|---|---|---|
| 1 | Revert the 52 ft slot `stations` to their N4.4 values (plan_n45_c); 0 cycles on 119 lanes, -26.3k flops | section 1 table | QC-PLAN-R3 |
| 2 | `cbc_pass.ft_span`: use in-pin to out-pin Manhattan (in pin from `in_window_um`, else the upstream bus window through the abutment); withdraw the 119-lane and the 85-lane row sets | section 1; cbx a22 98 um priced at 1,884 | CBC-RULES-1119 |
| 3 | Regenerate `latency.lanes` in the plan for every lane whose cycles change, and state the tx lane cycles (pad is 0); run LATCHECK on the final bind and a token run before publish | section 6 | QC-PLAN-R3 |
| 4 | coll_core tx: size stations on the direct path with fold slices crossed on M6 / M7: rec_tx_s2 0 stations, rec_tx_s0 1 (site about (275, 1320)), out_data 1; saves 3 lane-cycles | section 5 | QC-COLL-CORE-1118 (rows), QC-PLAN-R3 (fold) |
| 5 | coll_core: a placement region for `u_coll` out_data / qdata / srr beside their SRAMs before any further cycle (strategy lever 5); needs schema.py from rt 2d6e in the event tree | section 3, 5 | QC-COLL-CORE-1118 |
| 6 | Taps: write the region rule into the rows (`tap_radius_um` 200 -> region W+H 300, no spill); add taps on the 6 short types; fold `add_taps` for explicit types (coll_ft__cla4a25d77) | section 2 | CBC-RULES-1119 (rule), QC-PLAN-R3 (fold) |
| 7 | pk_coll: read `OT_TAP_INSERTION` and the placed rx end legs (bin -> stage 0, last stage -> srr bit) per chunk; add an lpad stage on fltv_s only if its 501-um leg fails at GRT | section 3 | QC-COLL-CORE-1118 |
| 8 | Pin rt by sha in `run_cbc.sh` / `run_reset.sh` / `g0pre.sh` and record it in the pack; next event syncs the whole `tools/die_plan`, not single files | section 4 | QC-PLAN-R3 |
| 9 | `n45_coll.py` `push`: use the core halo (4.32 um) and keep sites 2 um off the partition edge | section 5 | QC-COLL-CORE-1118 |

## 8. Stop list

- Do not publish or apply plan_n45_b with the 52 ft station rows. The running bind stays useful as proof of the coll_core, reset and tap rows.
- Do not take the 03:37 recount (85 lanes, a22 +3) in its place; it has the same span error.
- Do not add stations or cycles for the 420 / 433 / 501 um rx legs before pk_coll GRT.
- Do not size a cycle from the macro-free path length in coll_core; SRAMs block to M4 and fold slices to M5.
- Do not report the cap-1,000 rows as meeting the tap rule; do not lower a cap on an explicit-tap type without adding its taps.
- Do not rely on "the far-end pad absorbs" for the coll_core tx lanes; their pad is 0.
- Do not copy more single tool files into the event tree, and do not run row generators through the `rt/current` link.

## 9. Not checked

- The N4.5 bind result, G0 and PRE on N4.5 (not finished when I read; `g0_n45`, `pre_n45` absent).
- Placed positions in coll_core (attempt_7 `geom.tsv` not found): end-leg scatter per chunk, and whether the kit re-derives density taps under the new cap.
- The R8 table after derive, automatic replica groups, and whether tx sectors s0 / s1 / s2 need equal latency.
- Wire delays are estimates from lane-reported closure points, not from an RC extraction.
- In-pin positions assume abutted partitions (upstream out window = in pin); verified on cbx a22 only.
