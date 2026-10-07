# Budget sheets: summary (tools/budgets/budget_sheet.py)

83 hardened masters. Sign-off 833.333 ps, SS 60 / FF 25 ps, accept +15/+15; skew terms intra (clock-plan region bound + 25, <= 90) / inter-region, meso, cross-domain 150 / forwarded-clock hop 0; wire 1.135 ps/um SS; reach 412 um intra, 359 um inter, 491 um forwarded.

| master | kind | dies (instances) | size um | block insertion SS (grade) / target | die entry target SS | ports | max L um | max stages | infeasible | fanout flags |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| hfd_attn_tile | attn_tile | hbm:64 | 1349 x 1350 | 900 (target) / 900 | - | 8 | 4525 | 12 | 0 | 0 |
| hfd_barrier | spine | hbm:1 | 1400 x 37 | 626 (target) / 626 | - | 2 | 108 | 1 | 0 | 0 |
| hfd_cdist_r14 | waypoint | hbm:4 | 111 x 216 | 563.9 (target) / 563.9 | - | 6 | 3724 | 10 | 0 | 0 |
| hfd_cdist_r15 | waypoint | hbm:4 | 68 x 203 | 531.5 (target) / 531.5 | - | 5 | 3964 | 10 | 0 | 0 |
| hfd_cmdproc_n | spine | hbm:1 | 1400 x 702 | 900 (target) / 900 | - | 11 | 4133 | 7 | 0 | 0 |
| hfd_cmdproc_s | spine | hbm:1 | 1400 x 702 | 900 (target) / 900 | - | 9 | 1588 | 3 | 0 | 0 |
| hfd_coll | spine | hbm:1 | 1400 x 1404 | 900 (target) / 900 | - | 19 | 2092 | 4 | 0 | 0 |
| hfd_gath_r10 | waypoint | hbm:2 | 167 x 315 | 628.3 (target) / 628.3 | - | 5 | 2434 | 7 | 0 | 0 |
| hfd_gath_r24 | waypoint | hbm:2 | 110 x 110 | 525.1 (target) / 525.1 | - | 4 | 2464 | 7 | 0 | 0 |
| hfd_gath_r25 | waypoint | hbm:2 | 167 x 315 | 628.3 (target) / 628.3 | - | 5 | 2654 | 6 | 0 | 0 |
| hfd_gath_r8 | waypoint | hbm:8 | 81 x 82 | 500.6 (target) / 500.6 | - | 3 | 2406 | 6 | 0 | 0 |
| hfd_gath_r9 | waypoint | hbm:2 | 110 x 110 | 525.1 (target) / 525.1 | - | 4 | 2436 | 7 | 0 | 0 |
| hfd_hc | hub | hbm:4 | 276 x 5530 | 900 (target) / 900 | - | 2 | 542 | 1 | 0 | 0 |
| hfd_host_slab | host_slab | hbm:1 | 594 x 16824 | 900 (target) / 900 | - | 0 | 0 | 0 | 0 | 0 |
| hfd_index_q_b0 | hub | hbm:4 | 930 x 970 | 1186 (measured) / 1254 | - | 4 | 4530 | 12 | 0 | 0 |
| hfd_index_q_b1 | hub | hbm:4 | 930 x 970 | 1132 (measured) / 1154 | - | 4 | 2 | 1 | 0 | 0 |
| hfd_index_q_b2 | hub | hbm:4 | 930 x 960 | 1309 (measured) / 1402 | - | 7 | 2056 | 5 | 0 | 0 |
| hfd_index_q_b3 | hub | hbm:4 | 930 x 970 | 1185 (measured) / 1298 | - | 6 | 1737 | 5 | 0 | 0 |
| hfd_index_q_b4 | hub | hbm:4 | 930 x 830 | 900 (target) / 900 | - | 4 | 2 | 1 | 0 | 0 |
| hfd_index_q_b5 | hub | hbm:4 | 930 x 829 | 1324 (measured) / 1354 | - | 4 | 4525 | 12 | 0 | 0 |
| hfd_loader | spine | hbm:1 | 1400 x 238 | 900 (target) / 900 | - | 2 | 1608 | 4 | 0 | 0 |
| hfd_mcast_r5 | waypoint | hbm:4 | 242 x 410 | 702.5 (target) / 702.5 | - | 4 | 2108 | 5 | 0 | 0 |
| hfd_mcast_r6 | waypoint | hbm:8 | 467 x 121 | 635.6 (target) / 635.6 | - | 4 | 2108 | 5 | 0 | 0 |
| hfd_mcast_r7 | waypoint | hbm:4 | 467 x 121 | 635.6 (target) / 635.6 | - | 3 | 1995 | 5 | 0 | 0 |
| hfd_meso_r1 | waypoint | hbm:16 | 398 x 71 | 575.7 (target) / 575.7 | - | 2 | 1493 | 4 | 0 | 0 |
| hfd_meso_r28 | waypoint | hbm:9 | 63 x 190 | 525 (target) / 525 | - | 2 | 1614 | 4 | 0 | 0 |
| hfd_meso_r32 | waypoint | hbm:1 | 39 x 285 | 521.5 (target) / 521.5 | - | 2 | 1547 | 4 | 0 | 0 |
| hfd_meso_r35 | waypoint | hbm:4 | 39 x 285 | 521.5 (target) / 521.5 | - | 2 | 1625 | 4 | 0 | 0 |
| hfd_meso_r37 | waypoint | hbm:1 | 270 x 41 | 521 (target) / 521 | - | 2 | 1534 | 4 | 0 | 0 |
| hfd_quant | spine | hbm:1 | 1400 x 359 | 900 (target) / 900 | - | 5 | 4775 | 8 | 0 | 0 |
| hfd_router | spine | hbm:1 | 1400 x 326 | 900 (target) / 900 | - | 10 | 6724 | 11 | 0 | 0 |
| hfd_serdes_slab | serdes_slab | hbm:2 | 2462 x 3657 | 900 (target) / 900 | - | 0 | 0 | 0 | 0 | 0 |
| hfd_sfu | hub | hbm:4 | 399 x 5530 | 900 (target) / 900 | - | 4 | 542 | 1 | 0 | 0 |
| hfd_sm | sm | hbm:32 | 2203 x 2074 | 900 (target) / 900 | - | 5 | 3615 | 9 | 0 | 0 |
| hfd_stn_r0 | waypoint | hbm:16 | 70 x 60 | 486.4 (target) / 486.4 | - | 2 | 1701 | 4 | 0 | 0 |
| hfd_stn_r11 | waypoint | hbm:12 | 49 x 127 | 498.2 (target) / 498.2 | - | 2 | 1685 | 4 | 0 | 0 |
| hfd_stn_r12 | waypoint | hbm:12 | 56 x 65 | 482 (target) / 482 | - | 2 | 1666 | 4 | 0 | 0 |
| hfd_stn_r13 | waypoint | hbm:12 | 64 x 56 | 482 (target) / 482 | - | 2 | 1666 | 4 | 0 | 0 |
| hfd_stn_r16 | waypoint | hbm:24 | 19 x 119 | 471.1 (target) / 471.1 | - | 2 | 2050 | 5 | 0 | 0 |
| hfd_stn_r17 | waypoint | hbm:12 | 116 x 19 | 471 (target) / 471 | - | 2 | 1610 | 4 | 0 | 0 |
| hfd_stn_r18 | waypoint | hbm:8 | 67 x 60 | 485 (target) / 485 | - | 2 | 1672 | 4 | 0 | 0 |
| hfd_stn_r19 | waypoint | hbm:4 | 60 x 67 | 484.8 (target) / 484.8 | - | 2 | 1672 | 4 | 0 | 0 |
| hfd_stn_r2 | waypoint | hbm:16 | 15 x 143 | 469.5 (target) / 469.5 | - | 2 | 1894 | 5 | 0 | 0 |
| hfd_stn_r20 | waypoint | hbm:8 | 66 x 60 | 484.7 (target) / 484.7 | - | 2 | 1953 | 4 | 0 | 0 |
| hfd_stn_r21 | waypoint | hbm:8 | 60 x 67 | 484.6 (target) / 484.6 | - | 2 | 1671 | 4 | 0 | 0 |
| hfd_stn_r22 | waypoint | hbm:16 | 43 x 73 | 478.5 (target) / 478.5 | - | 2 | 1664 | 4 | 0 | 0 |
| hfd_stn_r23 | waypoint | hbm:8 | 73 x 43 | 478.4 (target) / 478.4 | - | 2 | 1657 | 4 | 0 | 0 |
| hfd_stn_r26 | waypoint | hbm:2 | 126 x 50 | 498.5 (target) / 498.5 | - | 2 | 2478 | 6 | 0 | 0 |
| hfd_stn_r27 | waypoint | hbm:27 | 63 x 63 | 484.5 (target) / 484.5 | - | 2 | 1698 | 4 | 0 | 0 |
| hfd_stn_r29 | waypoint | hbm:2 | 60 x 65 | 484.1 (target) / 484.1 | - | 2 | 1669 | 4 | 0 | 0 |
| hfd_stn_r3 | waypoint | hbm:16 | 15 x 143 | 469.5 (target) / 469.5 | - | 2 | 1579 | 4 | 0 | 0 |
| hfd_stn_r30 | waypoint | hbm:4 | 39 x 78 | 477.8 (target) / 477.8 | - | 2 | 1659 | 4 | 0 | 0 |
| hfd_stn_r31 | waypoint | hbm:6 | 73 x 41 | 477.3 (target) / 477.3 | - | 2 | 1657 | 4 | 0 | 0 |
| hfd_stn_r33 | waypoint | hbm:5 | 39 x 78 | 477.8 (target) / 477.8 | - | 2 | 1801 | 5 | 0 | 0 |
| hfd_stn_r34 | waypoint | hbm:4 | 73 x 41 | 477.3 (target) / 477.3 | - | 2 | 1648 | 4 | 0 | 0 |
| hfd_stn_r36 | waypoint | hbm:1 | 39 x 78 | 477.8 (target) / 477.8 | - | 2 | 1653 | 4 | 0 | 0 |
| hfd_stn_r4 | waypoint | hbm:20 | 121 x 52 | 498.5 (target) / 498.5 | - | 2 | 1682 | 4 | 0 | 0 |
| hfd_su | hub | hbm:4 | 703 x 5530 | 900 (target) / 900 | - | 15 | 6724 | 17 | 0 | 0 |
| hfd_su_full | spine | hbm:1 | 346 x 348 | 730 (target) / 730 | - | 0 | 0 | 0 | 0 | 0 |
| hfd_su_red | spine | hbm:1 | 1400 x 218 | 900 (target) / 900 | - | 0 | 0 | 0 | 0 | 0 |
| hfd_svc_SE_s0 | svc | hbm:2 | 1017 x 259 | 1057 (measured) / 874.1 OVER | - | 7 | 2467 | 4 | 0 | 0 |
| hfd_svc_SE_s1 | svc | hbm:2 | 1301 x 259 | 879 (measured) / 900 | - | 7 | 1701 | 3 | 0 | 0 |
| hfd_svc_SE_s2 | svc | hbm:2 | 1062 x 259 | 758 (measured) / 883.8 | - | 7 | 177 | 1 | 0 | 0 |
| hfd_svc_SE_s3 | svc | hbm:2 | 1382 x 259 | 919 (measured) / 919 | - | 10 | 2050 | 4 | 0 | 0 |
| hfd_svc_SE_s4 | svc | hbm:2 | 1009 x 259 | 808 (measured) / 872.3 | - | 7 | 175 | 1 | 0 | 0 |
| hfd_svc_SE_s5 | svc | hbm:2 | 1095 x 259 | 829 (measured) / 890.8 | - | 7 | 1699 | 3 | 0 | 0 |
| hfd_svc_SE_s6 | svc | hbm:2 | 764 x 259 | 562 (measured) / 814.9 | - | 5 | 9 | 1 | 0 | 0 |
| hfd_svc_SE_s7 | svc | hbm:2 | 870 x 259 | 631 (measured) / 840.8 | - | 5 | 175 | 1 | 0 | 0 |
| hfd_svc_SW_s0 | svc | hbm:2 | 1017 x 259 | 874.1 (target) / 874.1 | - | 7 | 2466 | 4 | 0 | 0 |
| hfd_svc_SW_s1 | svc | hbm:2 | 1306 x 259 | 900 (target) / 900 | - | 9 | 1952 | 3 | 0 | 0 |
| hfd_svc_SW_s2 | svc | hbm:2 | 1057 x 259 | 882.7 (target) / 882.7 | - | 7 | 344 | 1 | 0 | 0 |
| hfd_svc_SW_s3 | svc | hbm:2 | 1073 x 259 | 886.1 (target) / 886.1 | - | 8 | 1700 | 3 | 0 | 0 |
| hfd_svc_SW_s4 | svc | hbm:2 | 786 x 259 | 820.4 (target) / 820.4 | - | 5 | 9 | 1 | 0 | 0 |
| hfd_svc_SW_s5 | svc | hbm:2 | 1063 x 259 | 884 (target) / 884 | - | 7 | 344 | 1 | 0 | 0 |
| hfd_svc_SW_s6 | svc | hbm:2 | 1062 x 259 | 883.8 (target) / 883.8 | - | 7 | 1700 | 3 | 0 | 0 |
| hfd_svc_SW_s7 | svc | hbm:2 | 1136 x 259 | 899.4 (target) / 899.4 | - | 5 | 346 | 1 | 0 | 0 |
| hfd_vm_ne | spine | hbm:1 | 700 x 1000 | 900 (target) / 900 | - | 17 | 3437 | 6 | 0 | 0 |
| hfd_vm_nw | spine | hbm:1 | 700 x 1000 | 900 (target) / 900 | - | 18 | 3438 | 6 | 0 | 0 |
| hfd_vm_se | spine | hbm:1 | 700 x 1000 | 900 (target) / 900 | - | 17 | 3066 | 5 | 0 | 0 |
| hfd_vm_sw | spine | hbm:1 | 700 x 1000 | 900 (target) / 900 | - | 18 | 3067 | 5 | 0 | 0 |
| ot_hbm3e_phy_v41x_aw30_e8p5 | phy | hbm:4 | 8500 x 1177 | 900 (target) / 900 | - | 13 | 9 | 1 | 0 | 0 |
| ot_hbm_host_phy | link | hbm:1 | 261 x 1652 | 900 (target) / 900 | - | 1 | 174 | 1 | 0 | 0 |
| ot_pdie_serdes | link | hbm:9 | 250 x 2250 | 900 (target) / 900 | - | 1 | 1091 | 3 | 0 | 0 |

## Interfaces infeasible as planned (need an architecture / stage change)

| master | port | dir | bits | L um | skew class | stages needed | internal ps as planned | worst instance |
|---|---|---|---:|---:|---|---:|---:|---|
