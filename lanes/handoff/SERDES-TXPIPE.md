# SERDES-TXPIPE handoff (S81 serdes TX/RX pipe stage), 2026-11-14

## Problem (t14 wave route 4837cfb49ca5, epyc2, 4_cts_final.rpt + 4_cts.odb query)
- TX setup: u_txl.q[239] -> u_ptx/d[239] -718.9 (CTS), -454.9 after GRT repair, 340 endpoints. The PMA TX d face is the
  bottom edge of u_ptx (y 1093, x 244-2491), behind u_prx (y 951-1081, 11.9 um gap, all in halo). The encoder p_d flops sit at
  x 1478-2522 / y 607-941; GPL left the u_txl rows near the encoder (q[0] at (987,713) for pin x 264; q[239] at (2145,798) for
  pin x 1239), so one hop carries the 1.2-2.1 mm to the pin.
- RX setup: u_dec.u_face_p_d.q[538] -> u_syn.am_ok -351 (FA cone + ~400 ps wire + 160 ps rck skew). The face pads already sit
  AT the PMA q pins (y 946); the syn cone sits at x 621-2362 / y 164-943 (am_ok at (2006,892)).
- HOLD (not pipeline class, for the clock owner): u_enc.d4[355]->d5[355] -200 (clk_t23 leaf skew 229 vs 478);
  u_prx -> u_face_p_d.q[0] -209 (io_pma_rck insertion 2175 ps at face flops).

## Change (branch claude/serdes-txpipe-1114, clone intel2 ~/wt/serdes-txpipe-1114)
- rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv: `OT_S81_SERDES_TXPIPE` = u_txl +1 row (545 bits incl d_v); TX +1 clk.
  `OT_S81_SERDES_RXPIPE` = u_rxf pma_rck row (544 data + p_v=rn_r piped together) before u_dec; RX +1 rck. Default = unchanged.
- tools/die_plan/txl_mid.tcl: OT_TXL_MID_FACE=1 face mode (row next to a hard-macro pin sits at that pin; other rows even).
- tools/die_plan/gen_phys.py: txl_mid_exports turns the hook on from the type defines (chains u_txl u_rxf u_dec.u_face_p_d,
  FACE=1); no env needed.
- tests: test_txl_mid.py (+4), test_txl_mid_exports.py (+2): 19 pass.

## Plan (DIE-S81-92, serdes event B3z2s 61b772e20b3a)
- ASK sent: every serdes__t* type verilog_defines += OT_S81_SERDES_TXPIPE, OT_S81_SERDES_RXPIPE. No lane table change
  (stages are inside the column; LATCHECK counts u_bout/u_bin/pads/ist/ft/landing only).

## Proof
- epyc10 /srv/opentallas-scratch2/claude/serdes-txpipe/bench: eq.sh (yosys default-define equivalence vs main), bench_all.sh
  (Verilator 5.032 docker: rlat base/tx/rx/both, mutants, two-die col, rst_tree lock-step).
- t14 kit: epyc7 /srv/opentallas-scratch2/claude/serdes-txpipe/t14gen.sh (B3x2b bind + overlay + plan defines), log intel2
  ~/serdes-txpipe-t14-gen.log; route via run_kit.sh (route 80 GB, --hosts epyc7,epyc8,epyc9,epyc10,intel2).

## Status
- (updated below)
