# Finite top memory reach cases from actual placed data

One worst launch per failing capture; canonical typed-memory bounding-box reach, not routed delay. All native paths/guide matching use the existing exports. Full names, master/bank/coordinates and guide analysis are in long_pair_diagnosis.json.

## FF → memory

| # | Reach µm | Guide | Final FF inside | Bank / capture |
|---:|---:|---|---|---|
| 1 | 561.261 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.wdat_r[1][35]$_DFF_P_` |
| 2 | 558.597 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.wdat_r[1][218]$_DFF_P_` |
| 3 | 556.821 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[10].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.wdat_r[1][96]$_DFF_P_` |
| 4 | 551.589 | leaf2 | False | `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.dt[0].mem.g[1].mem` →/← `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.wdat_r[0][209]$_DFF_P_` |
| 5 | 543.795 | leaf4 | False | `u_fcore.g_c[4].u_c.g_p.u_p.g_m4.ix[0].mem.g[3].mem` →/← `u_fcore.g_c[4].u_c.g_p.u_p.pc[7]$_DFFE_PP_` |
| 6 | 542.751 | leaf2 | True | `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.ix[0].mem.g[2].mem` →/← `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.wdat_r[0][102]$_DFF_P_` |
| 7 | 542.199 | leaf8 | False | `u_fcore.g_c[8].u_c.g_p.u_p.g_m4.ix[0].mem.g[1].mem` →/← `u_fcore.g_c[8].u_c.g_p.u_p.pc[8]$_DFFE_PP_` |
| 8 | 536.259 | leaf2 | True | `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.ix[0].mem.g[1].mem` →/← `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.wdat_r[0][73]$_DFF_P_` |
| 9 | 519.933 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[12].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.wdat_r[1][35]$_DFF_P_` |
| 10 | 516.939 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[4].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.genblk5.g_p2.vi_c$_DFF_P_` |
| 11 | 515.541 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[9].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.wdat_r[1][96]$_DFF_P_` |
| 12 | 513.339 | leaf6 | False | `u_fcore.g_c[6].u_c.g_p.u_p.g_m4.ix[0].mem.g[3].mem` →/← `u_fcore.g_c[6].u_c.g_p.u_p.g_m4.wdat_r[0][46]$_DFF_P_` |
| 13 | 510.309 | leaf2 | False | `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.dt[0].mem.g[0].mem` →/← `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.wdat_r[0][209]$_DFF_P_` |
| 14 | 502.515 | leaf4 | False | `u_fcore.g_c[4].u_c.g_p.u_p.g_m4.ix[0].mem.g[2].mem` →/← `u_fcore.g_c[4].u_c.g_p.u_p.pc[7]$_DFFE_PP_` |
| 15 | 502.041 | leaf6 | False | `u_fcore.g_c[6].u_c.g_p.u_p.g_m4.ix[0].mem.g[2].mem` →/← `u_fcore.g_c[6].u_c.g_p.u_p.g_m4.wdat_r[0][80]$_DFF_P_` |
| 16 | 501.423 | leaf2 | True | `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.ix[0].mem.g[3].mem` →/← `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.wdat_r[0][102]$_DFF_P_` |
| 17 | 500.919 | leaf8 | False | `u_fcore.g_c[8].u_c.g_p.u_p.g_m4.ix[0].mem.g[0].mem` →/← `u_fcore.g_c[8].u_c.g_p.u_p.pc[8]$_DFFE_PP_` |
| 18 | 494.979 | leaf2 | True | `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.ix[0].mem.g[0].mem` →/← `u_fcore.g_c[2].u_c.g_p.u_p.g_m4.wdat_r[0][73]$_DFF_P_` |
| 19 | 477.039 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.ix[0].mem.g[0].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.wdat_r[0][41]$_DFF_P_` |
| 20 | 475.611 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[3].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.genblk5.g_p2.vi_c$_DFF_P_` |

## Memory → FF

| # | Reach µm | Guide | Final FF inside | Bank / capture |
|---:|---:|---|---|---|
| 1 | 555.627 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][196]$_DFF_P_` |
| 2 | 553.863 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][14]$_DFF_P_` |
| 3 | 553.197 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][211]$_DFF_P_` |
| 4 | 553.035 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][201]$_DFF_P_` |
| 5 | 551.595 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][22]$_DFF_P_` |
| 6 | 549.795 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][247]$_DFF_P_` |
| 7 | 547.797 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][213]$_DFF_P_` |
| 8 | 547.437 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][0]$_DFF_P_` |
| 9 | 546.501 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][222]$_DFF_P_` |
| 10 | 545.853 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][249]$_DFF_P_` |
| 11 | 545.853 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][210]$_DFF_P_` |
| 12 | 545.493 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][205]$_DFF_P_` |
| 13 | 545.439 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][183]$_DFF_P_` |
| 14 | 544.791 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][153]$_DFF_P_` |
| 15 | 544.341 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][199]$_DFF_P_` |
| 16 | 544.023 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[10].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][160]$_DFF_P_` |
| 17 | 543.909 | leaf1 | True | `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.g[5].mem` →/← `u_fcore.g_c[1].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[2][203]$_DFF_P_` |
| 18 | 543.537 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[10].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][57]$_DFF_P_` |
| 19 | 543.171 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][54]$_DFF_P_` |
| 20 | 543.117 | leaf3 | True | `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.g[11].mem` →/← `u_fcore.g_c[3].u_c.g_p.u_p.g_m4.dt[0].mem.og_q[5][202]$_DFF_P_` |

