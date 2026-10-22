# RG-FFN (S81-RTLGAP, 10-21): TOK.DS.BENCH.4.2 FFN result transport XR / rstop safe redesign + import

Base: 72-frame MU die RTL claude/s81-die72-g3-1021@4ee613834.  New modules (same ports as the ones they replace):

- `ot_s81sl_rstopt` (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt.sv): the ring stop, rebuilt.  0 data cycles.
- `ot_s81sl_xgt` (ot_s81sl_xgt.sv): ot_s81sl_xg with u_r = ot_s81sl_rstopt.
- `ot_s81sl_xrt` / `ot_s81sl_xrt1` / `ot_s81sl_xrt3` (ot_s81sl_xrt.sv): XR7 + the FFN result transport (typed V row-pair
  send/receive + in-XR local copy, the codex 241f7b963 mechanism that was default-off `OT_S81SL_RD_PAIR`; now built in,
  send config body[44] = s_local) + the census repair.  0 data cycles vs XR7; transport edges = the 241f7b963 cut.

## Mapped native census (tools/ref_tile/native_census.py from origin/main; yosys synth + ORFS keep-regs hook, TT RVT)
census/census_summary.json:

| top | status | max loads | drivers > 32 | rst_n loads | area um2 |
|---|---|---|---|---|---|
| ot_s81sl_rstop (base) | FAIL | 2935 | 61 | 2507 | 7776 |
| ot_s81sl_rstopt | PASS | 32 | 0 | 10 | 6848 |
| ot_s81sl_xr1 (base XR7) | FAIL | 148 | 29 | 10 | 8648 |
| ot_s81sl_xrt1 | PASS | 32 | 0 | 16 | 9337 |
| ot_s81sl_xr3 (base XR7) | FAIL | 513 | 33 | 10 | 10362 |
| ot_s81sl_xrt3 | PASS | 32 | 0 | 16 | 10789 |

xrt1 area +688 um2 is mostly the local-copy word (bb2, 1,024 FF on C1, which had no B word); xrt3 +428.

## SAFE checklist (items this change touches)
1 Reset: rst_n drives only ot_rst_relay (2 sync + 1 kept leaf); leaves clear control/valid only (rstopt: 26 flops; data
  words unreset).  Release 3 edges after the port, as XR.  PASS.
3 Fanout: every driver <= 32 mapped loads (census PASS).  Pin-decided selects are decoded at the input and registered as
  kept one-hot copies on the input edge; early-known selects are kept copies of the next state; every copy group is fed
  by its own node (decode AND a kept split leaf), <= 30 copies per node, <= 30 b (15 b for hold enables) per copy.  PASS.
5 Storage: rstopt drops the 2 x 1,104-b own / asm capture registers (4-slot buffers are read directly); xrt adds bb2
  (1,024 b, C1) for the local copy.  No new flop arrays indexed at runtime beyond the existing 4-slot fragment buffers.
8 Schedule: 0 added data cycles on every existing path (line 2 edges/stop, V assembly, ci, own, NX, CTL, RD, lo, SO).
  Transport edges = component_receipt of 241f7b963 (lo -> V out 5, V in -> sw 6, local CI -> sw 3).  No credits.
2/4/6/7: not changed by this RTL (tile kits / die floorplan own them).

## Benches (Verilator 5.050, fleet; bench/)
- existing XR bench tb_s81sl_xr (tools/s81_slice/xr_bench.sh flow) on xrt1/xrt3: base PASS hb0/1 x seeds 1,2; mutants
  hops/row/porder/nocol/xhold (hb0) and bwide (hb1) FAIL as expected.  Stimulus constraint for the new legal program
  (bench/ub_xr_*/constraint.txt): random send configs keep body[44] = 0 and never form the pair mode (dir V only + kind
  RD); the random "ignored V kind" never draws RD (= a transport word now).  Transport is covered by the next bench.
- existing transport cut bench (codex/s81-rdpair-cut-1019 tools/s81_dv/layer_prog/rdpair, tb copy with xrt/rstopt):
  mut 0 PASS (exact ages, 4/2-pair bursts 256+128 pairs, local copy, reset abort), mutants 1..11 all FAIL.
- existing rstop_sid bench on rstopt: PASS 16 stops / 144 checks; tiercol mutant FAIL as expected.
- L0 MU per-layer bench (cut_7 L0, 63b8a0d5e flow, scripts/l0.sh): K_ctl (die72 base xr/rstop) and K_new (slice bound to
  xgt + xrt1/3) built on the fleet; results -> pending_results (S81-RTLGAP-ffn).
