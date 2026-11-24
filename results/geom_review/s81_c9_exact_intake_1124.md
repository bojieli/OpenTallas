# S81 C9 exact plan geometry intake, November 24

Opened the whole-die core and wire views, dense crossing, clock-root and seam details for C9 model `048fa468f0a2` in E9 `s81-allfix-int/c9/p6w_c9_geom_model_t3_tap_1124.json`. The independent scan and viewed focus for t3, t22, t31, t34, t43, t71 and t72 show zero FT rectangle intersections with hard macros or declared probe blockages across 146,448 sites. The strips are visibly clear of the macro bodies. This is clearance evidence for the exact composed model. Full cut/channel G0 and PRE/bind remain separate release gates.

The overall model has 406 partitions and 403 types across a 32,970.24 × 25,980.48 µm die. The two main north-south wire trunks are still around x9–11 and x23–24 mm. The densest 100 µm bin carries about 3,879 bits at (9,950, 20,350). The densest edge is `svc_3/svc_3_att` with 9,656 bits across 1,512 µm. Model-listed lane legs have zero >405 µm, with 180 beyond 90% of reach (177 in c8). The center-check detects two pre-existing station centers inside macros. The undeclared one is `dn_s_0N_L2` in t6 at (10601.3, 17122.3). The other is a declared t1 station. Those findings are distinct from the per-bit FT site checks.

Recommended disposition is intake of this geometry model while the release hold remains. The view tests planned footprints and congestion patterns. The actual changed child placements, clock and reset implementation, and routing are pending.

- [Whole-die geometry](s81_c9_exact_1124/die_cores.png)
- [Modeled bit density](s81_c9_exact_1124/die_wire.png)
- [Exact FT seats in corrected types](s81_c9_exact_1124/c9_ft_sites.png)
- [Densest crossing](s81_c9_exact_1124/zoom_dense.png)
- [Densest seam](s81_c9_exact_1124/zoom_seam.png)
