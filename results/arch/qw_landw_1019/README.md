# QW-LANDW 10-19: wide D8 hop-0 landing masters (Q.STA.LAND600.3 wide lanes)

Owner: Claude QW-LANDW (LEAD3-QW). Pattern = QW-LAND8 (rtl/qwen_split/qfd_land8.sv, CLOSED d8/d8n W1/3/10/32).
Lanes: 107 b (slice ss status) and 116 b, 453 / 520 / 548 b (slice <-> slice rows of the qw_dieclk2 landing_list).

| lane | storage (8 slots) | masters (main ICG / fallback no ICG) | tile um |
|---|---|---|---|
| 107 | 856 b flop ring (< 2 kb) | qfd_landh0d8_107_EW_44x44 / qfd_landh0d8n_107_EW_44x44 | 44.28 sq |
| 116 | 928 b flop ring | qfd_landh0d8_116_EW_46x46 / qfd_landh0d8n_116_EW_46x46 | 46.44 sq |
| 453 | 3.6 kb SRAM record = 3 x d8s_151 | qfd_landh0d8s_151_EW_98x171 / qfd_landh0d8sn_151_* | 98.28 x 170.64 each |
| 520 | 4.2 kb = d8s_174 + 2 x d8s_173 | qfd_landh0d8s_17{4,3}_* / d8sn_* | same |
| 548 | 4.4 kb = 2 x d8s_183 + d8s_182 | qfd_landh0d8s_18{3,2}_* / d8sn_* | same |

SRAM slice (rtl/qwen_split/qfd_land8s.sv): 3 dual-clock ot_sram_1r1w2c_32x64_m1 banks (write port on the ring write
clock, registered read on the receiving root) at (43.2, 43.2 / 86.4 / 129.6) on the 43.2-um lattice; 3 macros per tile
(a 9-macro single tile is lattice/channel-bound at 13 % fill -> fill FAIL without a ROOT exception; three slice tiles
need none). Lane bits split as listed, so the die ties no data pin.

## Calendar and price (die strap K, four tie straps k0..k3)
- Flop (107/116): the D8 calendar unchanged: K = (L + G - R0 - 1) mod 16, write -> read age (L - 1) T + phi in
  [1.25 T, 4.125 T]; same release edges as d8 (en +2 source, rs +2 receiver).
- SRAM slices: K = (L + G - R0 - 2) mod 16, macro write -> read age (L - 3) T + phi in [1.25 T, 4.125 T].
  PRICE: +2 receiver edges per crossing vs the flop D8 (a pin register before the macro write, a registered macro read
  before the output register): min L = 5 at phi ~ 0 (flop D8: 3). Output 0 until R0 + 4 + K. All slices of one lane
  take the same K and release together (same en / rs nets). Static, no backpressure.
- The macro has no wclk -> rd_out arc: the write -> read age is guaranteed by the calendar (bench), not by STA. The only
  timed crossing is the slot-valid mask (vld on ck_s -> use on ck) under land8_clocks.tcl (2T check, 1.25T - 210 ps).

## Evidence
- Benches: tools/qwen_split/bench_land8w.sh (72 lanes, K 0..15, 8 phases, 3 release orders, restarts, x-initial unique,
  SRAM power-up random via OT_MEM_NO_INIT), Verilator 5.050 fleet; witnesses in bench/.
- Native receipt of the 8 CLOSED d8 views: native_receipts_d8.json (en capture 36.7..55.3 ps < 190).
