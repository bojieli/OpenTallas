# Per-pair die hop check: qwen_rom_tp8

Tool `tools/hier_contract/pinreg_pairs.py` at 80ca30a2a; case `results/arch/pinreg_audit_1013/pairs/qwen_rom_tp8_plan.json.gz`; 11,902 instances, 14,740 data hops / 6,580,701 bits (pin centroid to pin centroid (Manhattan) of the two ports, generator pin model).

Rule: TREE `o_A + 0.76 L + s_B <= W - 60 - SKEW` (SKEW 90, 150 when an R is over 300 ps), hold `l_A + 0.112 L - h_B >= 100` at FF; FWD (forwarded clock beside the bus) on the real forwarded edge; a side without a view takes the flat share 151.7 ps (two placeholders = 500 um). Relay class `^qfd_cst_[ns]$`: o 197.2 / s 162.5 ps.

## Counts

| ends with a real view | pass | setup fail | hold only | clock crossing | not evaluable |
|---|---|---|---|---|---|
| both | 534 | 8 | 0 | 0 | 0 |
| one | 2,713 | 703 | 0 | 0 | 0 |
| none (flat 500 um) | 10,782 | 0 | 0 | 0 | 0 |

Link models: DEFAULT 10,782, TREE 3,958.

Die port -> view pin binding of the judged hops with a real end: direction 1,313, exact 288, prefix 2,357 (exact = the view has a bus of the port's name; prefix = its <port>_* buses of that direction; direction = the die master's port names are not the element's: worst data bus of that direction, an upper bound).

## Fix totals

| fix | pair classes | hops | bits |
|---|---|---|---|
| (i) one more die relay (cycle) | 26 | 591 | 188,681 |
| (ii) pin register in the tile (re-route, +1 cycle a side) | 4 | 88 | 14,664 |
| (iii) pin re-plan / shorter hop (no cycle) | 13 | 32 | 11,403 |

## Cycles per token

Basis: tools/qwen_rom_fulldie_b3r2.py relay_token_cost: 217 ME ops per AR token wait on the longest bd (head chain + corridor + tap), in-block tree, tws (block word -> tree top) and ord chains; hub <-> stack link 2 x 36 traversals per token (results/rtl/qwen_dietop_takeover_20261006/observed_relay_token_cost.json); 216,713 cycles per AR token (results/rtl/qwen_elements_final_20261007/elements.json); kvn / io / sequencer / cdc / crom / d2d are not on the per-op chain (not priced: null)

- stack_local@kv: +2 stage(s) x 72 uses per token
- stack_local: +2 stage(s) x 72 uses per token
- cdc_core: +1 stage(s) x None uses per token
- hbm_cdc: +1 stage(s) x None uses per token
- spine_local@kv: +2 stage(s) x 217 uses per token
- spine_local: +1 stage(s) x 217 uses per token
- crom: +1 stage(s) x None uses per token
- sequencer: +1 stage(s) x None uses per token

Added cycles per token: 939 of 216,713 (0.433 %)

## Tiles

| master | inst | audit flags | verdict | hops (both real) | fail | hold | worst setup / hold margin ps | why |
|---|---|---|---|---|---|---|---|---|
| qkd_kvwq_ctl_bin | 4 | out_unreg, in_unreg, abut | RE-ROUTE | 44 (8) | 24 | 0 | -335.0 / 155.8 | pin register on the out side for 8 hops |
| qkd_ectl | 32 | out_unreg, in_unreg, abut | RE-ROUTE [candidate] | 480 (0) | 272 | 0 | -327.5 / None | pin register on the in side for 80 hops; UPPER BOUND on 272 of its failing hops: the die master's ports are bound to the view by direction (no bind map), worst bus taken; ALIAS view (same-family master): confirm on the real master |
| ot_qfd_serdes_112g_x12_phy | 1 | min_delay | STANDS | 1 (0) | 0 | 0 | 140.0 / None | all 1 judged hops pass |
| qfd_chead_e | 24 | - | STANDS | 95 (46) | 0 | 0 | 43.4 / 102.1 | all 95 judged hops pass |
| qfd_chead_w | 24 | - | STANDS | 95 (46) | 0 | 0 | 41.2 / 104.2 | all 95 judged hops pass |
| qfd_cst_n | 384 | - | STANDS | 1,104 (0) | 0 | 0 | 22.4 / None | all 1104 judged hops pass |
| qfd_cst_s | 384 | - | STANDS | 1,104 (0) | 0 | 0 | 34.8 / None | all 1104 judged hops pass |
| qfd_tt_up4 | 1 | in_unreg | STANDS | 9 (0) | 0 | 0 | 42.9 / None | all 9 judged hops pass |
| qkd_kvwq_leaf_s_w129_m | 128 | in_unreg | STANDS (die fix) | 736 (712) | 13 | 0 | -80.4 / 110.4 | 13 failing hops are fixed in the die (8 relay, 5 re-plan) |
| qfd_crom_g | 8 | in_unreg | STANDS (die fix) [candidate] | 16 (8) | 6 | 0 | -62.5 / 78.1 | 6 failing hops are fixed in the die (4 relay, 2 re-plan); UPPER BOUND on 6 of its failing hops: the die master's ports are bound to the view by direction (no bind map), worst bus taken; ALIAS view (same-family master): confirm on the real master |
| qfd_su_cbuf_g | 8 | spread | STANDS (die fix) [candidate] | 48 (8) | 20 | 0 | -82.3 / 78.1 | 20 failing hops are fixed in the die (11 relay, 9 re-plan); UPPER BOUND on 20 of its failing hops: the die master's ports are bound to the view by direction (no bind map), worst bus taken; ALIAS view (same-family master): confirm on the real master |
| qkd_cdc_wleaf | 128 | out_unreg, in_unreg, abut | STANDS (die fix) [candidate] | 768 (256) | 384 | 0 | -196.5 / 110.4 | 384 failing hops are fixed in the die (384 relay, 0 re-plan); UPPER BOUND on 384 of its failing hops: the die master's ports are bound to the view by direction (no bind map), worst bus taken |

## Pair classes that fail (all), then the tightest passing ones

| class | src.pin -> dst.pin | model | real | hops | bits | max um | reach um | o / s ps | setup / hold margin ps | fix |
|---|---|---|---|---|---|---|---|---|---|---|
| stack_local@kv | qkd_rhead.s -> qkd_ectl.s# | TREE (direction) | 1 | 128 (64 F, 0 H) | 4,352 | 477.1 | 46.1 | 151.7 / 436.6 | -327.5 / None | pinreg:dst x1 (64) |
| stack_local | qkd_ectl.t# -> qkd_rhead.ti | TREE (direction) | 1 | 128 (64 F, 0 H) | 199,552 | 467.5 | 70.7 | 417.9 / 151.7 | -301.5 / None | relay x2 (64) |
| stack_local@kv | qkd_ectl.e# -> qkd_rhead.e | TREE (direction) | 1 | 128 (64 F, 0 H) | 2,048 | 464.2 | 70.7 | 417.9 / 151.7 | -299.0 / None | relay x2 (64) |
| cdc_core | qkd_cdc_wleaf.co -> qkd_land.c#i | TREE (direction) | 1 | 64 (64 F, 0 H) | 18,112 | 454.4 | 195.9 | 382.8 / 151.7 | -196.5 / None | relay x1 (64) |
| cdc_core | qkd_cdc_wleaf.co -> qkd_land_n.c#i | TREE (direction) | 1 | 64 (64 F, 0 H) | 18,112 | 454.4 | 195.9 | 382.8 / 151.7 | -196.5 / None | relay x1 (64) |
| cdc_core | qkd_cdc_wleaf.cf -> qfd_rly_#_WE_#x#.a | TREE (direction) | 1 | 64 (64 F, 0 H) | 64 | 408.5 | 195.9 | 382.8 / 151.7 | -161.6 / None | relay x1 (64) |
| cdc_core | qkd_cdc_wleaf.cf -> qfd_rly_#_EW_#x#.a | TREE (direction) | 1 | 64 (64 F, 0 H) | 64 | 400.2 | 195.9 | 382.8 / 151.7 | -155.3 / None | relay x1 (64) |
| hbm_cdc | qkd_ctrl.c#o -> qkd_cdc_wleaf.hi | TREE (direction) | 1 | 64 (64 F, 0 H) | 18,816 | 161.6 | 102.6 | 151.7 / 453.7 | -44.8 / None | relay x1 (64) |
| hbm_cdc | qkd_ctrl_n.c#o -> qkd_cdc_wleaf.hi | TREE (direction) | 1 | 64 (64 F, 0 H) | 18,816 | 161.6 | 102.6 | 151.7 / 453.7 | -44.8 / None | relay x1 (64) |
| spine_local@kv | qkd_kvwq_ctl_bin.f# -> qkd_rly_#.a | TREE | 1 | 12 (12 F, 0 H) | 3,516 | 449.9 | 9.2 | 464.7 / 151.7 | -335.0 / None | pinreg:src x1 (8), relay x2 (4) |
| stack_local@kv | qkd_astk.e#o -> qkd_ectl.si | TREE (direction) | 1 | 16 (12 F, 0 H) | 10,144 | 259.8 | 46.1 | 151.7 / 436.6 | -162.4 / None | replan (4), pinreg:dst (8) |
| stack_local@kv | qkd_astk_n.e#o -> qkd_ectl.si | TREE (direction) | 1 | 16 (12 F, 0 H) | 10,144 | 259.8 | 46.1 | 151.7 / 436.6 | -162.4 / None | replan (4), pinreg:dst (8) |
| stack_local@kv | qkd_ectl.so -> qkd_astk.e#i | TREE (direction) | 1 | 16 (12 F, 0 H) | 6,800 | 259.8 | 70.7 | 417.9 / 151.7 | -143.7 / None | replan (4), relay x1 (8) |
| stack_local@kv | qkd_ectl.so -> qkd_astk_n.e#i | TREE (direction) | 1 | 16 (12 F, 0 H) | 6,800 | 259.8 | 70.7 | 417.9 / 151.7 | -143.7 / None | replan (4), relay x1 (8) |
| spine_local | qkd_ectl.rq -> qfd_rly_#_SN_#x#.a | TREE (direction) | 1 | 8 (8 F, 0 H) | 128 | 413.3 | 70.7 | 417.9 / 151.7 | -260.3 / None | relay x1 (8) |
| spine_local@kv | qkd_ectl.rq -> qkd_land.rq# | TREE (direction) | 1 | 8 (8 F, 0 H) | 128 | 327.3 | 70.7 | 417.9 / 151.7 | -195.0 / None | relay x1 (8) |
| spine_local@kv | qkd_ectl.rq -> qkd_land_n.rq# | TREE (direction) | 1 | 8 (8 F, 0 H) | 128 | 327.3 | 70.7 | 417.9 / 151.7 | -195.0 / None | relay x1 (8) |
| spine_local@kv | qkd_kvwq_leaf_s_w#_m.dp -> qkd_rly_#.a | TREE | 1 | 12 (5 F, 0 H) | 24 | 449.1 | 441.0 | 196.5 / 151.7 | -6.1 / None | replan (5) |
| spine_local@kv | qkd_ectl.rq -> qkd_rly_#.a | TREE (direction) | 1 | 4 (4 F, 0 H) | 64 | 446.8 | 70.7 | 417.9 / 151.7 | -285.8 / None | relay x2 (4) |
| spine_local | qkd_ectl.rq -> qfd_rly_#_NS_#x#.a | TREE (direction) | 1 | 4 (4 F, 0 H) | 64 | 414.8 | 70.7 | 417.9 / 151.7 | -261.5 / None | relay x1 (4) |
| crom | qfd_su_cbuf_g.fa -> qfd_rly_#_NE_#x#.a | TREE (direction) | 1 | 4 (4 F, 0 H) | 824 | 398.0 | 289.7 | 251.5 / 151.7 | -82.3 / None | relay x1 (4) |
| spine_local@kv | qkd_kvwq_leaf_s_w#_m.dp -> qkd_kvwq_ctl_bin.r# | TREE | 2 | 4 (4 F, 0 H) | 8 | 438.4 | 332.7 | 196.5 / 174.0 | -80.4 / 179.1 | relay x1 (4) |
| crom | qfd_rly_#_WE_#x#.b -> qfd_crom_g.ra | TREE (direction) | 1 | 4 (4 F, 0 H) | 824 | 378.1 | 295.9 | 151.7 / 246.8 | -62.5 / None | relay x1 (4) |
| spine_local@kv | qkd_kvwq_ctl_bin.f# -> qkd_kvwq_leaf_s_w#_m.c | TREE | 2 | 4 (4 F, 0 H) | 1,172 | 244.0 | 162.8 | 322.6 / 177.0 | -61.7 / 155.8 | relay x1 (4) |
| crom | qfd_su_cbuf_g.sq -> qfd_sp_su#_sfu.cq# | TREE (direction) | 1 | 8 (4 F, 0 H) | 4,096 | 359.0 | 289.7 | 251.5 / 151.7 | -52.7 / None | relay x1 (4) |
| crom | qfd_sp_su#_sfu.ca# -> qfd_su_cbuf_g.sa | TREE (direction) | 1 | 8 (4 F, 0 H) | 1,648 | 394.3 | 348.9 | 151.7 / 206.5 | -34.5 / None | replan (4) |
| spine_local@kv | qkd_kvwq_ctl_bin.fault -> qkd_land.wfault | TREE | 1 | 2 (2 F, 0 H) | 2 | 373.7 | 263.2 | 271.6 / 151.7 | -83.9 / None | relay x1 (2) |
| spine_local@kv | qkd_kvwq_ctl_bin.fault -> qkd_land_n.wfault | TREE | 1 | 2 (2 F, 0 H) | 2 | 373.7 | 263.2 | 271.6 / 151.7 | -83.9 / None | relay x1 (2) |
| sequencer | qfd_su_cbuf_g.rdy -> qfd_rly_#_WE_#x#.a | TREE (direction) | 1 | 3 (2 F, 0 H) | 30 | 389.2 | 289.7 | 251.5 / 151.7 | -75.6 / None | relay x1 (1), replan (1) |
| sequencer | qfd_su_cbuf_g.rdy -> qfd_rly_#_SN_#x#.a | TREE (direction) | 1 | 1 (1 F, 0 H) | 10 | 380.5 | 289.7 | 251.5 / 151.7 | -69.0 / None | relay x1 (1) |
| crom | qfd_rly_#_SE_#x#.b -> qfd_su_cbuf_g.fq | TREE (direction) | 1 | 1 (1 F, 0 H) | 513 | 399.4 | 348.9 | 151.7 / 206.5 | -38.4 / None | relay x1 (1) |
| crom | qfd_crom_g.rq -> qfd_rly_#_WE_#x#.a | TREE (direction) | 1 | 1 (1 F, 0 H) | 513 | 390.7 | 347.6 | 207.5 / 151.7 | -32.8 / None | replan (1) |
| crom | qfd_crom_g.rq -> qfd_rly_#_WS_#x#.a | TREE (direction) | 1 | 1 (1 F, 0 H) | 513 | 390.6 | 347.6 | 207.5 / 151.7 | -32.7 / None | replan (1) |
| crom | qfd_rly_#_ES_#x#.b -> qfd_su_cbuf_g.fq | TREE (direction) | 1 | 1 (1 F, 0 H) | 513 | 386.6 | 348.9 | 151.7 / 206.5 | -28.6 / None | replan (1) |
| sequencer | qfd_rly_#_NE_#x#.b -> qfd_su_cbuf_g.ctl | TREE (direction) | 1 | 1 (1 F, 0 H) | 25 | 384.7 | 348.9 | 151.7 / 206.5 | -27.2 / None | replan (1) |
| sequencer | qfd_su_cbuf_g.rdy -> qfd_seq_su.cbr# | TREE (direction) | 1 | 2 (1 F, 0 H) | 20 | 317.1 | 289.7 | 251.5 / 151.7 | -20.8 / None | replan (1) |
| crom | qfd_rly_#_WN_#x#.b -> qfd_su_cbuf_g.fq | TREE (direction) | 1 | 1 (1 F, 0 H) | 513 | 352.3 | 348.9 | 151.7 / 206.5 | -2.6 / None | replan (1) |
| spine_local@kv | qkd_rly_#.b -> qkd_kvwq_ctl_bin.r# | TREE | 1 | 12 (0 F, 0 H) | 24 | 397.6 | 398.8 | 151.7 / 167.5 | 2.0 / None | - |
| spine_local@kv | qkd_kvwq_leaf_s_w#_m.dp -> qkd_kvwq_leaf_s_w#_m.dn | TREE | 2 | 112 (0 F, 0 H) | 224 | 319.6 | 325.4 | 196.5 / 239.5 | 4.4 / 201.7 | - |
| crom | qfd_su_cbuf_g.fa -> qfd_crom_g.ra | TREE (direction) | 2 | 4 (0 F, 0 H) | 824 | 151.4 | 164.5 | 251.5 / 246.8 | 10.0 / 132.8 | - |
| sequencer | qfd_seq_su.cbc# -> qfd_su_cbuf_g.ctl | TREE (direction) | 1 | 2 (0 F, 0 H) | 50 | 324.1 | 348.9 | 151.7 / 206.5 | 18.9 / None | - |
| crom | qfd_crom_g.rq -> qfd_rly_#_SN_#x#.a | TREE (direction) | 1 | 1 (0 F, 0 H) | 513 | 318.2 | 347.6 | 207.5 / 151.7 | 22.3 / None | - |
| corridor | qfd_cst_n.a -> qfd_rly_#_SN_#x#.a | TREE (prefix) | 1 | 336 (0 F, 0 H) | 149,184 | 410.6 | 440.1 | 197.2 / 151.7 | 22.4 / None | - |
| spine_local@kv | qkd_rly_#.b -> qkd_kvwq_leaf_s_w#_m.c | TREE | 1 | 12 (0 F, 0 H) | 3,516 | 427.4 | 466.7 | 151.7 / 177.0 | 29.8 / None | - |
| tree_block | qfd_rly_#_WS_#x#.b -> qfd_rly_#_NS_#x#.a | DEFAULT | 0 | 26 (0 F, 0 H) | 13,312 | 460.3 | 500.0 | None / None | 30.2 / None | - |
| corridor | qfd_cst_s.b -> qfd_rly_#_NS_#x#.a | TREE (prefix) | 1 | 336 (0 F, 0 H) | 149,184 | 412.8 | 458.6 | 183.1 / 151.7 | 34.8 / None | - |
| spine_local@kv | qkd_land.rs# -> qkd_rly_#.a | DEFAULT | 0 | 2 (0 F, 0 H) | 2,050 | 447.2 | 500.0 | None / None | 40.1 / None | - |
| corridor | qfd_chead_w.s -> qfd_rly_#_NS_#x#.a | TREE (prefix) | 1 | 24 (0 F, 0 H) | 10,656 | 408.5 | 462.7 | 180.0 / 151.7 | 41.2 / None | - |
| spine_local@kv | qkd_rly_#.b -> qkd_rly_#.a | DEFAULT | 0 | 249 (0 F, 0 H) | 53,539 | 444.3 | 500.0 | None / None | 42.3 / None | - |
| tree_spine | qfd_tt_up#.flt -> qfd_tt_ctlm.uf | TREE (direction) | 1 | 1 (0 F, 0 H) | 1 | 398.8 | 455.2 | 185.7 / 151.7 | 42.9 / None | - |
| corridor | qfd_chead_e.s -> qfd_rly_#_NS_#x#.a | TREE (prefix) | 1 | 24 (0 F, 0 H) | 10,656 | 408.5 | 465.6 | 177.8 / 151.7 | 43.4 / None | - |
| head_chain | qfd_chead_e.e -> qfd_chead_e.w | TREE (prefix) | 2 | 23 (0 F, 0 H) | 10,212 | 342.4 | 400.6 | 192.3 / 186.6 | 44.2 / 102.1 | - |
| spine_local@kv | qkd_rly_#.b -> qkd_land.rq# | DEFAULT | 0 | 2 (0 F, 0 H) | 32 | 441.0 | 500.0 | None / None | 44.8 / None | - |
| head_chain | qfd_chead_w.w -> qfd_chead_w.e | TREE (prefix) | 2 | 23 (0 F, 0 H) | 10,212 | 342.4 | 404.5 | 191.0 / 184.9 | 47.2 / 104.2 | - |
| sequencer | qfd_rly_#_EW_#x#.b -> qfd_su_cbuf_g.ctl | TREE (direction) | 1 | 5 (0 F, 0 H) | 125 | 286.7 | 348.9 | 151.7 / 206.5 | 47.3 / None | - |
| spine_local@kv | qkd_astk_n.lt -> qkd_rly_#.a | DEFAULT | 0 | 2 (0 F, 0 H) | 42 | 437.8 | 500.0 | None / None | 47.3 / None | - |
| spine_local@kv | qkd_rly_#.b -> qkd_land_n.lt | DEFAULT | 0 | 2 (0 F, 0 H) | 42 | 436.9 | 500.0 | None / None | 48.0 / None | - |
| spine_local@kv | qkd_astk.lt -> qkd_rly_#.a | DEFAULT | 0 | 2 (0 F, 0 H) | 42 | 433.5 | 500.0 | None / None | 50.5 / None | - |
| tree_block | qfd_rly_#_SE_#x#.b -> qfd_rly_#_NS_#x#.a | DEFAULT | 0 | 1 (0 F, 0 H) | 512 | 432.5 | 500.0 | None / None | 51.3 / None | - |
| tree_spine | qfd_rly_#_NS_#x#.b -> qfd_tt_up#.lf# | TREE (direction) | 1 | 1 (0 F, 0 H) | 1 | 355.1 | 424.3 | 151.7 / 209.2 | 52.6 / None | - |
| corridor | qfd_chead_e.n -> qfd_rly_#_SN_#x#.a | TREE (prefix) | 1 | 24 (0 F, 0 H) | 10,656 | 395.5 | 466.3 | 177.3 / 151.7 | 53.8 / None | - |
| io | qfd_io_xfifo.o_serdes_tx# -> qfd_rly_#_EW_#x#.a | DEFAULT | 0 | 2 (0 F, 0 H) | 2,048 | 427.2 | 500.0 | None / None | 55.3 / None | - |
| io | qfd_io_serdes.r -> qfd_rly_#_WE_#x#.a | DEFAULT | 0 | 2 (0 F, 0 H) | 2,048 | 426.3 | 500.0 | None / None | 56.0 / None | - |
| tree_block | qfd_tile_nk.n_y -> qfd_rly_#_NS_#x#.a | DEFAULT | 0 | 166 (0 F, 0 H) | 84,992 | 425.9 | 500.0 | None / None | 56.3 / None | - |
| io | qfd_io_xfifo.o_serdes_tx -> qfd_rly_#_WE_#x#.a | DEFAULT | 0 | 1 (0 F, 0 H) | 1,024 | 425.9 | 500.0 | None / None | 56.3 / None | - |
| corridor | qfd_chead_w.n -> qfd_rly_#_SN_#x#.a | TREE (prefix) | 1 | 24 (0 F, 0 H) | 10,656 | 395.5 | 470.7 | 173.9 / 151.7 | 57.2 / None | - |
| io | qfd_rly_#_WE_#x#.b -> qfd_io_xfifo.i_serdes_rx# | DEFAULT | 0 | 2 (0 F, 0 H) | 2,048 | 424.7 | 500.0 | None / None | 57.2 / None | - |
| sequencer | qfd_sp_su#_sfu.acc -> qfd_seq_su.acc | DEFAULT | 0 | 1 (0 F, 0 H) | 24 | 424.0 | 500.0 | None / None | 57.8 / None | - |
| tree_block | qfd_tile_nk.n_y -> qfd_rly_#_SN_#x#.a | DEFAULT | 0 | 183 (0 F, 0 H) | 93,696 | 421.9 | 500.0 | None / None | 59.4 / None | - |
| io | qfd_rly_#_EW_#x#.b -> qfd_io_xfifo.i_serdes_rx | DEFAULT | 0 | 1 (0 F, 0 H) | 1,024 | 420.3 | 500.0 | None / None | 60.6 / None | - |
| spine_local | qfd_rly_#_NS_#x#.b -> qfd_rly_#_NE_#x#.a | DEFAULT | 0 | 19 (0 F, 0 H) | 6,034 | 419.7 | 500.0 | None / None | 61.0 / None | - |
| tree_spine | qfd_rly_#_SN_#x#.b -> qfd_rly_#_SE_#x#.a | DEFAULT | 0 | 21 (0 F, 0 H) | 8,853 | 419.3 | 500.0 | None / None | 61.3 / None | - |
| spine_local | qfd_rly_#_SN_#x#.b -> qfd_rly_#_SW_#x#.a | DEFAULT | 0 | 15 (0 F, 0 H) | 4,911 | 419.3 | 500.0 | None / None | 61.3 / None | - |
| spine_local@kv | qkd_rly_#.b -> qkd_land_n.rq# | DEFAULT | 0 | 2 (0 F, 0 H) | 32 | 419.4 | 500.0 | None / None | 61.3 / None | - |
| sequencer | qfd_seq_su.cbc# -> qfd_rly_#_NW_#x#.a | DEFAULT | 0 | 1 (0 F, 0 H) | 25 | 417.4 | 500.0 | None / None | 62.8 / None | - |
| phy_dfi | qkd_ctrl.phy -> ot_hbm#e_phy.dfi | DEFAULT | 0 | 2 (0 F, 0 H) | 18,414 | 417.2 | 500.0 | None / None | 62.9 / None | - |
| phy_dfi | qkd_ctrl_n.phy -> ot_hbm#e_phy.dfi | DEFAULT | 0 | 2 (0 F, 0 H) | 18,414 | 417.2 | 500.0 | None / None | 62.9 / None | - |
