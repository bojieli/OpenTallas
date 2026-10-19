# hbm_hc_root_d4g_xr3 (L2H-HC 10-19, H.STA.BLK.1)

Successor of hbm_hc_root_d4g_xr (route r1-88f1fa301 NEEDS_HUMAN: macro_place 'expected 1 macros, netlist has 2').
The root has two ot_sram_1r1w_1024x256_m2_r2c2: u_tbl (bases/scales) and u_seq.u_program (event programme).
Geometry (PARALLEL variant of xr2): stacked centre column, programme (237.6,216), table (237.6,388.8) R0; both W/E pin faces open onto >=237 um of cells.
RTL change (shared by xr2/xr3): ot_rst_relay REGIONS 2->8, eight kept reset cohorts (pin/tgt/seq/dn/core/mix/tbl/tail) instead of rn[0] for everything; same release edge.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS - every pin is a flop in RTL (pin_regs opt-out reason in spec); reset = ot_rst_relay 2 sync + 1 tree stage, now 8 kept regional copies (fixed).
2 Reach: 648 um tile, macros inside; gate netlist lint (>500 um/stage) decides; no die-level wire in the tile.
3 Fanout: reset fixed (8 cohorts). Mix 768-bit 8-way select / 3,072 emit enables: measured by the --cts gate; if flagged -> RTL successor (see 5).
4 Depth: measured by the --cts gate worst-path classes (TT 833 ps sign-off).
5 Storage: WAIVED-with-reason for this kit: the 6,144-bit mix flop store stays (moving it to SRAM re-times HC_MIX/RAW0 and needs a compiler/bench change); both 1024x256 stores are SRAM. SRAM mix store = next successor if this gate/route misses.
6 Floorplan: macros on the 43.2 um lattice, W/E pin-face halo 10.8 um (native 57 contacts/5.4 um faces), 5.4 um N/S; outline 648x648 = die slot (exact), aspect 1:1, one full std-cell band; util ~38% (slot-bound).
7 Clock: one root over 648 um (clock_span WARN); gate measures pin-flop spread <=80 TT+FF; io_hold_margin 0.03.
8 Schedule: static; no cycle added (reset release unchanged, XRD/XRU params as xr; re-derive with the current centre contract, H.STA.WIRE.8).
