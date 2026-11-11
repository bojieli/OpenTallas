# INTENT SHEET SLICE-C (CPL-S81-SLICE, plan 99f40d35071d)

Delta: `delta_SLICE-C_99f40d35.json` sha256 `6464cdede16922e8fd2f136dc19d55f46866a0570b9aad283d9c0e2d1a2892e8`; adopted types 12/16.

**Dataflow (bound netlist + LEF directions + plan buses/stations).** Ring side: leafup_i* face windows (279-668 b each,
the farthest one staged) -> u_xr (xrt ring core) <-> the slice content macros (2707 b in / 1240 b out, p2p) -> u_xr broadcasts
151 b to every leafdn_o* window and 312 b to u_cap (capc5r).  ret_i* windows -> u_cap.  u_eg.u_nh / u_eg.u_nk (egn) and
u_eg.u_gg (egg) sit one stage behind cap/xr.  Finish side: u_xf.g_cp[0..3].u_e (eng_finish) form a serial chain
(131 b per neighbour, 190-um pitch) closed by u_xf.u_f (norm_finish, 123 b).  Roles: face->xr and xr<->macros p2p;
xr->leafdn/cap broadcast; finish chain p2p neighbour links (+ skip links); cfg/status <=4 b serialisable.
**Timing-critical pairs:** the plan internal stations (leafup_i3/i4 -> xr staged, ~1190 um), xr<->macros (~800 um), and the
eng_finish chain neighbours.  **Intended layout:** the plan structure already follows this chain (finish row in chain
order, xr between its windows and the content macros, cap beside the ret windows), so it is kept: the search only
shifts cores <=250 um and flips them, and no link >=32 b (or any station link) may grow beyond 1.2x+20 um or cross the
396.9-um reach.  What it buys: face-window streets (the window jam class: capc5r is an M1-M7 full blocker under the W
lepk/xring windows), lower route_supply p99, a few % bit-mm.

## Per type

| type | moved | bit-mm | worst cut V/H | entry | rs p99 | chain corr | longer links | SVG |
|---|---|---|---|---|---|---|---|---|
| dsdv_slice_c1x_C__t1 | 10 | 7173.0 -> 7110.7 | 0.471/0.373 -> 0.471/0.368 | 3.42 -> 2.756 | 2.923 -> 2.313 | -0.986 -> -0.984 | 0 | dsdv_slice_c1x_C__t1_after.svg |
| dsdv_slice_c1x_C__t3 | 9 | 4745.6 -> 4693.3 | 0.314/0.409 -> 0.317/0.409 | 4.582 -> 3.697 | 1.744 -> 1.744 | 0.635 -> 0.636 | 0 | dsdv_slice_c1x_C__t3_after.svg |
| dsdv_slice_c1x_C__t4 | 8 | 6452.6 -> 6472.0 | 0.467/0.29 -> 0.467/0.29 | 2.18 -> 0.0 | 1.473 -> 1.473 | 0.881 -> 0.818 | 0 | dsdv_slice_c1x_C__t4_after.svg |
| dsdv_slice_c1x_C__t5 | 0 | 6643.2 -> 6643.2 | 0.389/0.433 -> 0.389/0.433 | 3.143 -> 3.143 | 2.087 -> 2.087 | -0.715 -> -0.715 | 0 | dsdv_slice_c1x_C__t5_after.svg |
| dsdv_slice_c1x_C__t6 | 4 | 7967.0 -> 7859.2 | 0.396/0.3 -> 0.396/0.3 | 2.199 -> 1.023 | 1.456 -> 1.457 | -0.921 -> -0.921 | 0 | dsdv_slice_c1x_C__t6_after.svg |
| dsdv_slice_c1x_C__t7 | 10 | 7824.9 -> 7920.3 | 0.473/0.429 -> 0.466/0.429 | 3.233 -> 1.751 | 2.373 -> 1.956 | -0.968 -> -0.96 | 0 | dsdv_slice_c1x_C__t7_after.svg |
| dsdv_slice_c1x_C__t8 | 8 | 6172.0 -> 5991.5 | 0.418/0.495 -> 0.43/0.425 | 3.143 -> 2.763 | 3.031 -> 2.691 | -0.44 -> -0.43 | 0 | dsdv_slice_c1x_C__t8_after.svg |
| dsdv_slice_c1x_C__t9 | 9 | 6099.0 -> 5927.5 | 0.371/0.445 -> 0.377/0.445 | 3.534 -> 2.649 | 2.003 -> 1.924 | -0.64 -> -0.653 | 0 | dsdv_slice_c1x_C__t9_after.svg |
| dsdv_slice_c1x_C__t10 | 0 | 7453.4 -> 7453.4 | 0.481/0.256 -> 0.481/0.256 | 2.977 -> 2.977 | 1.457 -> 1.457 | 0.796 -> 0.796 | 0 | dsdv_slice_c1x_C__t10_after.svg |
| dsdv_slice_c3x_C__t1 | 4 | 10169.5 -> 9955.1 | 0.431/0.432 -> 0.431/0.432 | 2.194 -> 0.934 | 0.482 -> 0.481 | 0.975 -> 0.97 | 0 | dsdv_slice_c3x_C__t1_after.svg |
| dsdv_slice_iq_C__t1 | 9 | 7779.0 -> 7651.7 | 0.476/0.325 -> 0.476/0.325 | 1.633 -> 0.657 | 0.785 -> 0.785 | -0.402 -> -0.474 | 0 | dsdv_slice_iq_C__t1_after.svg |
| dsdv_slice_kv512_C__t1 | 5 | 6563.9 -> 6453.2 | 0.42/0.34 -> 0.408/0.34 | 1.979 -> 0.876 | 1.457 -> 1.156 | 0.82 -> 0.807 | 0 | dsdv_slice_kv512_C__t1_after.svg |
| dsdv_slice_lepe_mu_C__t1 | 9 | 7853.0 -> 7640.9 | 0.422/0.326 -> 0.468/0.326 | 2.683 -> 0.219 | 1.457 -> 1.41 | 0.766 -> 0.74 | 0 | dsdv_slice_lepe_mu_C__t1_after.svg |
| dsdv_slice_lepe_nh_mus_C__t1 | 0 | 7247.1 -> 7247.1 | 0.447/0.43 -> 0.447/0.43 | 3.422 -> 3.422 | 1.457 -> 1.457 | 0.8 -> 0.8 | 0 | dsdv_slice_lepe_nh_mus_C__t1_after.svg |
| dsdv_slice_lepw_mu_C__t1 | 0 | 7567.6 -> 7567.6 | 0.429/0.443 -> 0.429/0.443 | 3.233 -> 3.233 | 2.373 -> 2.373 | -0.929 -> -0.929 | 0 | dsdv_slice_lepw_mu_C__t1_after.svg |
| dsdv_slice_lepw_mus_C__t1 | 7 | 7615.4 -> 7357.0 | 0.397/0.433 -> 0.471/0.437 | 3.954 -> 0.881 | 1.744 -> 1.744 | 0.623 -> 0.602 | 0 | dsdv_slice_lepw_mus_C__t1_after.svg |

## Dataflow links of dsdv_slice_c1x_C__t1 (top 30 by bits; length um before -> after)

| src | dst | bits | role | len |
|---|---|---|---|---|
| macros@259,701 | core:u_xr | 2817 | p2p | 821 -> 804 |
| core:u_xr | macros@259,701 | 1240 | p2p | 874 -> 856 |
| face:leafup_i2 | core:u_xr | 668 | p2p (staged station) | 464 -> 482 |
| face:leafup_i4 | core:u_xr | 668 | p2p (staged station) | 399 -> 416 |
| face:leafup_i0 | core:u_xr | 389 | p2p | 1383 -> 1365 |
| face:leafup_i1 | core:u_xr | 389 | p2p | 1451 -> 1434 |
| core:u_xr | core:u_cap | 312 | broadcast | 615 -> 606 |
| core:u_xr | face:leafdn_o0 | 151 | broadcast | 1182 -> 1165 |
| core:u_xr | face:leafdn_o1 | 151 | broadcast | 1596 -> 1579 |
| core:u_xr | face:leafdn_o2 | 151 | broadcast | 272 -> 289 |
| core:u_xr | face:leafdn_o3 | 151 | broadcast | 200 -> 217 |
| core:u_xr | face:leafdn_o4 | 151 | broadcast | 477 -> 494 |
| core:u_xf.g_cp[0].u_e | core:u_xf.g_cp[3].u_e | 131 | broadcast | 760 -> 769 |
| core:u_xf.g_cp[1].u_e | core:u_xf.g_cp[3].u_e | 131 | broadcast | 570 -> 570 |
| core:u_xf.g_cp[2].u_e | core:u_xf.g_cp[3].u_e | 131 | p2p | 190 -> 190 |
| core:u_xf.g_cp[0].u_e | core:u_xf.g_cp[2].u_e | 131 | broadcast | 570 -> 579 |
| core:u_xf.g_cp[1].u_e | core:u_xf.g_cp[2].u_e | 131 | broadcast | 380 -> 380 |
| core:u_xf.g_cp[0].u_e | core:u_xf.g_cp[1].u_e | 131 | broadcast | 190 -> 199 |
| core:u_xf.u_f | core:u_xf.g_cp[3].u_e | 123 | broadcast | 377 -> 377 |
| core:u_xf.u_f | core:u_xf.g_cp[2].u_e | 123 | broadcast | 187 -> 187 |
| core:u_xf.u_f | core:u_xf.g_cp[1].u_e | 123 | broadcast | 193 -> 193 |
| core:u_xf.u_f | core:u_xf.g_cp[0].u_e | 123 | broadcast | 383 -> 392 |
| face:ret_i0 | core:u_cap | 93 | p2p | 1777 -> 1769 |
| face:ret_i1 | core:u_cap | 93 | p2p | 1795 -> 1787 |
| face:ret_i2 | core:u_cap | 93 | p2p | 1813 -> 1804 |
| core:u_eg.u_gg | core:u_xr | 35 | p2p | 1151 -> 1090 |
| core:u_eg.u_nh | core:u_eg.u_gg | 35 | broadcast | 30 -> 30 |
| core:u_eg.u_nk | core:u_eg.u_gg | 35 | p2p | 26 -> 43 |
| core:u_xr | core:u_eg.u_gg | 32 | p2p | 1252 -> 1191 |
| core:u_xf.g_cp[3].u_e | glue:g_u_s_1S_u_lp_u_xf_edd | 32 | p2p | 380 -> 382 |

## Timing-critical pairs of dsdv_slice_c1x_C__t1

- {"kind": "plan station", "conn": "bus:leafdn_o0", "launch": "u_c.u_cap.cw_n_a", "capture": "face flop", "stages": 3, "bits": 597}
- {"kind": "plan station", "conn": "bus:leafdn_o1", "launch": "u_c.u_cap.cw_s_a", "capture": "face flop", "stages": 6, "bits": 597}
- {"kind": "plan station", "conn": "bus:leafdn_o2", "launch": "u_c.u_cap.cw_n_a", "capture": "face flop", "stages": 1, "bits": 597}
- {"kind": "plan station", "conn": "bus:leafdn_o3", "launch": "u_c.u_cap.cw_s_a", "capture": "face flop", "stages": 1, "bits": 597}
- {"kind": "plan station", "conn": "bus:leafdn_o4", "launch": "u_c.u_cap.cw_s_a", "capture": "face flop", "stages": 1, "bits": 597}
- {"kind": "plan station", "conn": "bus:leafup_i0", "launch": "face flop", "capture": "u_c.u_xr.e_c", "stages": 3, "bits": 668}
- {"kind": "plan station", "conn": "bus:leafup_i1", "launch": "face flop", "capture": "u_c.u_xr.e_c", "stages": 3, "bits": 668}
- {"kind": "plan station", "conn": "bus:leafup_i2", "launch": "face flop", "capture": "u_c.u_xr.e_c", "stages": 1, "bits": 668}
- {"kind": "plan station", "conn": "bus:leafup_i4", "launch": "face flop", "capture": "u_c.u_xr.e_c", "stages": 1, "bits": 668}
- {"kind": "plan station", "conn": "bus:ret_i0", "launch": "face flop", "capture": "u_c.u_cap.rt_w", "stages": 4, "bits": 70}
- {"kind": "plan station", "conn": "bus:ret_i1", "launch": "face flop", "capture": "u_c.u_cap.rt_w", "stages": 4, "bits": 70}
- {"kind": "plan station", "conn": "bus:ret_i2", "launch": "face flop", "capture": "u_c.u_cap.rt_w", "stages": 4, "bits": 70}
- {"kind": "link beyond 396.9-um reach", "src": "macros@259,701", "dst": "core:u_xr", "bits": 2817, "len_before": 821, "len_after": 804}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "macros@259,701", "bits": 1240, "len_before": 874, "len_after": 856}
- {"kind": "link beyond 396.9-um reach", "src": "face:leafup_i2", "dst": "core:u_xr", "bits": 668, "len_before": 464, "len_after": 482}
- {"kind": "link beyond 396.9-um reach", "src": "face:leafup_i4", "dst": "core:u_xr", "bits": 668, "len_before": 399, "len_after": 416}
- {"kind": "link beyond 396.9-um reach", "src": "face:leafup_i0", "dst": "core:u_xr", "bits": 389, "len_before": 1383, "len_after": 1365}
- {"kind": "link beyond 396.9-um reach", "src": "face:leafup_i1", "dst": "core:u_xr", "bits": 389, "len_before": 1451, "len_after": 1434}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "core:u_cap", "bits": 312, "len_before": 615, "len_after": 606}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "face:leafdn_o0", "bits": 151, "len_before": 1182, "len_after": 1165}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "face:leafdn_o1", "bits": 151, "len_before": 1596, "len_after": 1579}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "face:leafdn_o4", "bits": 151, "len_before": 477, "len_after": 494}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xf.g_cp[0].u_e", "dst": "core:u_xf.g_cp[3].u_e", "bits": 131, "len_before": 760, "len_after": 769}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xf.g_cp[1].u_e", "dst": "core:u_xf.g_cp[3].u_e", "bits": 131, "len_before": 570, "len_after": 570}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xf.g_cp[0].u_e", "dst": "core:u_xf.g_cp[2].u_e", "bits": 131, "len_before": 570, "len_after": 579}
- {"kind": "link beyond 396.9-um reach", "src": "face:ret_i0", "dst": "core:u_cap", "bits": 93, "len_before": 1777, "len_after": 1769}
- {"kind": "link beyond 396.9-um reach", "src": "face:ret_i1", "dst": "core:u_cap", "bits": 93, "len_before": 1795, "len_after": 1787}
- {"kind": "link beyond 396.9-um reach", "src": "face:ret_i2", "dst": "core:u_cap", "bits": 93, "len_before": 1813, "len_after": 1804}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_eg.u_gg", "dst": "core:u_xr", "bits": 35, "len_before": 1151, "len_after": 1090}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "core:u_eg.u_gg", "bits": 32, "len_before": 1252, "len_after": 1191}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_cap", "dst": "face:leafdn_o0", "bits": 29, "len_before": 1103, "len_after": 1094}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_cap", "dst": "face:leafdn_o1", "bits": 29, "len_before": 1623, "len_after": 1615}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_cap", "dst": "face:leafdn_o3", "bits": 29, "len_before": 444, "len_after": 452}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_cap", "dst": "face:leafdn_o4", "bits": 29, "len_before": 720, "len_after": 729}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "core:u_eg.u_nh", "bits": 16, "len_before": 1062, "len_after": 1002}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_xr", "dst": "core:u_eg.u_nk", "bits": 16, "len_before": 1200, "len_after": 1157}
