# INTENT SLICE-C-SRING (CPL-S81-SLICE-3, DO_NOT_COUNT) - dsdv_slice c1x_C t1/t3/t5/t7, lepw_mu_C__t1, lepw_mus_C__t1

Base BASE_1200 b5faa1ba (slice types equal 99f40d35). Positions only; no RTL, no re-pin, same masters/orients.

## Diagnosis (measured, not assumed)
- route_supply.py models hard_cores only (macro_rects reads t["hard_cores"]); contents[] SRAM/ROM banks are invisible to it.
  CPL-S81-LEAF-3's slicec form (12 content macros moved, verified applied) scores t1 2.923 -> 2.923: the
  "open u_xr N street by moving the bank column" form cannot move the S2 metric.
- The measured hot spot is the S-face landing ring (ring_H p99 2.923 at (351,27), t1): u_cap and u_xr sit 34.56 um
  above the S edge, so the leafup_i2/i3/i4 + leafdn landing bands (y 17-28) have one 34.56 strip under M1-M5 macros.
  Second hot spot: the E (t3/t7/lepw) or W (t5) xring_i* landing band is a 21.6-um sliver along the face (ring_V 1.74).

## Dataflow chain
S face leafup_i* (in) -> S landing ring -> u_xr.e_c (leaf up) -> content banks (g_bank g_mac/g_ex/ROM, p2p 2817 b in /
1240 b out) -> u_xf finish row (cp0..3, u_f) -> N face; u_cap cw_s_a/cw_n_a -> leafdn_o* stations -> S/N faces;
xring_i*/o* W/E faces land in their bands next to the face.

## Hand form
1. u_cap (34.56,34.56) -> (120.96,103.68); u_xr (388.8,34.56) -> (561.6,172.8). Both lift off the S ring
   (>=103 um strip) and cap leaves 86 um at the W face; cap|xr street widens 17.28 -> 103.68 um.
2. The bank rows that the lifted cap now covers re-site (legal.py, nearest legal site, gap >= 34.56 to all, y >= 371.52,
   x >= 120.96: out of the S/W ring strips and the cap|xr street) into the open middle directly over u_xr's N face,
   so the xr<->bank bus is short and goes N, not through the cap|xr sliver.
3. Landing bands: xring_i0 (t3/t7/lepw_mu/lepw_mus) widened inward to [1252.8,17.28,1425.6,257.244];
   t5 xring_i1 -> [17.28,380.16,86.4,552.96] (left of the lifted cap). Same face edge, same window.

## FIN7 (final candidate, 11-11 07:1x PST)
- Positions: c1x_C t5/t7, lepw_mu_C, lepw_mus_C: cap (120.96,103.68), xr (561.6,172.8); t3: cap (120.96,95.04), xr (561.6,172.8);
  t1: cap (95.04,103.68), xr (483.84,138.24) (t1 cap stays nearer W: leafdn_o2 1-reg chain must still close at <=405).
- Content movers (legal.py, KEEPOUT = u_xr north street, COORD 06:4x): every content that the moved cores now cover, plus any
  content inside the xr N street (xr x-span +-34.56, y to 734.4), goes to the nearest legal site outside it (east of x~800 or bank top).
  0 contents in the xr N street on all six types.
- Bands: xring_i0 widened inward to x 1252.8 at the same face edge and window y-span (t3/t7/lepw_mu/lepw_mus);
  t5 xring_i1 -> [17.28,380.16,86.4,552.96].
- Derived: internal_stations endpoints follow their core rigidly; blocked regs moved to the nearest free point (Manhattan hop <=405
  by my count); added taps re-sited (t1 clk_t36/clk_t43, t3 clk_t28/42, lepw_mu clk_t35, ...), kit tap rule passes.
