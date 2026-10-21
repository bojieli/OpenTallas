# hbm_sfucore_k9z -- SFU core with per-lane clock/reset entries at each lane child (HBM-COLLECT10/SFUC, 2026-10-21)

Parallel pair: **k9z** (MAIN: column-lane entries at the clk pin y, straight 259 um over the child) and **k9za**
(FALLBACK: column-lane entries in the row gap below each child, ~320 um around it). Child orientations = k9y in both (y-flips refused by gen: 928 child pins off-track). First to close binds.

## Classification of the k9y failure (hbm_sfucore_k9y-y1-d285e0902, PREROUTE_MARGIN reg2reg -18,510.9 ps)
Read from the run (ot-epyc7 .../routes/hbm_sfucore_k9y_y1_d285e0902/work/orfs/reports/.../3_detailed_place.rpt):
NOT an arithmetic cone and NOT the SDC period (833.333 ps, one core domain; all 44 entries same-domain). Every worst
path starts at a lane child (g_lane[k].u_sfu, ot_su12_sfu) whose clock arrives late through an UNBUFFERED entry wire:
hard-child clk entries are direct port->pin wires (ot_ce_require_wire; not CTS roots), and the 16 clk_lane ports sat
in index order on the W face (y 99.9 + 113.4 k) while the lane children ring all four faces. Entry wire load grows
61 fF (lane 0) -> 558 fF (lane 15): clk_lane[15] slew 54,715 ps, arrival 17,261 ps at g_lane[15].u_sfu/clk, so
launch = 17.26 ns + 0.48 ns child clk->Q + a few buffers -> -18.5 ns. clk_lane[3] arrives 3.1 ns, [8] 10.8 ns.
clk_map / rst_lane_n / rst_map_n had the same W-face index-order plan (clk_map CTS trunks up to ~3 mm).

## Fix (structural, port spelling only)
- Top **ot_hgi_sfu_core_split3l** (rtl/hbm_accel/generic/peers/ot_hgi_sfu_core_split3l.sv): pure port wrapper of
  ot_hgi_sfu_core_split3; the four 16-bit lane entry buses become 64 scalar ports <bus>_<lane>
  (clk_lane_k, clk_map_k, rst_lane_n_k, rst_map_n_k), so each can be ranged individually. No logic, **0 added cycles**.
- Each lane's 4 entries sit in the face channel next to its child's clk pin (child clk pin = W edge, 45.95 um from
  the child's bottom in R0): S row 12-15 and lanes 0/8 on S (~89 um), W/E column lanes at the clk pin y (259 um straight, over the child),
  N row on N (343 um).
- Die port change: sfucore_<q> master = ot_hgi_sfu_core_split3l; the die connects clk_lane[k] -> clk_lane_k etc.
  (same nets, same timing), every other port identical to split3.

## Safe-design checklist
1 Pins: unchanged from k9y (pin regs on, reset 2-stage face landing) -- PASS.
2 Reach: lane clock entry wires <= ~343 um (both) instead of up to ~3.1 mm -- FIXED. Tree source
  ~490 um/segment and bridge chains remain k9y's recorded waivers.
3 Fanout: unchanged (k9y native census; kept copies) -- as k9y.
4 Depth: textbook 643.5 ps / 17 lv (u_memory wpipe -> wcoll_q), guidance only (rule freeze 10-20) -- as k9y.
5 Storage: k9y waiver (bridge 65-deep delay chains in flops; k9x SRAM rings are the successor) -- waived.
6 Floorplan: k9y outline 1900.8 sq, macros on lattice; only lane entry pins move -- PASS.
7 Clock: hard-child entries now short direct wires (the CE policy compensates the measured wire); io_hold_margin 0.03.
8 Schedule: 0 cycles added; compiler SFU_LG_PATH calendar unchanged.

Benches: split_equiv r23 + the k9y mutants on split3l (CORE3L=1, Verilator 5.050), witnesses in
results/rtl/collect10_sfuc_1021/bench_witness/.
