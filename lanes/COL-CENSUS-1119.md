# COL-CENSUS-1119: S81 col structural census (11-19, Opus)

OWNER directive 11-19: fix the structural layout problems in the S81 col types now; no col structural class without a fix.
Base plan for every row: S81-GEOM-OPUS `plan_h3_d8i.json` f2ec5ffc3bda (D8h h3 + D8i 114 rows). 216 col types, 12 families.

## Evidence used

- 5,800 col attempt dirs on intel1/epyc2/epyc7/epyc8/epyc9/epyc10/intel2. Most old run dirs are cleaned, so the per-path reads come from the 70 kits with a report left: the 3fa87b84b18 (D8g plan_h2_2249) wave CTS/GRT reports (`4_cts_post_hook.rpt`, `5_global_route.rpt`) and the routed `6_finish.rpt` + `signoff.json`.
- Lane posts 11-15..11-19: S81-GEOM-OPUS, FABLE-FIX-S81-COL(H9R1), S81-TYPES-R2/R3, S81-COL-FLOW-1118, FABLE-CLOSURE-STRATEGY, COL-H10-1119, S81-CLOCK-WINDOW-1119.
- Reference (works): col_h9_r2 signed x2 (rtx-pro ~/signed-export-1114/s81): `cl774acf45__pv11b6518d__ax` and `clce45cab5__pv7a260fc0__pg3hei_1117` (DRC 0, TT -39.22, internal FF 0). Best wave kit pvea45273b: routed TT -44.75 (1 path, c12_6 -> s12), FF -0.54 (1 end), DRC 0.
- D8h (h3) is applied as event b4bb6a8b1e9, but every col wave row on it is `WAIT-BIND: kit_topology refused this bind` (18:16). Today only private builds run col types on h3/D8i.

## Classes

| Class | What it is (worst ends seen) |
|---|---|
| HOP | One long last hop, relay or stage -> hard-core input pin, over 405 um placed (700-960 ps wire, slew 2-3 ns). h10_r0_p1 xb_3/xa_3 -> t3 -481/-469 CTS; h10_r0_p4 cc_1 -> s0 -537 CTS; h9_r0 p1/p3/p5 xd s0_lc -> s0 -347..-351, t0 -> cf -331..-335 CTS, p1 cf -> t0 -227 GRT; p6 xa_1 -> t1 -133 GRT; h10_r1 flt_n24_n23 -> n23 -406..-442, lpl_8_r -> n24 -355..-390; h9_r1 lpl_9_r -> t3_payload -310..-352 GRT |
| BANK-OUT | hw ROM `pval` (falling edge, 620 ps clk->q, half cycle) -> `dsfd_qbank_N.e_r0`. p6 e0_u_w -> bn0 -30..-45 GRT; h10_r2 e13_u_w -> bn13 -96 GRT; h9_r2 e11_u_w -> bn11 -46.9 routed before the D8f move + lead. Plan distance (LEF pins): r0 bn0 222 um, h10_r0_p1 bn0 248, h10_r0_p4 bn2 283 / bn4 214, h9_r1 bn6 266 / bn7 227, h10_r1 bn8 348, h10_r2 bn12 266 / bn13 227 |
| BANK-IN | `dsfd_qbank_S.o_x` -> hw ROM `xs_q` / `cfg_d` (half cycle). h9_r2 bs12 -> e12_u_w -18 CTS; h9_r0_p2 bs1 -> e1_u_w -78.7 CTS (557 ends, S81-TYPES-R2 11-16). Plan distance 241-306 um in every family |
| RDLOOP | cfg ROM fixed-latency read loop c*_k -> s*.q (no stage allowed). h9_r2 c12_6 -> s12 -44.75 routed (the only end); h9_r1 proof worst u_s5/q6 at -41.49 |
| PIN | Station / pad siting: h9_r2 lpad frame_int_i0 r -> r -83 GRT; h10_r0_p4 bin_x_i0 -> lpad_x_i0.q 528-531 um placed; h10_r2 t7.so -> ist_o0 rank 0; h9_r1 frame stations on the N edge |
| CONG | GRT overflow: h9_r1 N strip x701-758; h9_r0_p2 two capacity-0 gcells at lpad_xo_i0.q (77,186 M8/M6 layer-assignment overflow, D8e proof); h9_r0_p3 ft0_i landing band (157k on the B-era plan, no current GRT); h10_r1 lpad_frame_int_i1 strip. h9_r2 and p6: overflow 0 |
| RST | Reset recovery across relays: h9_r0_p5 xo0_0 g_rsreg.rq -> xo2_1 / xo3_1 o[*] -196 CTS |
| CLKWIN | cw6 per-port windows up to 121 ps inside the type, the 39 S81 TT start-skew crossings, core-tap early insertion |
| PORT-HOLD | Input-port-start FF hold (frame_int_i0 / x_i0 / xo_i0 / ft*_i -> u_bin): -55..-110 at GRT, h10_r2 -297. Parent-owned (R-MINIMAL advisory, NEEDS_PARENT); GRT repair excludes ports since 1fd8080739 |
| INT-HOLD | Pre-repair CTS hold mins (cf_rs reset chain -> rr/nf/lpl, lpl_*_r wr -> rc, cland ring) -20..-178; GRT hold repair closes them (routed h9_r2 FF -0.54, 1 end) |
| FLOW | GRT post max-wire repair goes flat 1,800 s (h9_r2 FAIL_route, h9_r1); kit_topology WAIT-BIND on every D8h col wave row |

## Family x class x owner x status

Status: FIXED-PLAN = the row is in plan_h3_d8i (D8h/D8i), proof build running; CC1 = my CC-BANK-1 row, private build queued; OPEN-ROW = uncovered, my row follows the first CC1 CTS read; ADVISORY = not a type gate; FLOW = not structural.

| Family (types) | HOP | BANK-OUT | BANK-IN | RDLOOP | PIN | CONG | RST | CLKWIN | PORT-HOLD / INT-HOLD / FLOW |
|---|---|---|---|---|---|---|---|---|---|
| col_h9_r2 (60, 2 signed) | FIXED-PLAN D8h RLYBR copies (S81-DIE-R3) | bn11/bn12 FIXED-PLAN D8f move + lead -45; bn10/bn14 hw 84-88 um, none needed | OPEN-ROW CC-BANK-2 (COL-CENSUS) | OPEN near miss -2.75 ps, 1 end: ECO allowed, or c12_6 move CC-RDLOOP-1 (COL-CENSUS) | lpad i0: FIXED-PLAN D8h RLYBR-1 trunk aim | none (overflow 0) | - | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW (OT_MAXWIRE_POST_SKIP ask, S81-COL-FLOW-1118 + WAVE-FLOW-R2) |
| col_h9_r1 (60) | FIXED-PLAN D8h H9R1-I1-TRUNK-1 (FABLE-FIX-S81-COLH9R1, proof TT -41.49) | CC1: bn6 266->123, bn7 227->136 um | OPEN-ROW CC-BANK-2 | u_s5 q6 near miss (proof -41.49): read on D8i build | FIXED-PLAN D8i I0 +1 / H9R1-FRAME-1 | FIXED-PLAN D8i STRIP (S81-GEOM-OPUS) | - | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |
| col_h10_r1 (12) | FIXED-PLAN D8i rows; lpad i0 west-bit WATCH (COL-H10-1119) | HANDED to COL-H10-1119: bn8 348 um, bn6 227 | HANDED to COL-H10-1119 | - | COL-H10-1119 | COL-H10-1119 | - | S81-CLOCK-WINDOW-1119 | ADVISORY |
| col_h10_r2 (12) | t7 join FIXED-PLAN D8h (COL-H10-1119) | HANDED to COL-H10-1119: e13_u_w -> bn13 -96 GRT, bn12 266 / bn13 227 um | HANDED to COL-H10-1119 | - | COL-H10-1119 | - | - | S81-CLOCK-WINDOW-1119 | PORT-HOLD -297 GRT: parent (S81-DIE-R3) |
| col_h9_r0_p1 (6) | FIXED-PLAN D8h copy + D8i cf.st / t0 rows | CC1: bn0 222->184 um | OPEN-ROW CC-BANK-2 (bs1 276) | - | - | - | - | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |
| col_h9_r0_p2 (12) | FIXED-PLAN D8i relay_depth | CC1: bn0 222->184 um; cl0045af7b bn3 201 um has no legal site (5 types, residual) | OPEN-ROW CC-BANK-2 | - | - | lpad_xo_i0.q cap-0 gcells: read on the D8i p2 builds (S81-GEOM-OPUS) | - | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |
| col_h9_r0_p3 (12) | FIXED-PLAN D8h cc_1_s0 copy + cc_1 D1 (no build until CC1) | CC1: bn0 222->184 um | OPEN-ROW CC-BANK-2 | - | - | ft0_i band: first current GRT read = CC1 build | - | S81-CLOCK-WINDOW-1119 | INT-HOLD -155..-178 CTS: FLOW |
| col_h9_r0_p4 (6) | FIXED-PLAN D8i relay_depth | CC1: bn0 222->184 um | OPEN-ROW CC-BANK-2 | - | - | - | - | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |
| col_h9_r0_p5 (12) | FIXED-PLAN D8i relay_depth | CC1: bn0 222->184 um | OPEN-ROW CC-BANK-2 | - | - | - | OPEN: xo0 rsreg -> xo2/xo3 -196 CTS; read on the D8i/CC1 p5 CTS, reset relay row (COL-CENSUS) if it stays | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |
| col_h9_r0_p6 (12) | FIXED-PLAN D8h xa_1_bs0 copy D1 + t1 sinks (no build until CC1) | CC1: bn0 222->184 um (the GRT -30..-45 end) | OPEN-ROW CC-BANK-2 | - | - | none (overflow 0) | - | S81-CLOCK-WINDOW-1119 | PORT-HOLD -103: ADVISORY |
| col_h10_r0_p1 (6) | FIXED-PLAN D8h copies + D8i relay_depth (t3 xai/xbi/cci) | CC1: bn0 248->136, bn3 197->123 um | OPEN-ROW CC-BANK-2 | - | - | - | INT-HOLD cf_rs_r78 -> nf -167 CTS: FLOW | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |
| col_h10_r0_p4 (6) | FIXED-PLAN D8h cc_1_s0 copy D1 + s0.lc D1 (no build until CC1) | CC1: bn2 283->123, bn3 197->123, bn4 214->123 um | OPEN-ROW CC-BANK-2 | - | OPEN: bin_x_i0 -> lpad_x_i0.q 528-531 um placed; read on CC1 CTS, then a relay_sites row (COL-CENSUS) | - | - | S81-CLOCK-WINDOW-1119 | ADVISORY / FLOW |

## CC-BANK-1 (my row set, 0 cycles)

- What it does: moves every `dsfd_qbank_N` u_bnK whose hw pval -> e_r0 hop is over 180 um along its own row (x only, 4.32 grid) to the legal site that minimises that hop. The he pval -> e_r1 hop stays at or under 230 um. Checks: 8.64 um keepout to every hard core, and no station reg, relay site, tap or sink site inside the bank box. Plain core move: no reshape, no cycle, no clock row. h10_r1/h10_r2 are left to COL-H10-1119. Banks with a core_pin_lead row (h9_r2 bn11/bn12) are not touched.
- Scope: 210 moves in 132 types (r0 p1-p6 bn0, h10_r0_p1 bn0/bn3, h10_r0_p4 bn2/bn3/bn4, h9_r1 bn6/bn7). 5 unfixed: col_h9_r0_p2 cl0045af7b bn3 (201 um, no legal site).
- Limit: r0 bn0 can only move 38.9 um (250.56 -> 211.68), because it sits between cfg ROMs c2_2 and c2_3. If the p6 kits still show e0_u_w -> bn0 below -42 at GRT, the next step is a c2_2 shift (read-loop check first).
- Files: epyc8 /srv/opentallas-scratch2/claude/col-census-1119/
  - cc_bank_rows.py BASE OUT_PLAN OUT_ROWS
  - rows_cc_bank.json a164cf40a01a
  - plan_cc1.json 8865a8a00190 (= f2ec5ffc3bda + CC-BANK-1)
- Proof: private cp -al of the S81-GEOM-OPUS D8h tree4 -> tree_cc1, run through build_tree_own.sh. That covers elab, strict bind (bind_rowcheck FIXEDCYC/ROWSINK/MODULES/TOOLSTALE run inside bind), local-reset writeback, G0, LATCHECK and plan_gate_pre. ot-run unit oth-ubuntu-2304581-1795143705, log intel2 ~/col-census-1119-build1.log.
- Launch chain: intel2 ~/col-census-1119/cc_chain.sh, log ~/col-census-1119-chain.log. It waits for BIND_RC=0, LATCHECK_RC=0 and PRE_PASS, then for G0 with 0 NEW errors against the control (S81-GEOM-OPUS build6 on f2ec5ffc3bda, g0diff.py). Then it generates kits for 192 types: the 132 CC-BANK-1 types plus the 60 col_h9_r2 types, which have no build on h3 anywhere. Every type with GEN_LINT_RC=0 then goes to full sign-off through ot-run at once (--mem 96, --stage kit dir, no caps). Per-type logs: intel2 ~/col-census-1119-k-<type>.log.

## Coverage after this census

- Every col type has a current-plan build queued or running:
  - S81-GEOM-OPUS: D8i, 114 types
  - COL-H10-1119: col_h10_r2, 12 types
  - COL-CENSUS: CC1, 192 types (overlap with D8i = A/B for CC-BANK-1)
- Classes still open after CC1: BANK-IN (CC-BANK-2), h9_r2 RDLOOP near miss, p5 RST, h10_r0_p4 lpad_x_i0 hop. My rows for each follow the first CC1 CTS/GRT read.
- Not type-structural: PORT-HOLD belongs to the parent (S81-DIE-R3). INT-HOLD and FLOW belong to the flow lanes: GRT max-wire skip, and kit_topology WAIT-BIND on the D8h wave rows (S81-DIE-R3 / WAVE-FLOW-R2). That WAIT-BIND blocks every col wave build on h3.

## Class WINDOW: the cw6 window eats setup inside the type (COORD 11-19, added after the first post)

The plan gives col_h9/h10 ports a flat 40 ps window. cw6 delivers 87-121 ps, and about 140 ps with the handed-off rows. The per-family port gap below is from S81-CLOCK-WINDOW 18:28. The estimate is the worst known internal reg2reg setup minus that gap. The HOP ends are left out, because D8h/D8i fix them. The estimate is worst-case: it assumes the worst path has launch and capture on different clock ports. That holds for c12_6 -> s12 and for every ROM <-> bank path (core taps).

| Family | Port gap max (ps) | Worst internal setup now (non-HOP) | Estimate at the cw6 window | In-type fix? |
|---|---|---|---|---|
| col_h9_r2 | 98 | -44.75 routed (c12_6 -> s12, read loop); signed -39.22 | about -137..-143 | No. The read loop has a fixed latency (no stage allowed). |
| col_h9_r1 | 100 | -41.49 GRT proof (u_s5 q6, read loop) | about -141 | No (same reason) |
| col_h9_r0_p6 | 88 | -30..-45 GRT (e0_u_w -> bn0, half cycle) | about -118..-133 | CC-BANK-1 gives about +10 ps, far short |
| col_h9_r0_p1/p2/p3/p4/p5 | 76-97 | not measured clean (HOP masks); the same bank and read-loop tiers | about -95..-140 | No |
| col_h10_r0_p1 / p4 | 79 / 70 | HOP masks; bank hop 248 / 283 um before CC1 | about -100..-130 | Partly (CC1) |
| col_h10_r1 / r2 | 90 / 74 | h10_r2 -96 GRT (e13_u_w -> bn13) | about -170 (r2) | COL-H10-1119 |

Verdict: every col family fails setup at the cw6 window by roughly 75-145 ps.
- The binding paths are the fixed-latency cfg read loops and the half-cycle hw ROM ports.
- No cycle can be added to either, and each sits within a few ps of zero today.
- In-type pipelining therefore cannot recover 100 ps.
- The fix is die-side: a tap-balance request to S81-CLOCK-WINDOW-1119.
  - Balance the col core taps in the cw6 region DME so that col_h9/h10 port windows stay at 40 ps or less, 50 ps at most.
  - This is the same core-tap sink-balance lever as the attn_hcore class A.
  - Do NOT widen the col per_port windows to the cw6 need: that turns a die-clock error into roughly 100 ps of type-internal setup loss on all 216 types.
- In-type, CC-BANK-1 still helps the half-cycle class. CC-BANK-2 (bank-in) follows the CC1 read.
- The CC1 kits keep the 40 ps plan window, so they measure the type itself.

## Update 11-19 (COORD rulings): CC-BANK-1b + CC-WIN40, one build plan

- COORD ruled: col windows stay at 40 ps, and the die tree balances the col taps (S81-CLOCK-WINDOW-1119). CC-BANK-1 is approved.
- CC-BANK-1b (0 cycles, core moves only, keepout checks, old origins asserted). Script: cc_bank2_rows.py; rows: rows_cc_bank1b.json 0021a418299c.
  - Form A, all 60 col_h9_r0_p1..p6 types: move cfg ROM u_r0.u_c2_2 from x 164.16 to 276.48, into the free gap between s2 and c2_3. Its read loop to u_s2 gets shorter. Then move bn0 from 211.68 to 151.20. hw pval -> e_r0 goes 222 (base) -> 184 (CC-BANK-1) -> 123 um; he pval -> e_r1 goes to 229 um.
  - Form B, the 5 col_h9_r0_p2 cl0045af7b types: move station core u_r0.u_t2 36.72 um left to x 671.76 (moving it up hits u_e4). Then move bn3 to (764.64, 878.04), 8.64 um clear of the e3 ROM top (it was 7.56). hw pval -> e_r0 goes 201 -> 164 um. No p2 type is left without a bank site.
- CC-WIN40: every col_h* per_port and per_type window is clamped to 40 ps or less; the core-tap ports at 10 ps are untouched. 34 entries in 2 types: 30 ports of one col_h9_r0_p6 type (the max was 129 ps) and 4 ports of one col_h9_r2 type. Script: cc_win40.py; rows: rows_cc_win40.json da619119535d.
- Build plan: plan_cc2w.json 2d02a37c322f = f2ec5ffc3bda + CC-BANK-1 + CC-BANK-1b + CC-WIN40. The plan_cc1 bind was stopped in elab (my own unit, ot-heavy-stop; nothing published) and replaced by:
  - bind tree_cc2, ot-run oth-ubuntu-2498337-1795144503, log intel2 ~/col-census-1119-build2.log;
  - chain ~/col-census-1119/cc_chain2.sh, log ~/col-census-1119-chain2.log. Same gates (BIND/LATCHECK/PRE, G0 0 new vs GEOM build6), then the same 192 types to full sign-off. Kits go in kb2, logs in ~/col-census-1119-k2-<type>.log.

## Update 11-19 ~19:3x: CC-BANK-2 (bank-in hop), written from plan distances (Fable 19:15 lever 2)

- CC-BANK-2 adds no cycles; it only moves cores, with no reshape. Script: cc_bank3_rows.py; rows: rows_cc_bank2.json 50e4e0b000f7.
  - Each dsfd_qbank_S u_bsN moves on the 4.32 grid (x within ±80 steps, y within ±12 steps) to the site that minimises the worst pin-span Manhattan distance from o_x0/o_x1 to the xs_q pins of both ROM halves eN.u_w and eN.u_e. The distance is orientation-aware and taken at the worst-case corners.
  - Each site keeps the 8.64 um keepout and has no station reg, relay site, tap or sink site inside it. The centre moves at most 160 um, because the bank input is a full-cycle registered hop. A move is applied only when it gains at least 20 um.
- Applied: 768 banks in all 192 build types.
  - Every family goes from 237–306 um worst to 194–207 um. Examples: h9_r0 p1–p6 271–284 -> 194–202; h10_r0_p1 306 -> 196; h9_r1 and h9_r2 237–241 -> 194–207.
  - 12 banks gained nothing (under 20 um).
  - About 195 um is close to the floor for one bank serving two ROM halves 268 um apart. If the CC3 CTS still shows the hop failing, the next form needs a bank split or a stage (+1 cycle).
- col_h10_r1/r2 (COL-H10-1119): 84 bank rows (48 h10_r1, 36 h10_r2), each 237–241 -> 194–196 um. They are written as PROPOSED only, under proposed_not_applied in the same rows file, and handed to COL-H10 to adopt.
- The cc2w bind was still in elab, before G0, so I stopped it (own unit) and restarted it with everything included:
  - plan_cc3.json 4c0809267941 = f2ec5ffc3bda + CC-BANK-1 + CC-BANK-1b + CC-WIN40 + CC-BANK-2;
  - bind tree_cc3, unit oth-ubuntu-2562904-1795144815, log intel2 ~/col-census-1119-build3.log;
  - chain cc_chain3.sh, log ~/col-census-1119-chain3.log. It runs the same gates, then sends the same 192 types to full sign-off. Kits go in kb3, logs in ~/col-census-1119-k3-<type>.log.
