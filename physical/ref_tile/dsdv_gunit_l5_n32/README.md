# dsdv_gunit_l5_n32 -- native-32 gunit L5 (S81-GUVE, 10-20, tree S81.STA.PAR.3)

Successor of dsdv_gunit_l5_ro3 (route dsdv_gunit_l5_ro3-ro3-648ee10c0 CLOSED TT +26.16 / FF +15.42 / DRC 0, but the
final audit FAILED: ep9 /srv/opentallas-scratch/claude/codex-s81-gunit-ro3-audit/{final_native_census.json,final_geometry.json};
ROOT 08:00 hold, no adoption of its LEF/Libs).  Same RTL/params/outline/macros/benches + NAT32 = 1 (0 edges added).

## Failure classification (ro3)
- PG 4558 unbound iterms: VDD/VSS of CTS clock buffers / delay buffers / wire repeaters that were dont_touch before the
  final global_connect (ODB-0383 "marked do not touch and will be skipped").  FLOW defect of the 10-19 tools, fixed on main
  (physical/common_flow/native_pg_binding.tcl / clk_net_protect pg_bound: PG bound before protection).  This kit gates on
  origin/main tools; the gate's PG audit decides.
- native census 621 non-clock roots > 32 (max 101), all in the tail (u_tail) or its reset roots:
  | class | roots | loads | fix (NAT32) |
  |---|---|---|---|
  | u_mul f12 l5 cut regs u_k1/u_k5 (r[96..99] 101, r[175] 73) + 11 flattened nets 34-54 | ~20 | 35-101 | ve-local ot_s81sl_ve_qmul (bit/cycle-exact f12 LAT 5, VE5 define; full ve native PASS max 32) |
  | u_add f12 l4 cut regs u_k3/u_k5 (esub b 47-60) | 6 | 35-60 | ve-local ot_s81sl_ve_qadd (f12 LAT 4) |
  | reset roots rr[9] / rr[12] (u_mul / u_add async clears) | 2 | 38-39 | ve units reset the valid only (5 / 4 loads) |
  | payload write gates wa / wd / we / wm (one gate per 16 bits) | 192 | 33-34 | one kept gate per byte |
  | Sinkhorn skf_add slice ab1 / ba1 shift amounts + swap | 241 | 33-62 | ot_skf_rsh: one-hot sliced shifter, kept 2-level decode (ot_skf_sdec) |
  | Sinkhorn quot g_shc sh copies (Q2 grid shift) | 179 | 33-64 | ot_skf_rsh per Q2 output slice |
  Every replacement is bit-identical (benches below) and adds no edge; the unit operands get a second kept same-edge copy
  (dsdv_gunit_operand_pin32 x 4: a2 / b2 feed only the units' alignment / normalise shifters).

## SAFE-DESIGN checklist (owner 10-19)
| # | item | result |
|---|---|---|
| 1 | pins registered, reset landing | PASS (source-registered, as ro3); rst_n 2-stage landing, ot_rst_region16 roots |
| 2 | reach <= 405 um | PASS: 388.8 x 302.4 tile, ro3 route reach 115 um; gate-measured |
| 3 | fanout <= 32 | FIXED: all 6 ro3 classes restructured (table above); the gate's pre-floorplan native census is the check |
| 4 | depth | unchanged boundaries (f12 cuts; Sinkhorn stage cuts); one-hot shifters are 2 AND-OR levels |
| 5 | storage > 2 kb | PASS: base table in 12 SRAM banks (ro3), no new flop arrays |
| 6 | floorplan | ro3 floorplan (12 macros on the 43.2 lattice, full std band, fill ~41% + NAT32 growth), gate-measured |
| 7 | clock | one region (tile < 1 mm, no crossings), centre root; ro3 spread TT 23.7 / FF 23.0; io_hold_margin 0.03 |
| 8 | schedule | PASS: 0 added edges (units same latency, copies same edge) |

Benches (Verilator 5.050, with GUNIT_NAT32=1 -DOT_S81_VE_LOADSAFE5 / -DOT_SKF_OH=1): gunit exact 8 cases, MUT 8 / 10;
Sinkhorn fs vs reference 300 cases, MUT 1 / MUTQ4.  Witnesses: results/rtl/s81_guve_gunit_1020.
