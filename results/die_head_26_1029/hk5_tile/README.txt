DIE-HEAD-26 2026-10-29 07:40 PDT: plan delta hk5_tile = GEOM-55 FAIL fix V1 (fix-only delta admitted on the HEAD freeze of hk4, COORD 07:3x).
Input main results/die_head_21_1028/hk4/plan_spine_raw_rx_tx.json.gz (gunzip = plan_hk4_rx_tx.json). Script hk5_tile_pins.py (deterministic,
asserts the old geometry before every move). Output plan_hk5_tile.json(.gz); core_pins -> hk4/core_pins (relative hard-core pin paths).

PROBLEM (GEOM-55, epyc2 geom55-probe/walk.tsv): hd_tile i[564:0] pins on the W face at y 354-654 sit in the 17.28-um street between the die
edge and elemA eA2 (x 17.28-337, y 380-700); the CA landing ring is at y 706-788 (x 17-117), so all 565 bits run >150 um to their first
landing gate, 97 >405.
ESTIMATE V2 (ring at the pin column, kit-only): the ring is 16,109 cells / 2,128 um2 (2,949 flops; hold_mux D=4) [CHECKED own, 3_place.odb];
the only space beside the pins is the 17.28 x 300 um street (5,184 um2 incl. tapcells/PG) -> 41 % raw cell util in a 17-um strip that
must also carry 565 inputs + the ring's 565+ outputs around eA2 -> INFEASIBLE without moving a hard core (the cores fill the tile width
17.28+319.68+34.56+319.68+17.28 = 708.48). Not built.
V1 (built): move the i (W) / o (E) windows to y 708.48-1008.512 (free W band x 0-216 beside elemB, free E band x 501-708), i.e. onto the
ring. Tile->tile abutment keeps one window for i and o. Chain ends move with it, with NO added stations/cycles:
  hd_spn + hd_spn_end xw_o/xe_o 1391.04-1691.072 -> 1745.28-2045.312, bw_i/be_i 354.24-654.272 -> 708.48-1008.512 (spine frame)
  hd_spn_{e,w}shim_{tx,rx}: both slot windows -> 708.48-1008.512 (straight channel kept), outline height 682.56 -> 1036.8 (tile height)
  hd_turn_a: tile-side window -> 708.48-1008.512, outline 172.8x673.92 -> 172.8x1036.8 (S face unchanged)
  hd_turn_b: tile-side window (own frame, origin +336.96) 17.28-317.312 -> 371.52-671.552 (fits 699.84)
  277 ports carrying die-frame windows moved +354.24.
  (A first try that moved only the tile-facing shim windows gave an in-shim jog: G0 hops 449/527 um > 405 = extra stations = cycles,
   rejected; spine-side move instead.)
G0 PASS 0 errors / 14 warnings and G0C --completeness PASS 0 errors / 14 warnings, 21/21 types clean (hk4 baseline: G0 PASS 14 warnings);
worst cut 0.0578, worst partition segment 0.3587 (CHECKED own, g0/ g0c/). Render g0/die_plan.png viewed (tile/shim/spine pin bars in the
upper band of each tile row, shims full row height, no overlaps).
CLOCK rerun with the same config (head_hk4.yaml, plan -> hk5_tile; clk/head_hk5_tile.yaml): 719 taps (plan density taps follow the moved
windows: spines 34->31, turn_a 2->3, turn_b 2->1), GRT0 incl clock overflow 0 TT+FF, duty 0/719 outside 45-55, MPW 0, spread x1.05
75.8/62.3, spread incl OCV+droop shared 90.7 / 79.2, stated bound 105.7/92.3 -> clock check PASS on hk5_tile (CHECKED own).
KITS that change: hd_tile (pins + CA ring placement: kit regen + PLACE), hd_spn, hd_spn_end, 4 shims, hd_turn_a, hd_turn_b (pin/outline).
