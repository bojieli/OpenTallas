# FABLE-PD-KV-HG1: r199 structural review of KV plan event KV-HG1 (HG1A / HG1B), 2026-11-16 PST

Reviewed: HG1A plan 08d352df7ef0 (7yhr + v25hv + k2r + row A) and HG1B plan b78d8aa38797 (A + rows B + C), epyc10
`/srv/opentallas-scratch2/claude/fable-fix-kv-pvhub/hg1/` (plan_hg1A.json, plan_hg1BC.json = treeB plan_c.json, sha checked),
die run `hg1/runs/c1` (on HG1A, clock form E). MEASURED = computed by me from those files today (read-only; my scratch
epyc10 /tmp/fable-pd-kv-hg1). REPORTED = lane post.

## Verdict: ADOPT-WITH-SPLIT

- **Adopt now: HG1A + clock form E** (rows A, v25hv, k2r). Gated (pre 0 / G0 0 / bind 0 / LATCHECK 2404 of 2404, REPORTED) and
  die-proven on its own plan (c1, MEASURED below).
- **Hold rows B as cut** (9,286 rects). The merge turns 2.2-um clock cell sites into full M1-M7 walls along core pin edges
  (finding B-1, the HEAD NF14 problem). Regenerate B without merging along pin edges, then HG1B' = A + B' + C.
- **Rows C** are correct but have 0 ps margin by construction; they are valid only for the exact c1 tree. Ship with B'
  (same tree), regenerate at every event that moves a tap.
- Not BLOCK: no type has been built with rows B, so there is no measured failure on a released type.

## 1. Rows A: START reach (MEASURED: reach_rules.py check on treeB, 13 types; plan diff hgpv -> HG1A -> HG1B)

| type | reader depth before -> after | reader worst hop um | writer worst hop um | over 405 |
|---|---|---|---|---|
| kv3_pv_v2, v2n | 10 -> 12 | 365.0 | 365.0 | 0 |
| kv3_pv_v3, v3n | 9 -> 11 | 365.0 | 389.8 | 0 |
| kv3_pv_v4, v4n | 12 -> 12 | 365.0 | 380.3 / 354.2 | 0 |
| kv3_pv_v5, v5n | 11 -> 11 | 365.0 | 372.2 | 0 |
| kv3_pv_v6, v6n | 11 -> 12 | 365.0 | 365.0 | 0 |
| kv3_hg_v1p5, v1p6 | 7 -> 7 | 338.0 | 337.4 | 0 |
| kv3_io_cor_v1 | 4 -> 6 | 333.4 | 372.5 | 0 |

- All 13 close: R-REACH-1 0 errors, worst START hop 389.8 um (15.2 um under 405).
- Cost: 0 data cycles. `lanes`, `latency`, `count_aligned_cycles`, `count_aligned_bind` (root_settle 64) are byte-equal
  before and after. START depth +2 on 5 types, +1 on 2, max depth 12 of the 64-cycle settle. 47 to 157 relay sites per type.
- A-1 (new, small): R-REACH-4 fires on kv3_hg_v1p5 and v1p6: 3 forwarded clock outputs each take tap clk_t2 at 417.4 um
  (nearest tap at 34 um). Fix `reach_rules.py fix --rules 4`, 0 cycles. Not a START hop; next row set.

## 2. Rows B: reserved clock sites (MEASURED on plan_hg1BC + core LEF pins + raw sites from c1 tree.json)

- Size is fine: 9,286 rects, 0.07 to 0.30 % of type area (278,143 um2 total), 0 rects overlap a hard core.
- **B-1 (HOLD): merged walls on core pin edges.** gen_phys emits each rect as placement blockage AND M1-M7 routing
  obstruction. The merge (17,762 -> 9,286 rects, area x4.4: kv3_hg 1,116 -> 4,922 um2) builds strips 1.1 to 1.4 um high and
  up to 560 um long. 997 strips run >= 10 um along a core edge within 5 um of it (gap is 2.16 um in most). Counting the
  core LEF signal pins on the facing edge inside the strip span (cores with a LEF only, so a lower bound; pcc / pcf not counted):
  - 392 walls have pins behind them; 330 have >= 50; 221 have >= 138; **125 have >= 276 pins**.
  - 276 is every horizontal track (M2 + M4 + M6, about 138) of a 2.16-um gap used once to each side: beyond it the pins
    cannot leave even in theory.
  - Worst: kv3_pv_v1n rect [741.4, 1289.5, 955.8, 1290.9]: 214.4 um wall 2.16 um above pvg1_p3 (kv3_pv_pair), **946 of its
    1,660 M5 pins behind it**. That wall is made of 4 raw sites of 2.16 um (8.6 um of 214.4).
  - Per type pins behind walls: pv family 1,628 to 6,139 (all 18 pv types), hgi 281 to 1,538, hg 522 to 963, hub_C 142.
  - Raw sites (no merge): longest side 2.21 um, at most 16 pins behind one site, 0 walls. So the defect is the merge only.
- B-2: about 280 planned register points lie in or within 0.5 um of a reserved blockage: 89 ft station points (kv3_pv_v4
  15, hub_Eo 10, hub_Wo 10), 76 START reader stages (kv3_pv_v5 17), 44 START writer stages (kv3_pv_v12 14), 71 internal
  station points. G0 does not check this. Most should clear with unmerged rects; re-count on B'.
- B-3: 9 types hold 220 to 380 rects (kv3_pv_v12 380) against the cap target 100. With B-1 the cap must give way, not the pins.
- Fix (script, one rule): in `clksite_reserve.merge_rects`, never form a merged rect that lies within 5 um of a hard-core
  edge unless it is under about 10 um long (or pass the pin edges as blockers with a 5-um gap). Then re-run my wall count:
  target 0 walls with >= 50 pins. First build check: kv3_pv_v1n to GRT with the rows.

## 3. Rows C: per-port windows, seam 180 -> 200 (MEASURED: kitwin.json vs rows_windows_c1.json vs die_sta_related.json)

- 6,129 ports on 51 types: window = measured need on every port (window - need = 0.00; mean 68.1, p90 114, max 208.25 ps;
  171 ports over 150 ps). Need = max over TT / FF of late - early - CPPR, nominal, no OCV term.
- Left over on c1: 1 clamped port (kv3_pc_v1__cl4ea58a5c clk_t25 need 211 vs 208.25, -2.75 ps) and signed kv3_sys_SD
  (need 81 vs flat 80). Both advisory under R-MINIMAL. Other 4 signed types fit their flat window (max need 62 of 80, 37 of 100).
- Seam: need 188.48 ps on c1 (188.5 on 7yhr) against 200: margin 11.5 ps. OK.
- Sensitivity: the tree is deterministic (41 unchanged types reproduce 7yhr needs to 0.0 ps), but on the types the compose
  touched the need moved by p90 29 ps, p99 55 ps, max 91 ps (kv3_pv_v12), and 2,548 of 5,774 ports (44 %) now need more than
  their 7yhr window (470 by more than 25 ps). So C is safe for the c1 tree only and must be regenerated with every tap move.
- Old flat windows under-cover 20 types on c1 (intra need 178.0 vs 120), so C is needed; without it 376 + 8 contract pairs.
- Not measured: die STA on HG1B itself; die hold on real views (0 of 1,453,812 pairs; 444 early taps signed, 1,928 planning-only).

## 4. Row E: H-tree + DME on pv_N_7 and phy_*_7 (MEASURED from c1 proof, 11,571 taps, 33,360 inverters)

- Slew: max 128.4 ps TT / 123.6 FF, 0 taps over 150, 9 over 120 (TT). Margin 21.6 ps. The five E regions are now 11.5 to
  32.3 ps; the worst tap moved to hgi_EN_7 (H-tree region, clk_c2).
- Die GRT0 TT and FF: 0 overflow, use 2.48 %, 286.9 m. Setup TT +482.8 intra / +510.6 seam; count-aligned 3,915 of 3,915.
- Watch: insertion max 8,079 ps TT (7,149 on 7yhr); worst per-partition spread pc_WS_7 263 ps, pc_ES_7 194, pv_N_7 188.
- The plan `clock.cohort` still names tree_kv58 (2,114 taps, DME on pv_S_6 / pv_S_7 / sys_SW / sys_SE). Record the c1 tree
  sha and form E there with B' / C, since C is only valid for that tree.

## 5. Open after KV-HG1

| item | number | state |
|---|---|---|
| Row B2: die clock cells on signed kv3_phy / kv3_phy_v1 | 2,024 cells (REPORTED, 7yhr); c1: 381 distinct type-frame sites on the two types, 670 on the 5 signed types | The c1 tree is not buildable on the phy partitions until B2 + re-sign, or a tree stamped on the 45 / 55 islands. Owner FABLE-DIE-KV. Do B2 with the B-1 merge rule. |
| hg wide ports over 405 um | 39 ports / 7,128 bits, max 530.21 um (hg_EN_0.ft2_o -> hgi_EN_0.ft27_i, 321.3 inside hg + 209.0 inside hgi) on HG1A, unchanged | KV-PVHG-O. +1 station siting exists for 7 types (19,219 FF bits) but model_ready_to_build=false. |
| Die hold on real views | 0 measured | needs signed views; -3.13 ps FF pair is two independent incoming rings (REPORTED), not a data edge |
| R-REACH-4 hg_v1p5 / v1p6 | 6 outputs, 417.4 um | A-1 |

## Not checked
Detailed route; PG / IR; any type kit with rows B or C; OCV on the E tree; pin counts on cores without a LEF in treeB
(qkd_kvs_pcc / pcf, hr cores), so the pc-type walls (up to 189 um) are unpriced.
