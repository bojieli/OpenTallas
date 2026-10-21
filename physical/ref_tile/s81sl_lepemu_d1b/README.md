# s81sl_lepemu_d1b -- MU end-slice landed parent, DIAGNOSTIC stand-in kit (DRIVE-S81-SLICEP 10-20)

Master: dsdv_slice_lepe_mu (s_7N, E end, host plane): slice | lep_mu_h + dsdv_mu_land | 2 x dsfd_coll_lane_e_ntf. Top `ot_s81sl_slice_lepe_mu_x_lp` (lp.py spec tools/landed_parent/specs/dsdv_slice_lepe_mu.json; record
results/rtl/drive_s81_slicep_1020/lp). Built by tools/s81_slice/mk_lepmu_kits.py from the DRIVE-S81-LEPENH s81sl_lepenh_d3b recipe.
**Not bindable, never submit**: slice / endpoint / lanes are STANDIN_NOT_A_VIEW; only dsdv_mu_land is a CLOSED view (dsdv_mu_land-263e13fc3).
Strict bind (die_port_bind, fleet ep7): landed + flat tops PASS, 0 tied / open / undriven / unread.

## Region plan (10-20 clock rule)
S = u_sl (slice; its own internal regions when hardened, PL-SLICE c1x), K = u_lep + u_land + u_ln0/u_ln1. Exactly 3 crossings
(slice->lep line 1104 b, lep->slice line 1104 b, slice fault) land in fixed-latency rings (D 4 / E 2, 8-b chunks, kept-enable
writers, per-chunk reset forest); no direct reg->reg path between ck_S and ck_K. Loop -> RESCHEDULE: +3 edges each way on the
off-die line hop (elastic at the d2d link), fault +2 (out_regs), reset +4. Parent flops: landing 16,862, reset 577, out_regs 2.

## SAFE checklist (parent level)
1 Pins PASS: children register their pins; parent ports = abutment hops; reset root + 2 K fault out_regs.
2 Reach: line ports bit-aligned across the 172.8-um channel. OPEN (gate measures): mu_rc -> land rc ~1000 um (land R0: its rc corner faces the channel; an MY flip puts its 1112 pins off-track = ref_tile macro_grid FAIL); host plane (t_host/t_kd/f_*) E-face y 1700-2420 -> lep S face ~650 um. Fix if the gate names them.
3 Fanout: the gate's mandatory post-synthesis native census decides (refuses before layout); same lp landing generator / chunk 8 as lepe_nh d2 (census PASS max 32, 75,363 roots).
4 Depth PASS (ring write + one read stage per chunk). 5 Storage WAIVED for the rings (landing contract D=4); land storage = SRAM macros inside its view.
6 Floorplan: children on the 43.2 lattice; aspect 2.35 WAIVED (die slice column); std-cell band = channel + free area around lep/land.
7 Clock: regional roots ck_S / ck_K, landed crossings; spread <=80 TT/FF judged within each region; hold margin 0.03.
8 Schedule PASS: static, offsets in the lp record.
Variant b: anchors kept, CTS 24 sinks / 30 um / 15-um buffers / -balance_levels.
