# FABLE-PD-QC-2300 2026-11-19 23:00 PST: QC events N46R3 / N46T / N46U3, coll_core, tt_ctlm, die hold

Reviewer: FABLE-PD-QC-2300 (Fable). Read-only: no job launched, stopped or patched; no plan edited. Technical PD only.
Marking: **V** = I opened the plan, report, log or code this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
Gate: route DRC 0, TT >= -42, hold >= 0, bind + LATCHECK, hops <= 405 um. Nothing below is a new gate, hold or freeze.
Sources (V), epyc9 `/srv/opentallas-scratch2/claude/qc-plan-r3-n41p/` unless named: `n46/plan_n46_r3.json` (bdc8b8995309),
`n46/plan_n46_t3.json` (d5a895df40f5, the plan under tag S4Q9N46T4), `n46u3/{plan_n46_u3,sidecar_n46u3,n46u3_report}.json`
(befd0321737b), `event_tree_t2/tools/die_plan/{kit_istations,check}.py`, `rt/current/tools/die_plan/{macro_sites,qc_add_macro_sites}.py`,
`bind/bind_s29q103S4Q9N46T3BR.log`, `pkits/pk46_{s2b,cbf1,e6}`; epyc9 `fable-fix-qc-collcore/opus/pkits/pkw2b_coll`;
epyc7 `qc-ttctlm-1119/r2a`, `qc-ttctlm-1119-r1/{r1a,r1b}`; epyc10 `die-level-1119/runs/qwen_compute/rv1/sta_ca/die_sta_related.json`,
`die-level-1119/qc_n46e/chain/qc/n46ct_e/reg/{kitwin,kitoffs}.json`.

## 0. Headline

| item | state 23:00 PST (V) | verdict |
|---|---|---|
| N46R3 | applied 22:49, live tree n46_s2 | sound; my checks agree |
| N46T (d5a895df40f5, tag T4 binding) | bind running | cycles and latency sound; **59 station rows on 19 types will stop kit gen**, 899 exact bit sites sit in hard cores |
| N46U3 fall fold (befd0321737b) | bind running | latency table sound; **3 slice type buses still have mixed ring depth** (the U2 TYPE_SPLIT types); proof clock is still n46ct_e |
| macro-site generator (main 1ef667d1811f) | used on 2 st_b types | its obstacle list has no hard cores, straps, tap sites or relay sites |
| coll_core pkw2b | post-CTS TT -558.7 | the worst class is an SRAM read that cannot fit one cycle; no wall or rec_tx row touches it |
| tt_ctlm r1b | post-CTS TT -106.1, tns -417 | depth class is closed (-17.6); two ROM read ends remain; the form is not enough alone |
| QC die hold -355 | bound | the real class is tap spread inside one instance: 30 % of kit clock ports need more than the 57 ps window |

1. **N46T will bind and then fail in kit gen (V, static run of the event tree's own `kit_istations.exact_banks` on the plan; no kit run).**
   33 rows carry `bit_sites_um` and `bit_route` together; 26 rows are `per_bit` without `leaf_um`. Bind and LATCHECK do not read either.
2. **N46U3 keeps the cause of the U2 TYPE_SPLIT (V plan, I outcome).** `fold_classes` equalises the shift. The split is in ring depth:
   18 destination type buses have instances at depth 4 and 8; N46R3 has none.
3. **coll_core (V path).** SRAM clock-to-out 434 ps + 8 logic cells 278 ps leave 49 ps for wire. The path carries 657 ps of buffers.
4. **tt_ctlm (V paths).** R1 + un-keep took the flop-to-flop class from -180.6 to -17.6. The -106.1 and -50.7 ends start at two ROMs
   whose clock-to-out is 591 and 520 ps.
5. **Die hold (V).** The -355.17 pair is slw_fe_v2 against itself with 42.8 ps of die clock difference. The die-owned number is the
   per-port window: p50 43, p90 92, max 283 ps over 15,964 ports.

## 1. (A) Plan events

### 1.1 N46R3 (applied): checks on bdc8b8995309 (V, my scripts)
| check | N46Q e6 | N46R3 |
|---|---|---|
| hard-core box overlaps | 0 | 0 |
| strap sites inside a hard core or SRAM halo | 70 | 0 |
| clock / reset tap sites in or within 4.32 um of an SRAM | 0 | 0 |
| `cycles = stations + boundary + fixed + clock_landing + pad` | 1921 / 1921 | 1921 / 1921 |
| latency groups equal | 14 / 14 | 14 / 14 |
| nominal hops over 405 um | 104 of 4,460 | 97 of 4,508 |
| `per_bit` station rows without `leaf_um` | 0 | 0 of 1,062 |

Sound. Two notes on its proofs:
- pk46_cbf1 (sibling) after TT repair: -60.37 -> **+28.46**, 1,451 cells (V, `tt_setup_repair.log`).
- pk46_s2b was resumed on its own CTS DB, which is the bind with the stale collector names: -2002.87 -> -1761.76 after repair (V).
  It measures the old plan. The cbf_q00_s2 proof is its wave kit on n46_s2.

### 1.2 N46T (plan d5a895df40f5): what passes (V)
| check | result |
|---|---|
| hard-core overlaps | 0 (the 22:14 refusal, 110 KITFIT-OVERLAP, is cleared by taking generator sites on 2 st_b types only) |
| latency formula / groups | 1921 / 1921; 14 / 14 |
| lane cycles | 21,792 -> 22,009 (+217): 82 lanes +1, 45 +2, 10 +3, 3 +5 |
| station count change against latency change | 136 lanes, 0 mismatches; 4 lanes take +1 pad with no station (sl_E1/E2/E3/E5_su_l0__x_su_l0_ctl, group with su_l1_ctl) |
| su-family taps | 28 rows on 7 types equal the handoff means (l0 397.07 / 327.17 ... l7 414.04 / 333.91) |
| nominal hops over 405 um | 124 of 4,692; the 27 new ones are rows with a relay bin at 1/3 (st_a rs_s0 / rs_s1, fe arm / arv), which the nominal chain does not show |

### 1.3 N46T findings
**F1. 59 rows on 19 types (23 instances) stop kit gen (V).**
- `kit_istations.py` line 1676 calls `exact_banks(e, W)` on every bus station row. Line 254: a row with `bit_sites_um` and `bit_route`
  raises "exact internal bank sites cannot also request bit_route". I ran that function on every row of both plans: N46R3 0 errors,
  N46T 33 errors (rs_s0, rs_s1, x_ctl_o on the 11 st_a types; SUST v3 "exact per-bit form").
- With `bit_route` removed the same 33 rows raise "each bit_sites_um stage must contain width+1 payload/epoch sites" (514 sites for
  width 514, 268 for 268): the epoch site is missing.
- Line 1809: a `per_bit` row needs `leaf_um`, else SystemExit. 26 more rows have none: x_fe_o on the 11 st_a types, x_st_b_o x2 on
  slw_st_a_v2__cl9f076a5c, sle_fw_v1 x2 x_st_a_o / x_st_b_o, slw_fw_v1 x2 and slw_fw_v2__cl8537f156 flt_wo, sle_fe_v1 x2 and
  slw_fe_v2__cle312294d arm / arv. All 1,062 `per_bit` rows of N46R3 carry `leaf_um`.
- Types: 11 st_a, 2 sle_fe_v1, 1 slw_fe_v2, 2 sle_fw_v1, 2 slw_fw_v1, 1 slw_fw_v2.

**F2. 899 exact bit sites lie inside hard cores (V).**
| bus | where | sites | depth inside the box (um) | types |
|---|---|---|---|---|
| rs_s0 | region macro u_r0 | 8 to 22 per type | 0.9 to 13.0 | 11 st_a |
| rs_s0 | region macro u_r1 | 20 to 40 per type | 1.7 to 17.3 | 11 st_a |
| rs_s1 | btab SRAM g_btb[1] | 23 per type | 0.9 to 17.3 | 6 (sle_st_a_v1 x3, slw_st_a_v1 x3) |
| rs_s1 | btab SRAM g_btb[2] / [3] | 36 to 43 per type | 0.9 to 18.4 | 4 of those 6 |
Total 610 in region macros, 289 in SRAMs. The N46T footprint check (`n46t_post.py`) reads `regs_um` and `relay_sites`, not
`bit_sites_um`. Nominal `regs_um` inside a core are not a finding: N46R3 already has 18 on `per_bit` rows, where the reg is a centroid.

**F3. Clock inputs of the 23 types with moved macros are the N46R3 ones (V).**
- 2 to 20 macros moved per type, median move 276 to 924 um, max 1,028 um (sle_st_b_v2__clfde1249e).
- `reset.consumer_sites_um`, `clock.sink_bins_file`, `clock.reset_tree_anchor` and the landing start stages are byte-equal to N46R3.
- 14 tap sites now sit inside an SRAM (5) or within 4.32 um (9) on 11 types; N46R3 has 0. Inside: slw_st_b_v2__pva66d0f22 x2
  clk_t49 / clk_t82, sle_st_a_v1__cl989804f6__cled3c1d7b clk_t84.
- I: the sink bins are flop density measured with the macros at the old sites. The st_b regions (4 x about 33k cells) follow their
  SRAMs, so the tap load and radius in the first kits will not match the plan.

**F4. Generator sites on slw_st_b_v1__cle6023ec2 land on the count straps (V).** The 20 SRAMs sit in x 207 to 455, y 588 to 829 around
the type centre (311, 670), which is also `clock.tap_um` and the strap site. 1 strap site is inside an SRAM and 9 are within 5.4 um
(5 of 9 straps). That is the class N46R3 just removed. The other 10 st_b types keep v3 rows (two clusters), so the family carries two forms.

**F5. slw_su_l1 x2 stay on 392.5 ps lane taps (V).** The signed means of the same lane cores are 401.18 to 426.38. I: those lane pins
get the clock 9 to 34 ps later than planned. Known and deferred by SONNET-FIX-QC; listed so the first slw_su_l1 kit is read with it.

### 1.4 Macro-site generator on main 1ef667d1811f (V, code)
- `qc_add_macro_sites.obs()` reserves landing bands, clock `taps[].xy`, `tap_um`, collector relays, station regs and bit sites. It does
  not reserve `hard_cores[]` boxes, `count_straps` sites, `reset.consumer_sites_um`, `relay_sites` or landing start stages.
- `macro_sites.gap()` is 0 when the macro overlaps its partner box, so `target()` for a btab bank with partner u_r0 is a point on u_r0.
  That produced the 10 KITFIT-OVERLAP (R, QC-PLAN-R3 22:49) and the bank over the u_lis2 relay sites (R).
- st_b partner = mean `leaf_um` of the core-capture stations. On slw_st_b_v1__cle6023ec2 that is the type centre for all four regions.
  QC-PADLEG measured that this anchor is not where the consumers sit (R, 19:12).

### 1.5 N46U3 fall fold (plan befd0321737b, sidecar_n46u3) (V)
| check | result |
|---|---|
| latency formula / groups | 1921 / 1921; 14 / 14 |
| lane `clock_landing` = sum of its ports' `sched_lat` | all lanes, 2,525 ports |
| lane cycles | 21,792 -> 20,759 (-1,033) |
| depth changes | 141 ports 4 -> 8, 40 ports 8 -> 4 |
| destination (type, bus) with instances at different depth | **18** (N46R3 sidecar: 0) |
| margins | min lo 108.1, hi 111.4 against need 100; 14 ports lo under 120, 3 hi under 120; 131 lo and 33 hi under 150 |
| proof | `sta_interval.plan` = plan_n46_ct 95ff3208, proof n46ct_e |

- The 18 include `sle_ctl__cl67434795 x_su_l1_i` (sl_W2 and sl_W4 depth 8, sl_W3 depth 4), `slw_su_c__cl92142dac x_su_l1_ctl_i`
  (W1, W3 depth 8; W2, W4, W5 depth 4) and `sle_su_c x_su_l1_ctl_i` (E0 depth 8, the rest 4). The first two are the U2 TYPE_SPLIT
  types. The other 15 are cb* buses (cbf_q00 na_i00, cbf_q01 nb_i12, cbf_q11 x4, cbn_q00 bc_i10, cbn_q01 x2, cbx_q10 x6); U2 named
  no cb type, so I read those as tolerated (not checked).
- x_su_l0_ctl pads on sl_W0..W5: 30 / 30 / 31 / 30 / 31 / 28 (N46R3 29 / 29 / 29 / 29 / 29 / 30). U2's G0 error was "sl_W3_su_l0__x_su_l0_ctl:
  pad 30 fits no site"; U3 still has 30 there.
- The worst margins sit 8 to 11 ps above need on a clock built from an older plan. Per-port clock offsets differ by tens of ps
  between QC tree builds (V, `kitoffs.json`), so a rebuilt clock will put some ports under 100.

### 1.6 Fix, ranked (P)
| # | fix | owner | evidence / check |
|---|---|---|---|
| 1 | Rewrite the 33 exact rows in one legal form before N46T is applied: exact bank (no `bit_route`, width + 1 sites, every site outside each `hard_cores[]` box + halo) or `per_bit` with `leaf_um` and no sites. Add `leaf_um` to the 26 `per_bit` rows. The apply binds first, so no separate bind is lost. | QC-SUST-MACRO-1119 (st_a rows), QC-PLAN-R3 (PADLEG rows, compose) | `exact_banks` on every row returns; site scan 0 |
| 2 | Compose check: run `kit_istations.exact_banks` and the `per_bit` key test on every row, and the footprint test on `bit_sites_um`. Estimator in the compose step, not a gate. | QC-PLAN-R3 | would have shown F1 and F2 in seconds |
| 3 | Fold: class floor on depth as well as shift (every instance of a slice type bus takes the largest depth of its class). Keep x_su_l0_ctl pad at 29 or add its pad site. | QC-PLAN-R3; KV-CROSSING for the main copy | 18 -> 15 mixed classes, 0 on sl types |
| 4 | Fold proof: rebuild the die clock on the N46T plan, then re-time TT + FF. Where +1 cycle buys it, take K with both margins >= 150 (cycles are pre-approved). | QC-PLAN-R3 | 17 ports under 120 today |
| 5 | Generator: `obs()` adds hard cores + halo, strap sites, tap sites, relay sites; a partner gap of 0 by overlap is refused; inventory SRAMs nested in a hard core are skipped; st_b partner = placed g_pin flop centroid per region from the proof kit. | QC-SUST-MACRO-1119 | F4, 1.4 |
| 6 | After the N46T bind: confirm 0 tap sites in or beside an SRAM in the bound tree. In the first st kits read `OT_TAP_BALANCE` spread and empty taps; re-bin `sink_bins` for the 23 types from those placements in the next event. | QC-PLAN-R3 | F3 |
| 7 | Proof kits on N46T: one st_a (rows), slw_st_b_v1__cle6023ec2 (generator) and one v3-row st_b side by side, one fw, one sle_ctl, to GRT TT. | QC-SUST-MACRO-1119, QC-PLAN-R3 | r712 |

## 2. (B) coll_core: what closes the gap after pkw2b

### 2.1 Evidence
- V, `pkw2b_coll/gen/coll_core/run/reports/asap7/dp_coll_core/base/4_cts_post_hook.rpt`, worst setup path (-607.23 before TT repair;
  repair added 284 cells -> -558.72, tns -341.5k; pk45 -997.9, tns -692k):

| segment | ps |
|---|---|
| launch clock at `u_coll.g_sring[4].u_m/clk` (ot_sram_1r1w_512x128_m4_r2c2) | 251.37 |
| SRAM clk -> rd_out[36] | 433.59 |
| 8 logic cells (INV, NOR2, OR2, OA22, OA211, INV, OA211, AO21) | 278.14 |
| 13 buffers | 656.63 |
| required at `u_coll.out_data[77]` (capture clock 189.81, setup 10.25) | 1012.56 |

- Budget: 1012.56 - 251.37 - 433.59 - 278.14 = **49.5 ps** for all wire. The clock is 61.6 ps against the path (launch 251.4, capture 189.8).
- R (OPUS-FIX-QC-COLLCORE, pk45 census): g_sring rd_out -> out_data 512 ends, worst -524, direct 140 um; g_sring rd_out -> g_xf src
  949 ends, -475, direct 493 um. The lane filed both as congestion detour for the wall form.
- V: with the wall form the same class is still the worst path of the kit. So the wall did not close it.
- V, same log: `OT_TAP_BALANCE` tap mean insertion 168 to 329 ps (target 250), 5 of 33 core clock pins outside +/- 20, 2 empty taps.
- V, `pregrt_ff_hold.log`: 43,261 hold endpoints, 8,826 hold buffers; worst hold -177.0 on `u_coll.ur_rec[]` -> `u_d5_..._ur_rec.r[][]`
  (launch clock 143, capture 341). Cell census 335,598 before those buffers.

### 2.2 Root cause
A single-cycle SRAM read: access time is 52 % of the period and the read mux takes another 33 %. Even at 140 um direct the path needs
under about 90 ps of wire to meet -42. It is a latency item, not a placement item. pkw3's rec_tx stations serve the g_wd -> g_sxo ->
rec_tx distance classes (1,003 ends) and do not touch it.

### 2.3 Fix, ranked (P). Owner OPUS-FIX-QC-COLLCORE; latency row to QC-PLAN-R3
1. **Registered SRAM read.** One register bank after the sring read mux, sited at the SRAM column (rd_out pin edge), +1 cycle on
   io_collective__out_data and on the g_xf source path. Expected: SRAM + mux = 712 of 761 ps with the register beside the mux; the next
   cycle carries the 140 um (out_data) and 493 um (g_xf, one station) legs. Pre-approved cycles.
2. **Keep pkw3** for the rec_tx distance classes. Read it by class, not by WNS: its WNS will still be the SRAM read.
3. **Clock on the read path.** After 1, bring the out_data capture taps to target (they are 60 ps early). Do not early-tap the SRAMs:
   g_wd -> g_sring wd_in is itself negative (-330 / -270 on pk45, R).
4. **Hold.** The `u_d5` pad-delay stages are a zero-logic cross-tap chain (198 ps between launch and capture clocks). Group consecutive
   stages on one tap (the KV form A) instead of 8,826 buffers at 336k cells.
Pass mark for the next kit: the sring -> out_data and sring -> g_xf classes at or above -42 at GRT TT; GRT round-5 marks as set.

## 3. (C) tt_ctlm

### 3.1 Evidence (V, `tt_setup_repair.log`, `tt_setup_keep.log`, `4_cts_post_hook.rpt` of each kit; placement RC, TT)
| form | cycles | post-CTS before -> after TT repair | tns | flop -> flop class (cells) | calrom read | op ROM read |
|---|---|---|---|---|---|---|
| N46C wave kit (R, SONNET-FIX-QC) | 0 | -196.2 | | 24 levels median | | |
| r2a un-keep + u_75259 split | 0 | -180.58 -> -148.34 | -44,163 | -180.6 (28) | not in the top 10 | not in the top 10 |
| r1a R1 start register | +1 | -143.66 -> -128.48 | -347 | -42.3 (25) | -143.7 (13) | -128.2 (19) |
| r1b R1 + un-keep | +1 | -106.09 (repair to -95.66 raised tns, DB restored) | -417 | **-17.6** (24) | **-106.1** (9) | **-50.7** (12) |

r1b worst paths:
- `u_gi.u_cal.g_calrom.u_rom.m1` (ot_rom_4096x266_m8) clk -> rd_out[249] **591.21 ps**; 5 logic cells 206.06; 2 buffers 123.53; launch
  260.01, capture 244.86; required 1074.75. Without the buffers the path is +17.4.
- `u_gi.g_op.u_leaf.g_op.u_rom` (ot_rom_4096x72_m8) clk -> rd_out[49] **520.04 ps**; 10 cells 334.86, no long wire; launch 255.32,
  capture 227.65; required 1059.58.
- `u_hr` -> `u_hr` -25.6. Each ROM has its own clock tap (clk_t18 260 ps, clk_t30 255 ps; `OT_TAP_CORE` target 250).

### 3.2 Root cause
Two causes, one closed.
1. Logic depth from the start decode under per-gate bmath mapping (R, QC-TTCTLM). R1 moves the start one edge; un-keep lets abc
   restructure. Together they bring the class inside the gate at CTS. Each alone does not (-180.6, -42.3).
2. ROM read in one cycle. ROM access is 71 % and 62 % of the period; the logic after it needs 206 and 335 ps of the 224 and 284 ps left.
   No retime of the start decode reaches these paths.

### 3.3 Is the form enough?
No. r1b is the right base and should be adopted, but it leaves two ROM read ends at -106 / -51 at CTS. It needs one more row.

### 3.4 Fix, ranked (P). Owner QC-TTCTLM-1119; latency row to QC-PLAN-R3. Run 1 and 2 in parallel
1. **Register the calrom and op ROM read data** (+1 cycle on each read; same frontend mechanism as the STARTREG / CALREG map). Robust
   at GRT. LEC as for R1.
2. **Early tap on the three ROM taps** (calrom m0 / m1, op ROM): about 110 ps and 60 ps earlier than the 250 target. 3 of 63 kit clock
   ports, ledgered in lanes/CLOCK-RESIDUAL.md (12.8 d2). Before writing the row, read the ROM address setup slack on the r1b DB: the
   10 worst clock-group paths contain no ROM endpoint, which is not a number.
3. Read r1b at GRT TT before sizing either row; the calrom path has 123 ps of buffers that GRT may move.
4. Keep r1a and r2a as controls only; relaunch neither.

## 4. (D) Die-level hold on QC

### 4.1 What -355 is made of (V, `rv1/sta_ca/die_sta_related.json`, FF intra)
- Worst pair: launch `t_sl_W1_fe__clk_t80`, capture `t_sl_W1_fe__clk_t31`, both models `kit:slw_fe_v2__cle312294d`, die clock
  difference **42.81 ps**, CPPR 0. The other 312 ps is that type's insertion range charged to a pair inside one instance, plus hold
  and uncertainty. TT worst (-416.56) is the same type on sl_W3_fe with 49.86 ps.
- 471,668 measured pairs, 5,441,104 unmeasured; the tool times every tap pair of a partition, connected or not.
- So -355 says nothing about the die tree. The per-port extraction replaces the range with per-port values and the number moves to
  the class below.

### 4.2 The real class (V, `kitwin.json` = per kit clock port, worst late - early - CPPR over regions and corners; `kitoffs.json`)
| window a port needs | ports of 15,964 |
|---|---|
| <= 10 ps (plan `tap_window.window_ps`) | 1,311 (8 %) |
| <= 57 ps (what QC kits carry today: tt_ctlm 56.9, coll_core 57.1) | 11,103 (70 %) |
| over 100 ps | 1,318 |
| over 150 ps | 512 |
| p50 / p90 / max | 43 / 92 / 283 |

| family (types) | port window p50 / p90 / max (ps) | non-core tap offsets in one type, FF (ps) |
|---|---|---|
| cbn_q00 (3) | 75 / 223 / 283 | -155 .. +101 |
| cbn_q01 (3) | 50 / 139 / 273 | -215 .. +82 |
| cbx_q10 (4) | 160 / 192 / 259 | -106 .. +97 |
| cbn_q11 (2) | 117 / 174 / 210 | -90 .. +124 |
| sle_su_l0 (2) | 110 / 143 / 200 | |
| cbf_q00 (2) | 154 / 165 / 182 | -15 .. +137 |
| hc1 / hc2 (11) | 48-56 / 101-116 / 155-168 | -97 .. +54 |
| st_a, sle_ctl, coll_core | 45-52 / 70-82 / 120-137 | about 100 wide |
| fw, stm, fe, tt_ctlm, coll_ft* | 12-28 / 20-44 / 31-57 | under 60 wide |

- Same file, `kit_contract_hold`: 252,203 of 5,912,772 tap pairs exceed the window, in 253 of 377 partitions: all 168 cb tiles,
  sl_ctl / hc0 / st_a / su_c / su_l0 / su_l1 (12 each), sl_sc 7, 4 coll, 1 fe. Worst 223.93 ps (`c_W5_bn_01` clk_t48 -> clk_t46).
- The proof has `clock_ocv none`: the spread is nominal skew between sub-trees that feed one instance, not derate.
- Core taps of the a0c tile sit 320 to 628 ps early against a plan value of 483 / 568 (kitoffs clk_c*; R, DIE-CORETAP: 1,081 of 1,461 short).
- In the kit the class appears as zero-logic chains across taps: coll_core `ur_rec` -> `u_d5` pad-delay stage, clocks 198 ps apart (V, 2.1).

### 4.3 Root cause
The region tree balances each region to one target. The taps of one type instance hang on different sub-trees, so an instance sees
100 to 280 ps between its own taps on the cb tiles, hc1 / hc2 and su_l0, while its kit was closed against 10 to 57 ps.

### 4.4 Fix, ranked (P)
1. **Report the port-window table as the QC die hold number** until per-port views land; drop -355 from status lines. Owner
   DIE-LEVEL-CHECK-1119. It already exists in every chain run.
2. **Tree: per-pin sink offsets inside an instance**, first on the cb tile types and hc1 / hc2 / su_l0 (the families over 150). Target:
   every port <= 57 ps. It is nominal skew, so offsets can remove it; S81 cw7 is the same form and reads first. Owner QC-PLAN-R3 clock
   with DIE-CORETAP-1119.
3. **Type side for the tail**: ports left between 57 and about 100 ps take their own `tap_window.per_port_ps` from `kitwin.json`; the kit
   repairs only connected short pairs. Measured cost at 57 ps on coll_core: 8,826 buffers for 43,261 endpoints (2.6 % of cells).
4. **Zero-logic chains by construction**: consecutive pad-delay and relay stages share a tap (KV form A) or take a lockup latch.
   PRECHECK-1119 counts stage k -> k+1 cross-tap pairs per placed QC kit (estimator).
5. **Pair only connected pins** in `die_sta_related` (bind net graph), as already found on KV. Owner DIE-LEVEL-CHECK-1119.
6. Core-tap rows for a0c stay with DIE-CORETAP-1119; they are a separate class from 2.

## 5. Stop list
1. Do not apply N46T with the 33 two-form rows or the 26 `per_bit` rows without `leaf_um`. No st_a, fw or fe kit on it until they are fixed.
2. No exact bit site inside a `hard_cores[]` box or SRAM halo. No footprint verdict from `regs_um` and `relay_sites` alone.
3. No generator sites on a further type until `obs()` holds hard cores, straps and tap sites. No st_a use of the generator.
4. Do not read the pk46_s2b resume (-1762): it is the old bind. Stop quoting -2003 / -1762 for cbf_q00_s2.
5. No N46U re-fold that equalises shift only. Do not call the fold proven on n46ct_e. No fold with margins under 120 where a cycle buys more.
6. No further coll_core wall or site round for the sring read classes. No coll_core verdict from WNS alone. No early tap on the sring SRAMs.
7. No tt_ctlm relaunch of r1a, r2a or r2b. No abc delay-target sweep. No station or core-move row for the ROM read ends.
8. No die hold verdict or tree change from -355 / -416. No QC status line that quotes them without "bound".
9. No hold buffers as the first answer on cross-tap pad-delay chains.

## 6. Not checked
- No kit was run through `kit_istations` for F1: the result is the function called on the plan rows plus the code path read.
- The N46T4 and N46U3 bind and G0 results (running at 23:00); whether the bind re-solves tap sites (F3).
- Whether ring depth may differ per instance on cb types; I only know U2 raised no cb error.
- coll_core class census on pkw2b (the report holds 5 paths per group); pkw3 (in CTS). The placed distance of sring -> out_data in pkw2b.
- ROM address slack on tt_ctlm r1b; any GRT number for r1a / r1b / r2a.
- The 79-type per-port extraction; `kitwin.json` is from the n46ct_e clock on plan_n46_ct, not N46R3.
- PADLEG section 3 bin sites against each bit's real consumer; the 4 stm guides (held); renders of any of the three plans.
- failure_breakdown 22:53: QC 32 / 130 signed, 98 running, no technical class listed.
