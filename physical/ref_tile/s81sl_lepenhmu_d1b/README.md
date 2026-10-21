# s81sl_lepenhmu_d1b -- MU end-slice landed parent dsdv_slice_lepe_nh_mus, DIAGNOSTIC stand-in kit (DRIVE-S81-LEPENHMU 10-20)

Master: dsdv_slice_lepe_nh_mus (s_7S, E end, no host plane, MU twin of lepe_nh): slice | lep_mu_a + dsdv_mu_land | 2 x
dsfd_coll_lane_e_safe8_ntf. Top `ot_s81sl_slice_lepe_nh_mu_x_lp` (lp spec tools/landed_parent/specs/dsdv_slice_lepe_nh_mu.json;
record results/rtl/drive_s81_lepenhmu_1020/lp). Built by tools/s81_slice/mk_lepenhmu_kits.py (= mk_lepmu_kits lepemu recipe =
DRIVE-S81-LEPENH d3 recipe) with the REAL MU lane outline 725.76 x 583.2 + pin ranges (DRIVE-S81-NTF kit dscoll_lane_e_s8n @445e6c74c).
Outline 2764.8 x 5788.8 (lanes widen it from 2462.4). mu_rt kept as a K port (die master leaves it open).
**Not bindable, never submit**: slice / endpoint / lanes are STANDIN_NOT_A_VIEW; only dsdv_mu_land is a CLOSED view.
Strict bind (die_port_bind, fleet ep7, results/rtl/drive_s81_lepenhmu_1020/bind): landed + flat PASS, 0 tied/open/undriven/unread,
lanes bound to the real safe8_ntf RTL.

## Region plan (10-20 clock rule)
S = u_sl, K = u_lep + u_land + u_ln0/u_ln1. 3 crossings (line 1104 b each way, slice fault) land in fixed-latency rings (D 4 / E 2,
chunk 8, kept-enable, reset forest). RESCHEDULE: +3 edges each way on the off-die line hop, fault +2, reset +4.
Parent flops: landing 16,862, reset 577, out_regs 2 (lp audit PASS).

## SAFE checklist (parent level)
1 Pins PASS: children register their pins; reset root + 2 K fault out_regs.
2 Reach: line ports bit-aligned across the 172.8-um channel; lanes 43.2 um E of the endpoint, stacked about its window
  (lane0 y 2289.6, lane1 y 2894.4), parent rx/tx pins on the lane rows. OPEN (gate measures): mu_rc E pin (y 3570) -> land rc corner
  (x ~1470, y 3197) ~1.3 mm; endpoint fault -> E pin y 2266 ~0.9 mm (out_regs 2); ck_S root E -> slice.
3 Fanout: in-gate native census decides (same lp generator / chunk 8 as lepe_mu: census PASS max 32).
4 Depth PASS. 5 Storage WAIVED for the rings (landing contract D=4).
6 Floorplan: children on the 43.2 lattice; aspect 2.09 WAIVED (die slice column); std-cell band = channel + free area.
7 Clock: regional roots ck_S / ck_K, landed crossings; spread <=80 TT/FF within each region; hold margin 0.03.
8 Schedule PASS: static, offsets in the lp record.
Variant b: port-flop anchors kept, CTS 24 sinks / 30 um / 15-um buffers / -balance_levels.
