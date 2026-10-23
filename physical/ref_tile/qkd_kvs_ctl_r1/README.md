# qkd_kvs_ctl_r1 (KDIE5-TV 10-22) -- release KV die qkd_kvs_ctl at the relm frame

KDIE5-TV 10-22 (STEWARD-QKc decision b): die-bindable kit of the release KV die qkd_kvs_ctl (relm f9b69ebb3; module text _k_mu_ba == _n32_pj, no RTL change) at the relm frame 1123.176 x 172.776.  W / E faces carry 2524 pins each on 172.776 um: M4 + pin-only M6 contacts (grant = pin density, not growth: outline and M5 cap unchanged).  Face / bit order = the frame; ck / rst_n (frame M8 interior drop at x 552) + por_n (unconnected on the relm die!) + kg (unread) on N at x ~552.  Pin registers off (die charges 0 face edges); 2-stage reset landing + kept copies, clock spine as the c32k gate (WARN, spread 29.8 / 25.8 ps).

**M6 grant = pin density, not growth.** W and E each carry 2524 pins (o_hroot_*S / *N 2 x 1118 + i_hroot 2 x 144) on a
172.776-um face: 14.6 pins/um on M4 alone exceeds the 12 b/um/layer FLOORPLAN_MARGIN limit (a 2-track M4 face holds 1800).
The pins alternate between 2-track M4 and 2-track M6 slots (2166 M6 contacts per kit, 0.384 um deep, PORT-only;
m6_pin_access stubs) = 7.3 pins/um/layer.  Outline, signal cap M5 and PG M5 are the frame's / the contract's.

SAFE checklist (pre-gate):
1 Pins: frame faces and bit order kept; pin registers OFF (the die static schedule charges 0 face edges; kv_tile_views
  refuses a view that adds them); reset landing 2 stages + kept copies (startup only, <= FACE_LAND_RST_BUDGET).
2 Reach: 1123-um wide tile; o_hroot W/E buses are member output flops (RTL); the gate textbook wire_reach decides.
3 Fanout: native census at the gate.  4 Depth: unchanged RTL.  5 Storage: flop tables (no macros in this RTL).
6 Floorplan: 6.5:1 frame (die slot, frozen); N 1.7 / S 0.1 pins/um; W/E 7.3 / um / layer with M6.
7 Clock: spine (c32k settings); pin-flop spread <= 80 TT+FF checked at the gate.  8 Schedule: static, +0 cycles.
Benches: kvs_tile_bench at the relm design point (tools/qwen_kv_die/kvs_tile_bench_relm.sh; the bench's kit tile text ==
the release module, checked): m0 PASS, m1 / m2 FAIL; m3 (child removed) is NOT detected by this bench (recorded, not used).
