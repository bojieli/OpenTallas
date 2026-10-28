# DRT-TRIAL-1 (METHODOLOGY 12.15e): detailed-route trial per die. ESTIMATE run, not a gate.

Lane file: ~/coord/lanes/DRT-TRIAL.md. Numbers are CHECKED-own (read back from the run logs/reports kept here) unless marked UNCHECKED; not yet NUMBER-CHECKed independently.

## HEAD (s81_head part map, DIE-HEAD-3 22:5x, claude/die-head-1027@20dc2e91f1)
Region = partition hd_tile (ot_s81hd_tile_p, 708.48 x 1036.8 um; 264 of 326 partitions; 4 elemA + 1 elemB SIGNED clockfreeze views from
results/die_head_1027/views). Flow = shared `tools/die_plan/gen.py phys --types hd_tile --trial` kit + `run_kit.sh route` (ORFS image
openroad/orfs:asap7lock, ot-run intel2, 16 threads). Run dir intel2:/srv/opentallas-scratch2/claude/drt-trial-1/head/kits/hd_tile.

Trial-local deviations (each one is a finding; plan files untouched; edits in kit_trial_edits/):
1. plan schema: `partition_types.*.clock.note` is rejected by gen phys -> stripped.
2. landed tile: gen phys sdc_lint FAIL (`create_generated_clock fclk_out_o -source [get_ports clk_t3]`, no such port) -> edge_clocks/landing_contract dropped (no ring in the trial tile).
3. no plan pin sites for the 18 ID strap bits (strap_row0[16:0], strap_ten) and no straps.json -> port_bind FAIL extra 18 -> 18 M7 pins added at y 4.32.
4. plan hard_cores point at OLD closed views (317.672 / 277.652) -> replaced by the SIGNED views (319.68 / 285.12); signed clock pin ft_mstrap_i renamed clk in the copy (geometry unchanged); 8 die-owned ft_* pins left open.
5. reset: pre-CTS reset-leaf gate FAIL (single in_site (531.872, 4.32), 646.5 um to the W-face regs, limit 405) -> reach 800.
6. FF structural hold gate FAIL wns -875.41 ps / 2,606 endpoints -> made non-blocking, SKIP_INCREMENTAL_REPAIR=1 (timing of this run not usable).

Results:
- synth: 51,414 cells (25,051 clock sinks), placed 98,698 instances (34,959 fixed), util 70 % (cores).
- GRT (with clock, after CTS): overflow 0 on every layer; usage M2 11.67 / M3 7.61 / M4 5.21 / M5 2.43 / M6 4.11 / M7 1.12 % (total 5.00 %); 6:26 wall, 7.3 GB.
- Pin access: stdCellPinNoAp 0 of 151,645 pins; macroNoAp 0 (7,649 macro access points generated) -> 0 pin-access failures.
- DRT: iter0 15,920 -> 918 -> 361 -> 12 -> ... -> 5 after 49 iterations; final 5 DRC, all `Short` on M6, net rst_n_t5..t9 (one per core: the core rst_n pin) vs VDD. 58:30 wall, 13.1 GB peak, 16 threads. Wirelength 1.373 m (M2 480k / M3 382k / M4 201k / M5 84k / M6 158k / M7 67k um).
- Root cause of the 5 shorts (odb query q_pg.tcl): the tile M6 PG grid runs VDD/VSS straps 0.288 um wide at a 4.32-um pitch over the cores (238 per net). The core rst_n pin is a 0.192-um M5 island pin (elemA (159.744, 157.584) core frame, elemB (142.464, 140.304)); in place (eA0 MX) it lands at y 170.580-170.772, under the VDD strap at 170.688-170.976, so the only access (M6->M5 via) shorts VDD. The clock pin (168.420-168.612) sits in the strap gap and routes clean. Same for all 5 instances (R0, MX, MY, R180) -> systematic, not congestion.
- Clock NDR/shield: the tile kit routes its CTS tree without an NDR (none defined) -> 0 NDR violations by construction, NDR untested here. No clock net in the DRC list.
- vs die GRT0 (planned views, part map grt_TT.txt): die GRT used the die_trial abstract of ot_s81hd_tile_p: M1-M3 full OBS, M4-M7 OBS only over the 5 core outlines (= signed outlines, match), M4-M7 adjustment 0.75; overflow 0. The abstract has 1,138 pins (566 i M4/M6 + 566 o + clk, arst_n, start_i, fclk_in_i); the real kit has 1,161 (no fclk ring in the trial; +18 straps; +rst_o_0..3/start_o_0..3). The tile kit itself reserves no M4-M7 tracks for die nets over the tile glue (UNCHECKED whether any die net routes over hd_tile in the die GRT).

## KV (H200B on plan pd9b/hm_r26q9b.json dae191169d57) -- NOT RUN
gen phys --trial fails on every hard-core partition type tried (kv/phys_*.log): unbound buses (open input/output) because q9b partitions
have no binder kit RTL (--kit-rtl), and all 1,627 hard_cores carry no lef/lib (H200B die GRT0 = planned abstracts only).
Real views available: kv3_pv_pair, kv3_head_eighth_e0..e7, ot_qwen_tp8_pv_join_t. Best region: kv3_pv_v1n (20/20 real).

## S81 (plan die-s81-3/die_plan_r98.json 06301f33d226, code main f1e2bcf90e) -- RUNNING at park
Region = col_h9_r1__t1__cl49d7a23e (54 instances, 1442.88 x 1226.88, 73/73 hard cores with real LEF: 35 ROM4096x72 generated macros +
38 closed views, all verdict PASS). Kit intel2:/srv/opentallas-scratch2/claude/drt-trial-1/s81/kits/col_h9_r1__t1__cl49d7a23e.
Trial-local: 4 OT_RESET_CORE equal-depth checks (u_r1.u_e5/e6/e7/e9 rst_n: 'existing reset is not an equal-depth relay copy') made non-fatal.
