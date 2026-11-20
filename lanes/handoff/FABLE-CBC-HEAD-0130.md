# FABLE-CBC-HEAD-0130: hd_lep0N close-by-construction review, rows for r13 / r14

2026-11-20 00:32 to 01:00 PST. To HEAD-CROSSING-1119 (owner of the r13 drafts). Scope cut by COORD to hd_lep0N, the one HEAD type unsigned on any plan. Rows: `lanes/handoff/FABLE-CBC-HEAD-0130-rows.json`.

Paths are epyc10 unless named. `M` = `/srv/opentallas-scratch2/claude/fable-cbc-head-0130` (scripts `pairs.py`, `chains.py`, `macropin.py`, `stations.py`, `patch_rows.py` and their outputs). Inputs: the r8b placed `geom.tsv` (`kw43-wave-1109n/.../head_rp21z20NF15f_r8b/items/hd_lep0N/geom`), the pair LEF in the kit, `r13/lep0N/plan_r13_lep0N.json`.

## State of the builds

- hd_lep0N has never finished a build. The r8b wave route job (`ot-jobs/hd_lep0N-route-civil-redfish-285021-1795150613`) re-ran floorplan and placement and has been inside `4_1_cts` since 07:42 UTC with no timing line at 08:54 UTC. The private r11b kit is in global placement.
- Neither kit has a station row, a current tap table or the fixes below, so neither can sign. They are measurements only.
- The fleet admits 0 GB on every host (epyc10: 49 waiters, 2.8 TB). Nothing of mine has run yet.

## What the r13 lep0N draft gets right

Per-bit maxima on the r8b sites: coll_i0 131 / 310 / 353 um, coll_o0 377 / 328, unit_i0 338 / 324, ctrl_o0 306 / 303. All under 405. The RST-FAN core fan and mapped u_lep tree cover u_rrl_657 and group->local. The six fclk_out repoints are in.

## What it does not cover (ranked)

| # | Class | Finding | Fix | Cycles |
|---|---|---|---|---|
| 1 | geometry, fixed-to-fixed | **Hidden hard-core pin legs.** `placed_scan` measures to the macro box, not the pin. Real: u_bin_coll_i3 -> pair3.coll_i 861 um, 482 bits over 405, 272 over one cycle (scan: 467 / 7). pair3.coll_o -> u_bout_coll_o3 616 um, 311 over, 55 over a cycle. pair2.coll_o -> u_bout_coll_o2 565 um, 123 over. coll_i1 417 (6). | internal_stations: coll_i3 2 (hops 287/280/293), coll_o3 2 (255/240/242), coll_o2 1 (284/287), coll_i1 1 optional | +2, +2, +1, (+1) |
| 2 | geometry, rows | **g_rxr rows reversed.** rxr stage j shares rxf stage j's band, but rxr runs centre -> pair. li2_r -> s0 762, rxv_r 708, li1_r 686; s5 -> pair k_li_r pin 685 / 609 (hidden). | rxr stage j takes the band of rxf stage N-1-j. After: 43 / 149 / 235 at the head, 140 / 392 at the pin. li3_r stays 484: one row for li3_r or KRX lane 3 = 3. | 0 |
| 3 | clock | **Tap table stale.** Kit split: clk_t130 6,597 sinks, clk_t127 5,994, 33 taps over the 800 cap, 45 taps with 10 or fewer. The bins file is the r4 census, older than the NF15f stage tuple. hd_host_w failed TT -56.32 / FF -21.08 with seven taps near 3,000. | density taps from the r8b placed census, die clock rerun, rows, offsets and windows in the same event | 0 |
| 4 | geometry, rows | **g_pin / g_pout mix buses with different face windows** (lepk y 10..511, unit / ctrl y 800..850, fault y 1084). r13 stations fix unit_i0 and ctrl_o0 but leave fault_o0 845, lepf_i0 639, g_pin s5 -> u_land.rcq 470. | four slice rows on the existing stages (pin_s0u, pin_s5u, pout_s7c, pout_s7f): 310..350 um. Replaces the two r13 stations. | 0 |
| 5 | RTL, small | **Credit return fan.** kr -> 18 credit_pin_r copies: lane 3 735 um (copies span 556 um), lane 0 472, lanes 1 / 2 421. | g_txr stage count split from KTX (lane 3 = 3, lane 0 = 2), sited rows | credit round trip only |
| 6 | geometry, rows | g_plw s1 -> s2 560 um | plw_s2 band to y 822: 337 / 339 | 0 |
| 7 | reset | local_r[1] / [953] / [3] sit 500 / 579 / 445 um from their loads | relay_sites at the load centre: 282 / 263 / 225. rxvb needs its lane local (two flops 931 um apart on one local). | 0 |

Open points inside the draft: rule 1 START reach still fails in `rr_check_r13.tsv` (416 and 485 um); g_c0i / g_c0o have no stage rows; unit_lep +1 and ctrl_lep +1 move those lanes against lepk, which the RTL header treats as one count, so run `tb_head_lepk_stages` on the r13 wrapper or take row set 4 instead.

## Family rules worth keeping (generator level)

1. A stage rank row carries one face leg. A rank that mixes buses is split by bit slice.
2. A return chain takes the forward chain's bands in reverse order.
3. Reach checks use hard-core pin sites. `placed_scan.py` needs pin names in `geom_dump.tcl` N lines; until then every flop <-> hard-core leg is under-reported.
4. A stage tuple change re-derives the tap table from a fresh census in the same event.
5. A reset local is sited at its load centre; a load span over 405 um splits it.

## Proof status

- **Not measured.** Fleet admission is at 0 GB.
- Queued 1 (hub client `intel2:~/fcbc0130/proof_rxr.otrun.log`): `M/proof_rxr`, a `kit_fork.py` fork of the private r11b kit with `patch_rows.py` (30 changed lines: rows 2 and 6 only), goal route, 64 GB. It proves the two zero-cycle row changes; it does not contain rows 1, 3, 4, 5. Read `M/proof_rxr/run.log` and the kit's `OT_PLACE_WIRE_RATIO`, `OT_CTS_POST_TIMING`, `OT_TT_SETUP_REPAIR` lines.
- Queued 2 (`intel2:~/fcbc0130/sta_r8b.otrun.log`): placement-RC TT census of the r8b `3_place.odb`, output `M/sta_r8b/paths_TC.json`. It is the check that the 861 um coll_i3 leg is the worst end.
- Rows 1 and 3 need a gen pass, so the real proof is your r13 kit. I did not build a second gen tree.

## Not checked

- Any timing number for hd_lep0N: none exists yet.
- Free sites at the proposed station and slice coordinates; they are targets.
- Whether the slice regexes take precedence over the whole-stage rows in `landing_placement.tcl`.
- Whether ctl compensates LAT_UNIT_LEP / LAT_CTRL_LEP against kd / ku.
- The density tap table itself (needs the clock-net census from the ODB).
