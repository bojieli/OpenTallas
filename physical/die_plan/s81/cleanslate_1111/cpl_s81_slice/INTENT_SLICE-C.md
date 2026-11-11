# INTENT SHEET SLICE-C (CPL-S81-SLICE, plan 99f40d35071d)

Delta: `delta_SLICE-C_99f40d35.json` sha256 `e1ebefaeb58f95b6d43aaee78c4e830f4f56587438be299d35ab5d43b41bbd95`; adopted types 6/16.

**Dataflow (bound netlist + LEF directions + plan buses/stations).** Ring side: leafup_i* face windows (279-668 b each,
the farthest one staged) -> u_xr (xrt ring core) <-> the slice content macros (2707 b in / 1240 b out, p2p) -> u_xr broadcasts
151 b to every leafdn_o* window and 312 b to u_cap (capc5r).  ret_i* windows -> u_cap.  u_eg.u_nh / u_eg.u_nk (egn) and
u_eg.u_gg (egg) sit one stage behind cap/xr.  Finish side: u_xf.g_cp[0..3].u_e (eng_finish) form a serial chain
(131 b per neighbour, 190-um pitch) closed by u_xf.u_f (norm_finish, 123 b).  Roles: face->xr and xr<->macros p2p;
xr->leafdn/cap broadcast; finish chain p2p neighbour links (+ skip links); cfg/status <=4 b serialisable.
**Timing-critical pairs:** the plan internal stations (leafup_i3/i4 -> xr staged, ~1190 um), xr<->macros (~800 um), and the
eng_finish chain neighbours.  **Intended layout:** the plan structure already follows this chain (finish row in chain
order, xr between its windows and the content macros, cap beside the ret windows), so it is kept: the search only
shifts cores <=250 um on the 8.64 lattice (no relocate, no flip), and no link >=32 b (or any station link) may grow beyond
1.2x+20 um or cross the 396.9-um reach.  **Composer gate (v2, DS85-COMPOSE-1111 dry-run FAIL of v1 6464cded):** every
search step must also pass the composer legality copied rule for rule (cgate.py): no new overlap or street <34.56 um
(abutted 0 allowed) against every hard core AND every lef content macro (the slice SRAM/em banks), no new station/ft
reg, tap or core tap strictly under any core or macro box (after the station re-site), and the kit tap rule
(taps.grid_explicit_taps load <=1500, radius <=1.10 x tap_radius_um) checked on 99f + the LP-W window.  Six types keep a
legal fine-tune (c1x t4/t8/t9, c3x, iq, lepe_mu_C); c1x t1/t3/t6/t7, kv512 and lepw_mus_C have no legal improvement
under the gate -> KEEP.  What it buys: face-window entry streets, lower route_supply p99 (c1x_t8 3.03 -> 2.69),
~0.5 % family bit-mm.

## Per type

| type | moved | bit-mm | worst cut V/H | entry | rs p99 | chain corr | longer links | SVG |
|---|---|---|---|---|---|---|---|---|
| dsdv_slice_c1x_C__t1 | 0 | 7173.0 -> 7173.0 | 0.471/0.373 -> 0.471/0.373 | 3.42 -> 3.42 | 2.923 -> 2.923 | -0.986 -> -0.986 | 0 | dsdv_slice_c1x_C__t1_after.svg |
| dsdv_slice_c1x_C__t3 | 0 | 4745.6 -> 4745.6 | 0.314/0.409 -> 0.314/0.409 | 4.582 -> 4.582 | 1.744 -> 1.744 | 0.635 -> 0.635 | 0 | dsdv_slice_c1x_C__t3_after.svg |
| dsdv_slice_c1x_C__t4 | 10 | 6452.6 -> 6447.1 | 0.467/0.29 -> 0.467/0.29 | 2.18 -> 0.632 | 1.473 -> 1.473 | 0.881 -> 0.851 | 0 | dsdv_slice_c1x_C__t4_after.svg |
| dsdv_slice_c1x_C__t5 | 0 | 6643.2 -> 6643.2 | 0.389/0.433 -> 0.389/0.433 | 3.143 -> 3.143 | 2.087 -> 2.087 | -0.715 -> -0.715 | 0 | dsdv_slice_c1x_C__t5_after.svg |
| dsdv_slice_c1x_C__t6 | 0 | 7967.0 -> 7967.0 | 0.396/0.3 -> 0.396/0.3 | 2.199 -> 2.199 | 1.456 -> 1.456 | -0.921 -> -0.921 | 0 | dsdv_slice_c1x_C__t6_after.svg |
| dsdv_slice_c1x_C__t7 | 0 | 7824.9 -> 7824.9 | 0.473/0.429 -> 0.473/0.429 | 3.233 -> 3.233 | 2.373 -> 2.373 | -0.968 -> -0.968 | 0 | dsdv_slice_c1x_C__t7_after.svg |
| dsdv_slice_c1x_C__t8 | 9 | 6172.0 -> 6028.8 | 0.418/0.495 -> 0.432/0.425 | 3.143 -> 2.763 | 3.031 -> 2.691 | -0.44 -> -0.387 | 0 | dsdv_slice_c1x_C__t8_after.svg |
| dsdv_slice_c1x_C__t9 | 9 | 6099.0 -> 6054.1 | 0.371/0.445 -> 0.371/0.445 | 3.534 -> 3.313 | 2.003 -> 1.924 | -0.64 -> -0.663 | 0 | dsdv_slice_c1x_C__t9_after.svg |
| dsdv_slice_c1x_C__t10 | 0 | 7453.4 -> 7453.4 | 0.481/0.256 -> 0.481/0.256 | 2.977 -> 2.977 | 1.457 -> 1.457 | 0.796 -> 0.796 | 0 | dsdv_slice_c1x_C__t10_after.svg |
| dsdv_slice_c3x_C__t1 | 5 | 10169.5 -> 9953.7 | 0.431/0.432 -> 0.431/0.432 | 2.194 -> 1.31 | 0.482 -> 0.481 | 0.975 -> 0.97 | 0 | dsdv_slice_c3x_C__t1_after.svg |
| dsdv_slice_iq_C__t1 | 6 | 7779.0 -> 7657.3 | 0.476/0.325 -> 0.476/0.325 | 1.633 -> 0.969 | 0.785 -> 0.785 | -0.402 -> -0.469 | 0 | dsdv_slice_iq_C__t1_after.svg |
| dsdv_slice_kv512_C__t1 | 0 | 6563.9 -> 6563.9 | 0.42/0.34 -> 0.42/0.34 | 1.979 -> 1.979 | 1.457 -> 1.457 | 0.82 -> 0.82 | 0 | dsdv_slice_kv512_C__t1_after.svg |
| dsdv_slice_lepe_mu_C__t1 | 7 | 7853.0 -> 7754.3 | 0.422/0.326 -> 0.418/0.326 | 2.683 -> 1.523 | 1.457 -> 1.427 | 0.766 -> 0.757 | 0 | dsdv_slice_lepe_mu_C__t1_after.svg |
| dsdv_slice_lepe_nh_mus_C__t1 | 0 | 7247.1 -> 7247.1 | 0.447/0.43 -> 0.447/0.43 | 3.422 -> 3.422 | 1.457 -> 1.457 | 0.8 -> 0.8 | 0 | dsdv_slice_lepe_nh_mus_C__t1_after.svg |
| dsdv_slice_lepw_mu_C__t1 | 0 | 7567.6 -> 7567.6 | 0.429/0.443 -> 0.429/0.443 | 3.233 -> 3.233 | 2.373 -> 2.373 | -0.929 -> -0.929 | 0 | dsdv_slice_lepw_mu_C__t1_after.svg |
| dsdv_slice_lepw_mus_C__t1 | 0 | 7615.4 -> 7615.4 | 0.397/0.36 -> 0.397/0.36 | 2.631 -> 2.631 | 1.744 -> 1.744 | 0.623 -> 0.623 | 0 | dsdv_slice_lepw_mus_C__t1_after.svg |

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

## Composer gate evidence (v2)
- cgate.py (rule-for-rule copy of compose_cleanslate_1111.py legality + kit tap rule) on 99f + LP-W window: 0 new findings on all 6 moved types (ctest_g.log); v1 had 74 new.
- G0 (check.py) plan_g and plan_g_win: 84 -> 84 errors, NEW 0; no new warning naming any slice/kv_leaf type.
- Advisory only: c1x_C__t8 added tap clk_t23 radius 211.464 / 211.0 target (KW-FIX-28: stop only above 1.10 x).
- Companion for the composer (--derived): companion_SLICE-C.json (core taps of the moved cores + every internal station from/to/regs, counts unchanged).

## Explorer view (COORD 03:0x), v2
Command (epyc4, plan-route-1/repo): `explorer_render.py type --plan plan_99f.json --type T --repo . --delta delta_SLICE-C_99f40d35.json --supply --release-cache .../release_cache.json`, plus `--plan plan_g.json` (station regs and core taps re-sited).
PNGs: `explorer_<T>_delta.png` and `explorer_<T>_after_resited.png`.

| type | before max hop / hop>reach | --delta (stale regs) | after, re-sited | rs p99 before -> after |
|---|---|---|---|---|
| c1x_C__t4 | 416 / 1 | 416 / 1 | 416 / 1 | 1.473 -> 1.473 |
| c1x_C__t8 | 417 / 1 | 417 / 1 | 416 / 1 | 3.031 -> 2.691 |
| c1x_C__t9 | 364 / 0 | 364 / 0 | 399 / 0 | 2.003 -> 1.924 |
| c3x_C__t1 | 416 / 1 | 416 / 1 | 416 / 1 | 0.482 -> 0.481 |
| iq_C__t1 | 416 / 2 | 416 / 2 | 416 / 2 | 0.785 -> 0.785 |
| lepe_mu_C__t1 | 416 / 2 | 416 / 3 | 416 / 2 | 1.457 -> 1.427 |

**Over-reach links.** I viewed the c1x_C__t8 and lepe_mu_C__t1 renders myself.
- With the regs re-sited, the delta adds no over-reach link on any type. The one extra link in the lepe_mu_C `--delta` column is a stale station reg.
- The remaining over-reach links are the plan's own: cap `cw_n_a` -> the first leafdn station reg at 408-416 um (reach 405).
- **I accept them:** they are pre-existing, at most 11 um over, and owned by the die-owner station siting.
- c1x_C__t8, the largest move:
  - u_xf.u_f (norm_finish) lifts 225 um, from the finish row to y 769, between the row and egn.
  - The four eng_finish shift by at most 86 um in x and 35 um in y, so the row reads cp0, cp1, (u_f above), cp2, cp3 in chain order.
  - Chain correlation goes from -0.44 to -0.39. No link of >=32 b grows beyond 1.2x+20 um or crosses reach.
  - The hot S-face band under cap/xr cools: p99 3.03 -> 2.69, core_H 1.23 -> 1.19, ring_H flag cleared.
