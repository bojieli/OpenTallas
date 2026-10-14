# R25GQ r25gqn_v13 (candidate): bits per cut

Model: `tools/hbm_r25gq_cuts.py` (capacity of results/arch/hbm_b2_1012 SPEC 6a: 0.75 of M8 / M9 over the whole line + 0.75 of M6 / M7 and 0.5 of M4 / M5 in its channels; a bus crosses a line when the line separates the nearest points of its two end boxes).

**64 cuts, worst 0.431, limit 0.60: PASS**

| cut | line | window um | what | bits | tracks | util | largest buses |
|---|---|---|---|---:|---:|---:|---|
| X_centre_full | x = 16,492 | 0-25,979 | full die | 63,631 | 601,598 | 0.106 | xt_SE 4,136, vring_SW_SE 2,148, vring_SE_SW 2,148 |
| Y_centre_full | y = 12,990 | 0-32,984 | full die | 55,266 | 923,362 | 0.060 | vring_SW_NW 2,148, vring_NW_SW 2,148, vring_SE_NE 2,148 |
| x12_hub | x = 12,000 | 10,000-16,000 | hub line (cuts_v07) | 10,170 | 105,402 | 0.096 | xt_SW 2,068, hgi_lgsw_tap_rdn_sfu_SW_ 2,065, vmap_SW 1,200 |
| x13_hub | x = 13,000 | 10,000-16,000 | hub line (cuts_v07) | 19,406 | 105,402 | 0.184 | hgi_lgnw_wup_1 2,243, hb_su_SW_vm_q0n0 2,048, xt_SW_3_t0_w0_q1n0 1,040 |
| x14_hub | x = 14,000 | 10,000-16,000 | hub line (cuts_v07) | 32,023 | 156,226 | 0.205 | lk_lk_N1 2,244, hgi_su_cmd 2,198, tkm_del 2,180 |
| x14.4_hub | x = 14,400 | 10,000-16,000 | hub line (cuts_v07) | 40,081 | 189,062 | 0.212 | vxl_SW 4,130, tkm_del 2,180, vring_NW_NE 2,148 |
| x15_hub | x = 15,000 | 10,000-16,000 | hub line (cuts_v07) | 16,524 | 117,230 | 0.141 | xt_SW 2,068, lk_lk_N3_0_q0n5 1,122, hgi_su_cmd_w1 1,094 |
| x15.5_hub | x = 15,500 | 10,000-16,000 | hub line (cuts_v07) | 12,760 | 117,230 | 0.109 | xt_SW 2,068, lk_lk_S1_0_q0n0 1,122, lk_lk_N3_0_q0n4 1,122 |
| x16_hub | x = 16,000 | 10,000-16,000 | hub line (cuts_v07) | 18,610 | 117,230 | 0.159 | vring_NE_NW 2,148, hgi_idx_cmd 2,075, xt_SW 2,068 |
| x16.5_hub | x = 16,500 | 10,000-16,000 | hub line (cuts_v07) | 23,228 | 189,062 | 0.123 | vring_NW_NE 2,148, vring_NE_NW 2,148, xt_SE_0_t3_q0n2 2,068 |
| x17_hub | x = 17,000 | 10,000-16,000 | hub line (cuts_v07) | 33,248 | 154,398 | 0.215 | vring_SE_NE 4,296, vrc_att_wup 2,241, vcb_SE_NE 2,176 |
| x18_hub | x = 18,000 | 10,000-16,000 | hub line (cuts_v07) | 33,289 | 121,562 | 0.274 | hb_su_SE_vm 10,240, xt_SE 2,068, vrc_hce_wup_0_w0_q0n4 1,136 |
| y10_hub | y = 10,000 | 12,000-18,000 | hub line (cuts_v07) | 27,610 | 130,261 | 0.212 | lk_lk_S0 3,366, lk_lk_S2 2,244, xt_SE 2,068 |
| y11_hub | y = 11,000 | 12,000-18,000 | hub line (cuts_v07) | 37,320 | 158,081 | 0.236 | hgi_su_cmd_t10_q0n0 2,198, xt_SE 2,068, hb_vm_su_SW 2,048 |
| y12_hub | y = 12,000 | 12,000-18,000 | hub line (cuts_v07) | 35,340 | 131,753 | 0.268 | hgi_su_cmd 2,198, vring_SW_NW 2,148, vring_NW_SW 2,148 |
| y12.5_hub | y = 12,500 | 12,000-18,000 | hub line (cuts_v07) | 44,121 | 162,367 | 0.272 | hgi_su_cmd 2,198, vring_SW_NW 2,148, vring_NW_SW 2,148 |
| y13_hub | y = 13,000 | 12,000-18,000 | hub line (cuts_v07) | 48,819 | 162,367 | 0.301 | hgi_su_cmd 2,198, vring_SW_NW 2,148, vring_NW_SW 2,148 |
| y14_hub | y = 14,000 | 12,000-18,000 | hub line (cuts_v07) | 48,037 | 162,735 | 0.295 | tkm_del 2,180, vring_SW_NW 2,148, vring_SE_NE 2,148 |
| y14.6_hub | y = 14,600 | 12,000-18,000 | hub line (cuts_v07) | 41,700 | 131,753 | 0.317 | vring_SW_NW 2,148, vring_NW_SW 2,148, vring_NE_SE 2,148 |
| y15_hub | y = 15,000 | 12,000-18,000 | hub line (cuts_v07) | 55,725 | 158,081 | 0.353 | lk_lk_N2 4,488, tkm_del 4,360, lk_lk_N1 2,244 |
| y16_hub | y = 16,000 | 12,000-18,000 | hub line (cuts_v07) | 37,488 | 105,622 | 0.355 | lk_lk_N2 3,366, vxl_SW 2,065, vxl_SE 2,065 |
| hb_tkm_W | x = 8,566 | 15,778-18,622 | 235-um channel W of hb_tkm | 3,593 | 89,636 | 0.040 | rt_NW 2,165, cd_NW 899, tr_NW0 529 |
| hb_tkm_E | x = 11,056 | 15,778-18,622 | 235-um channel E of hb_tkm | 8,278 | 89,636 | 0.092 | rt_NW_e_t2_q0n0 2,165, xt_NW 2,068, hb_su_NW_vm_q0n5 2,048 |
| hb_coll_E | x = 16,465 | 10,402-12,963 | 658-um channel E of hb_coll | 8,884 | 80,720 | 0.110 | vcb_coll_SE_0_q0n2 1,088, hgi_idx_cmd_t10_w0_q0n2 1,040, hgi_idx_cmd_t10_w0_q0n6 1,040 |
| hb_coll_S | y = 10,750 | 14,236-16,636 | 302-um channel S of hb_coll | 22,524 | 75,614 | 0.298 | xt_SE 2,068, hb_su_SW_su_SE 2,048, lk_lk_S0 1,122 |
| hb_cmdproc_W | x = 14,543 | 13,834-16,238 | 386-um channel W of hb_cmdproc | 31,075 | 75,750 | 0.410 | lk_lk_N0 2,244, lk_lk_N2 2,244, vring_NW_NE 2,148 |
| hb_cmdproc_N | y = 15,848 | 14,236-16,636 | 220-um channel N of hb_cmdproc | 31,514 | 73,086 | 0.431 | hb_su_NE_su_NW 3,072, lk_lk_N2 2,244, vring_NW_NE 2,148 |
| hb_quant_W | x = 14,712 | 15,458-17,106 | 49-um channel W of hb_quant | 20,638 | 51,929 | 0.397 | xt_SW 2,068, vxl_SW 2,065, vrc_cp_wup_w0 1,136 |
| hb_quant_S | y = 15,848 | 14,236-16,636 | 220-um channel S of hb_quant | 31,514 | 73,086 | 0.431 | hb_su_NE_su_NW 3,072, lk_lk_N2 2,244, vring_NW_NE 2,148 |
| hb_quant_N | y = 16,757 | 14,236-16,636 | 302-um channel N of hb_quant | 25,477 | 66,583 | 0.383 | xt_SW 2,068, xt_SW_0_q0n0 2,068, xt_SE 2,068 |
| hb_dbk_SW_W | x = 14,372 | 8,520-9,814 | 43-um channel W of hb_dbk_SW | 6,447 | 40,767 | 0.158 | lk_lk_S0_1_t12_q0n12 1,122, lk_lk_S1_1_t11_q0n4 1,122, vring_SE_SW_7_w0 1,088 |
| hb_dbk_SW_E | x = 14,712 | 8,520-9,814 | 49-um channel E of hb_dbk_SW | 4,060 | 40,767 | 0.100 | lk_lk_S1 1,122, vring_SW_SE_0_w1_q0n0 1,060, idx_score_SW_e_q0n0 610 |
| hb_dbk_SE_E | x = 17,748 | 8,520-9,814 | 43-um channel E of hb_dbk_SE | 6,656 | 40,767 | 0.163 | lw_SE 2,317, vdb_SE 2,065, vring_SW_SE_7_w1_q0n0_q1 1,060 |
| hb_dbk_NW_W | x = 14,372 | 16,069-17,363 | 43-um channel W of hb_dbk_NW | 10,918 | 40,767 | 0.268 | vdb_NW 2,065, hb_vm_su_SW 2,048, vrc_q_wup_w0_q0n0 1,136 |
| hb_dbk_NW_E | x = 14,712 | 16,069-17,363 | 49-um channel E of hb_dbk_NW | 12,464 | 40,767 | 0.306 | vxl_SW 2,065, hb_vm_su_SW 2,048, vrc_q_wup_w0 1,136 |
| hb_dbk_NE_E | x = 17,748 | 16,069-17,363 | 43-um channel E of hb_dbk_NE | 3,648 | 40,767 | 0.089 | vring_NE_NW_0_w0 1,088, vxl_NE_0_w0 1,040, vxl_NE_0_w1 1,025 |
| hb_vms_SW_W | x = 13,295 | 8,499-11,183 | 210-um channel W of hb_vms_SW | 20,579 | 84,599 | 0.243 | hgi_lgsw_wup 2,243, hgi_lgsw_tap_rdn_su_SW 2,065, hb_su_SW_vm_q0n1 2,048 |
| hb_vms_SW_E | x = 14,372 | 8,499-11,183 | 43-um channel E of hb_vms_SW | 14,447 | 84,599 | 0.171 | lk_lk_S0_1_t12_q0n3 1,122, lk_lk_S0_1_t12_q0n12 1,122, lk_lk_S1 1,122 |
| hb_vms_SE_W | x = 17,748 | 8,499-11,183 | 43-um channel W of hb_vms_SE | 19,830 | 84,599 | 0.234 | lw_SE 2,317, xt_SE 2,068, vdb_SE 2,065 |
| hb_vms_SE_E | x = 18,826 | 8,499-11,183 | 211-um channel E of hb_vms_SE | 24,647 | 84,599 | 0.291 | hgi_lgse_wup_1_3_t0_w0_q 2,272, hgi_lgse_wup 2,243, xt_SE_5_t2_q0n0 2,068 |
| hb_vms_NW_W | x = 13,295 | 14,700-17,385 | 210-um channel W of hb_vms_NW | 18,461 | 84,599 | 0.218 | tkm_del 4,360, hgi_lgnw_rdn 2,067, hb_vm_su_SW 2,048 |
| hb_vms_NW_E | x = 14,372 | 14,700-17,385 | 43-um channel E of hb_vms_NW | 35,319 | 84,599 | 0.417 | vring_NW_NE 2,148, vring_NE_NW 2,148, vxl_SW 2,065 |
| hb_vms_NE_W | x = 17,748 | 14,700-17,385 | 43-um channel W of hb_vms_NE | 18,754 | 84,599 | 0.222 | vrc_att_wup_3_w0_q0n0 1,136, vrc_att_wup_3_w1_q0n0 1,105, vcb_SE_NE_14_q0n0 1,088 |
| hb_vms_NE_E | x = 18,826 | 14,700-17,385 | 211-um channel E of hb_vms_NE | 9,342 | 84,599 | 0.110 | hgi_lgne_rdn 2,067, hb_vm_su_NE_t5_q0n3 2,048, hgi_lgne_wup_0_w0 1,136 |
| C_x3.8_y2.7 | y = 2,728 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 17,277 | 43,758 | 0.395 | rh_SW 1,623, wl_sm4 1,102, wl_sm5 1,102 |
| C_x7.5_y2.7 | y = 2,728 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 5,260 | 43,745 | 0.120 | wl_sm7_0_t1_q0n0 1,102, wl_sm3 1,099, xh_SW_2a 1,026 |
| C_x24.2_y2.7 | y = 2,728 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 16,139 | 43,745 | 0.369 | lw_SE 2,317, wl_sm12 1,102, wl_sm13 1,102 |
| C_x27.8_y2.7 | y = 2,728 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 11,060 | 43,745 | 0.253 | rt_SE 2,165, wl_sm15_0_t0_q0n0 1,102, wl_sm11 1,099 |
| C_x3.8_y5.1 | y = 5,070 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 9,441 | 43,758 | 0.216 | ks0_SW 1,102, ks1_SW 1,102, ks3_SW 1,102 |
| C_x7.5_y5.1 | y = 5,070 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 7,668 | 43,745 | 0.175 | lw_SW 2,317, xl_sm4_t0_q0n8 2,063, wl_sm7 1,099 |
| C_x24.2_y5.1 | y = 5,070 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 13,534 | 43,745 | 0.309 | lw_SE 2,317, xl_sm12_t0_q0n1 2,063, ks0_SE_2_t4_q0n0 1,102 |
| C_x27.8_y5.1 | y = 5,070 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 7,757 | 43,745 | 0.177 | rt_SE_0_t8_q0n0 2,165, ks3_SE_3_t2_q0n0 1,102, wl_sm15 1,099 |
| C_x3.8_y6.8 | y = 6,763 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 5,685 | 43,758 | 0.130 | ks0_SW 1,102, ks1_SW 1,102, ks2_SW 1,102 |
| C_x24.2_y6.8 | y = 6,763 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 9,978 | 43,745 | 0.228 | rt_SE 2,165, xl_sm15_q0n0 2,063, ks0_SE 1,102 |
| C_x3.8_y19.2 | y = 19,218 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 4,959 | 43,758 | 0.113 | xl_sm23_q0n0 2,063, ks5_NW_5_t4_q0n1 1,102, xl_sm22a_t12_q0n2 1,024 |
| C_x24.2_y19.2 | y = 19,218 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 6,729 | 43,745 | 0.154 | rt_NE 2,165, xl_sm31_q0n0 2,063, ks4_NE 1,102 |
| C_x3.8_y20.9 | y = 20,911 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 9,150 | 43,758 | 0.209 | rt_NW 2,165, ks5_NW 1,102, wl_sm22 1,099 |
| C_x7.5_y20.9 | y = 20,911 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 5,768 | 43,745 | 0.132 | ks4_NW 1,102, ks6_NW 1,102, ks7_NW 1,102 |
| C_x24.2_y20.9 | y = 20,911 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 6,648 | 43,745 | 0.152 | xl_sm28_q0n1 2,063, ks4_NE 1,102, wl_sm30 1,099 |
| C_x27.8_y20.9 | y = 20,911 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 11,987 | 43,745 | 0.274 | xl_sm30b 2,078, rh_NE 1,623, ks5_NE_2_t1_q0n2 1,102 |
| C_x3.8_y23.3 | y = 23,252 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 3,402 | 43,758 | 0.078 | wl_sm20 1,102, wl_sm21 1,102, wl_sm22 1,102 |
| C_x7.5_y23.3 | y = 23,252 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 5,536 | 43,745 | 0.127 | lw_NW 2,317, wl_sm23 1,102, ks7_NW 1,102 |
| C_x24.2_y23.3 | y = 23,252 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 4,864 | 43,745 | 0.111 | wl_sm28 1,102, wl_sm29 1,102, wl_sm30 1,102 |
| C_x27.8_y23.3 | y = 23,252 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 4,502 | 43,745 | 0.103 | wl_sm31 1,102, ks5_NE_0_t0_q0n0 1,102, ks6_NE 1,102 |

## SM column channels, channel-only figure (stations and channel-layer wires only, 18.2 tracks/um)

Informative: the die criterion is the table above (the die routes over the SMs on M8 / M9).

| cut | channel um | bits in the channel | tracks | ratio | classes |
|---|---|---:|---:|---:|---|
| C_x3.8_y2.7 | 3,839-4,272 | 17,277 | 7,870 | 2.19 | kv_rows 5,449, weight 3,306, x_trunk 3,110, x_leaf 3,102, result_trunk 1,623, result_leaf 540 |
| C_x7.5_y2.7 | 7,486-7,918 | 5,260 | 7,862 | 0.67 | weight 2,201, x_trunk 1,026, x_leaf 1,024, loader_mem 658, expert_req 258, weight_req 89 |
| C_x24.2_y2.7 | 24,204-24,636 | 16,139 | 7,862 | 2.05 | kv_rows 4,347, weight 3,306, x_trunk 3,094, loader_mem 2,962, x_leaf 2,048, weight_req 135 |
| C_x27.8_y2.7 | 27,850-28,282 | 11,060 | 7,862 | 1.41 | result_trunk 3,788, x_leaf 3,102, weight 2,201, x_trunk 1,042, control 450, result_leaf 270 |
| C_x3.8_y5.1 | 3,839-4,272 | 9,441 | 7,870 | 1.20 | kv_rows 4,347, x_trunk 2,068, weight 1,099, x_leaf 1,039, control 450, result_leaf 270 |
| C_x7.5_y5.1 | 7,486-7,918 | 7,668 | 7,862 | 0.97 | x_leaf 3,087, loader_mem 2,624, weight 1,099, result_leaf 810, weight_req 44, kv_credit 4 |
| C_x24.2_y5.1 | 24,204-24,636 | 13,534 | 7,862 | 1.72 | kv_rows 4,347, loader_mem 3,269, x_leaf 3,087, weight 1,099, x_trunk 1,026, result_leaf 540 |
| C_x27.8_y5.1 | 27,850-28,282 | 7,757 | 7,862 | 0.99 | result_trunk 2,165, kv_rows 1,102, weight 1,099, x_trunk 1,042, x_leaf 1,039, result_leaf 810 |
| C_x3.8_y6.8 | 3,839-4,272 | 5,685 | 7,870 | 0.72 | kv_rows 5,449, control_leaf 224, kv_credit 12 |
| C_x24.2_y6.8 | 24,204-24,636 | 9,978 | 7,862 | 1.27 | kv_rows 4,347, result_trunk 2,165, x_leaf 2,063, control 899, result_leaf 270, control_leaf 224 |
| C_x3.8_y19.2 | 3,839-4,272 | 4,959 | 7,870 | 0.63 | x_leaf 3,087, kv_rows 1,102, result_leaf 540, control_leaf 224, kv_credit 6 |
| C_x24.2_y19.2 | 24,204-24,636 | 6,729 | 7,862 | 0.86 | result_trunk 2,165, x_leaf 2,063, kv_rows 1,102, control 899, result_leaf 270, control_leaf 224 |
| C_x3.8_y20.9 | 3,839-4,272 | 9,150 | 7,870 | 1.16 | result_trunk 2,705, x_trunk 2,068, kv_rows 1,102, weight 1,099, x_leaf 1,024, result_leaf 540 |
| C_x7.5_y20.9 | 7,486-7,918 | 5,768 | 7,862 | 0.73 | kv_rows 3,306, weight 1,099, x_leaf 1,039, result_leaf 270, weight_req 44, kv_credit 10 |
| C_x24.2_y20.9 | 24,204-24,636 | 6,648 | 7,862 | 0.85 | x_leaf 3,087, kv_rows 1,102, weight 1,099, loader_mem 658, result_leaf 540, control_leaf 112 |
| C_x27.8_y20.9 | 27,850-28,282 | 11,987 | 7,862 | 1.52 | kv_rows 3,306, x_leaf 3,117, x_trunk 2,068, result_trunk 1,623, weight 1,099, control 450 |
| C_x3.8_y23.3 | 3,839-4,272 | 3,402 | 7,870 | 0.43 | weight 3,306, weight_req 90, kv_credit 6 |
| C_x7.5_y23.3 | 7,486-7,918 | 5,536 | 7,862 | 0.70 | loader_mem 2,975, weight 1,102, kv_rows 1,102, expert_req 258, weight_req 89, kv_credit 10 |
| C_x24.2_y23.3 | 24,204-24,636 | 4,864 | 7,862 | 0.62 | weight 3,306, kv_rows 1,102, loader_mem 364, weight_req 90, kv_credit 2 |
| C_x27.8_y23.3 | 27,850-28,282 | 4,502 | 7,862 | 0.57 | kv_rows 2,204, weight 2,201, weight_req 89, kv_credit 8 |
