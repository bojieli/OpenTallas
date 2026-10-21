# QW-LANDW3 reset-landed wide flop landings (d8g / d8gn, 107 and 116)

Successors of the d8f/d8fn native32 masters (394bda8c4). Their four CTS gates were refused only by
textbook.reset_landing: port rs fed 8/9 first-stage flops (top rs0 + one rs0 per calendar copy). 116 also had a util WARN of 44.8 %.

Fix (RTL, `ot_qfd_land8_fan32 #(.RSL(1))`, default 0 keeps d8f/d8fn byte-identical in behaviour):
rs reaches exactly 2 kept face flops, rs0 (top rs1, regions, meta) and rs0c (the <=8 calendar copies). Each copy
(`ot_qfd_land8_ctrl_copy1`) keeps only its local second stage rs1. So rs -> rs0|rs0c -> rs1 -> rc releases on the
same edges as before: no added reset edge, no K, calendar or II change, and assert stays asynchronous.
ot_rst_relay was NOT used because it adds a third release edge (SYNC 2 + TREE 1) that the K strap does not price, and
its port clears >2 flops. The 116 outline went 54 -> 51.84 um square.

Masters: qfd_landh0d8g_107_EW_52x52 / qfd_landh0d8g_116_EW_52x52 (main, ICG) and qfd_landh0d8gn_* (fallback, no ICG).

Pre-gate native census (census/, mapped ORFS synth, transparent all-driver, reset included), on ep5 at 1e76eb382:
| master | over32 | max | FF | rs port loads | rs0 loads |
|---|---|---|---|---|---|
| d8g/d8gn 107 | 0 | 30 | 1843 | 2 | 29 |
| d8g/d8gn 116 | 0 | 32 | 1987 | 2 | 31 |
Textbook hf/reset at 32: PASS. Depth is 185.0/181.7 ps.

Benches (bench/, Verilator 5.050): 4 masters x (pass + sel/naive/vld/encomb/k3/wsel/rsel + new rsl mutant, where the copy lands
one stage late) = 36/36 qualified. Pass covers 72 calendars, K 0..15, phases, release orders and restarts over 3 seeds.

CTS gates (PASS 0 fail 0 warn; GRT overflow 0):
| kit | util | setup/hold WNS ps | ck spread TT/FF | ck_s spread TT/FF | ins max TT/FF |
|---|---|---|---|---|---|
| d8g_107 | 47 % | +299.8/+34.8 | 7.7/8.1 | 9.3/8.6 | 153.2/119.1 |
| d8gn_107 | 47 % | +301.7/+46.6 | 1.9/2.1 | 4.7/4.9 | 100.9/80.2 |
| d8g_116 | 50 % | +301.6/+47.9 | 7.7/7.4 | 6.9/6.2 | 150.9/117.0 |
| d8gn_116 | 50 % | +303.8/+46.1 | 4.9/5.0 | 7.5/6.9 | 104.4/82.9 |

Safe-design checklist:
1. Pins: PASS. Inputs land on one flop stage (bounded CE mux, root-approved 01:31), outputs are flops, rs is landed in 2 stages at the face (fixed).
2. Reach: PASS. The tile is 51.84 um square, so no wire exceeds 405 um.
3. Fanout: PASS. Native max is 30/32, no paramod merge (rs0c and every copy rs1 survive: FF -6/-7 vs d8f).
4. Depth: PASS, 185 ps / 6 levels.
5. Storage: PASS. The ring is 856/928 b (<2 kb), with no runtime-indexed array.
6. Floorplan: PASS. The tile is square, with no macros, one full std band, util 47/50 %, a on E, b on W and control on N (PNGs viewed: uniform density).
7. Clock: PASS. Spreads are <=9.3 ps, and io_hold_margin is 0.03.
8. Schedule: PASS. No edges are added, and K=(L+G-R0-2) is unchanged.
