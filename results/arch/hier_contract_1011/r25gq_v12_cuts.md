# R25GQ r25gqn_v12: bits per cut

Model: `tools/hbm_r25gq_cuts.py` (capacity of results/arch/hbm_b2_1012 SPEC 6a: 0.75 of M8 / M9 over the whole line + 0.75 of M6 / M7 and 0.5 of M4 / M5 in its channels; a bus crosses a line when the line separates the nearest points of its two end boxes).

**64 cuts, worst 0.502, limit 0.60: PASS**

| cut | line | window um | what | bits | tracks | util | largest buses |
|---|---|---|---|---:|---:|---:|---|
| X_centre_full | x = 16,492 | 0-25,979 | full die | 40,757 | 601,598 | 0.068 | vrc_att_wup 2,241, vcb_SE_NE 2,176, vring_SW_SE 2,148 |
| Y_centre_full | y = 12,990 | 0-32,984 | full die | 57,952 | 923,362 | 0.063 | xh_SW 4,136, hgi_su_cmd 2,198, tkm_del 2,180 |
| x12_hub | x = 12,000 | 10,000-16,000 | hub line (cuts_v07) | 10,421 | 105,402 | 0.099 | tkm_del 2,180, xt_SW 2,068, vmap_SW 1,200 |
| x13_hub | x = 13,000 | 10,000-16,000 | hub line (cuts_v07) | 18,231 | 105,402 | 0.173 | hgi_lgsw_wup_1_0_r00 2,243, hgi_lgnw_wup_1 2,243, tkm_del 2,180 |
| x14_hub | x = 14,000 | 10,000-16,000 | hub line (cuts_v07) | 26,296 | 156,226 | 0.168 | hgi_su_cmd 2,198, tkm_del 2,180, xt_SW 2,068 |
| x14.4_hub | x = 14,400 | 10,000-16,000 | hub line (cuts_v07) | 38,845 | 189,062 | 0.205 | vrc_cp_wup 2,241, hgi_su_cmd 2,198, tkm_del 2,180 |
| x15_hub | x = 15,000 | 10,000-16,000 | hub line (cuts_v07) | 11,766 | 117,230 | 0.100 | vring_NW_NE 2,148, vring_NE_NW 2,148, xt_SW 2,068 |
| x15.5_hub | x = 15,500 | 10,000-16,000 | hub line (cuts_v07) | 11,052 | 117,230 | 0.094 | vring_NW_NE 2,148, vring_NE_NW 2,148, xt_SW 2,068 |
| x16_hub | x = 16,000 | 10,000-16,000 | hub line (cuts_v07) | 11,742 | 117,230 | 0.100 | vring_NW_NE 2,148, vring_NE_NW 2,148, xt_SW 2,068 |
| x16.5_hub | x = 16,500 | 10,000-16,000 | hub line (cuts_v07) | 18,365 | 189,062 | 0.097 | vrc_att_wup 2,241, vcb_SE_NE 2,176, vring_NW_NE 2,148 |
| x17_hub | x = 17,000 | 10,000-16,000 | hub line (cuts_v07) | 34,616 | 154,398 | 0.224 | vring_SE_NE 4,296, vring_NE_SE 4,296, vrc_att_wup 2,241 |
| x18_hub | x = 18,000 | 10,000-16,000 | hub line (cuts_v07) | 15,083 | 121,562 | 0.124 | xt_SE 2,068, hb_vm_su_SE 2,048, hb_su_SE_vm 2,048 |
| y10_hub | y = 10,000 | 12,000-18,000 | hub line (cuts_v07) | 17,014 | 130,261 | 0.131 | lk_lk_S0 3,366, hgi_lgsw_wup_1 2,243, hgi_idx_cmd 2,075 |
| y11_hub | y = 11,000 | 12,000-18,000 | hub line (cuts_v07) | 39,815 | 158,081 | 0.252 | hgi_lgsw_wup_1 2,243, vrc_hce_wup 2,241, hgi_su_cmd_t10_r00 2,198 |
| y12_hub | y = 12,000 | 12,000-18,000 | hub line (cuts_v07) | 37,429 | 131,753 | 0.284 | hgi_lgsw_wup_1 2,243, vrc_hce_wup 2,241, hgi_su_cmd 2,198 |
| y12.5_hub | y = 12,500 | 12,000-18,000 | hub line (cuts_v07) | 44,927 | 162,367 | 0.277 | hgi_su_cmd 2,198, tkm_del 2,180, vring_SW_NW 2,148 |
| y13_hub | y = 13,000 | 12,000-18,000 | hub line (cuts_v07) | 44,985 | 162,367 | 0.277 | hgi_su_cmd 2,198, tkm_del 2,180, vring_SW_NW 2,148 |
| y14_hub | y = 14,000 | 12,000-18,000 | hub line (cuts_v07) | 48,262 | 162,735 | 0.297 | hgi_su_cmd 2,198, tkm_del 2,180, vring_SW_NW 2,148 |
| y14.6_hub | y = 14,600 | 12,000-18,000 | hub line (cuts_v07) | 52,601 | 131,753 | 0.399 | hgi_lgnw_wup_1 6,729, hgi_lgnw_rdn_1 6,201, tkm_del 2,180 |
| y15_hub | y = 15,000 | 12,000-18,000 | hub line (cuts_v07) | 44,083 | 158,081 | 0.279 | vrc_att_rdn 4,130, lk_lk_N2 2,244, tkm_del 2,180 |
| y16_hub | y = 16,000 | 12,000-18,000 | hub line (cuts_v07) | 36,408 | 105,622 | 0.345 | lk_lk_N2 3,366, hgi_lgnw_wup 2,243, hgi_lgnw_wup_1 2,243 |
| hb_tkm_W | x = 8,566 | 15,778-18,622 | 235-um channel W of hb_tkm | 2,694 | 89,636 | 0.030 | rt_NW 2,165, tr_NW0 529 |
| hb_tkm_E | x = 11,056 | 15,778-18,622 | 235-um channel E of hb_tkm | 6,206 | 89,636 | 0.069 | rt_NW 2,165, xt_NW 2,068, ct_NW 899 |
| hb_coll_E | x = 16,465 | 10,402-12,963 | 658-um channel E of hb_coll | 5,651 | 80,720 | 0.070 | vcb_coll_SE 1,088, hb_su_SE_coll 1,024, hb_su_SW_su_SE 1,024 |
| hb_coll_S | y = 10,750 | 14,236-16,636 | 302-um channel S of hb_coll | 16,966 | 75,614 | 0.224 | hgi_idx_cmd 2,075, lk_lk_S0 1,122, lk_lk_S1 1,122 |
| hb_cmdproc_W | x = 14,543 | 13,834-16,238 | 386-um channel W of hb_cmdproc | 36,396 | 75,750 | 0.480 | lk_lk_N2 3,366, lk_lk_N0 2,244, vrc_cp_wup 2,241 |
| hb_cmdproc_N | y = 15,848 | 14,236-16,636 | 220-um channel N of hb_cmdproc | 9,269 | 73,086 | 0.127 | xt_SE 2,068, hgi_quant_cmd 1,216, lk_lk_N2 1,122 |
| hb_quant_W | x = 14,712 | 15,458-17,106 | 49-um channel W of hb_quant | 23,257 | 51,929 | 0.448 | vrc_q_wup 2,241, vring_NW_NE 2,148, vring_NE_NW 2,148 |
| hb_quant_S | y = 15,848 | 14,236-16,636 | 220-um channel S of hb_quant | 9,269 | 73,086 | 0.127 | xt_SE 2,068, hgi_quant_cmd 1,216, lk_lk_N2 1,122 |
| hb_quant_N | y = 16,757 | 14,236-16,636 | 302-um channel N of hb_quant | 7,044 | 66,583 | 0.106 | xt_SW 2,068, hb_vm_su_SE 2,048, ct_NE 899 |
| hb_dbk_SW_W | x = 14,372 | 8,520-9,814 | 43-um channel W of hb_dbk_SW | 13,949 | 40,767 | 0.342 | lw_SW 2,317, vring_SW_SE 2,148, vring_SE_SW 2,148 |
| hb_dbk_SW_E | x = 14,712 | 8,520-9,814 | 49-um channel E of hb_dbk_SW | 7,300 | 40,767 | 0.179 | vring_SW_SE 2,148, vring_SE_SW 2,148, idx_score_SW 610 |
| hb_dbk_SE_E | x = 17,748 | 8,520-9,814 | 43-um channel E of hb_dbk_SE | 9,675 | 40,767 | 0.237 | lw_SE 2,317, vring_SW_SE 2,148, vring_SE_SW 2,148 |
| hb_dbk_NW_W | x = 14,372 | 16,069-17,363 | 43-um channel W of hb_dbk_NW | 11,917 | 40,767 | 0.292 | vxl_SW 2,065, vxl_NW 2,065, vdb_NW 2,065 |
| hb_dbk_NW_E | x = 14,712 | 16,069-17,363 | 49-um channel E of hb_dbk_NW | 13,700 | 40,767 | 0.336 | vrc_q_wup 2,241, vrc_q_rdn 2,065, vxl_SW 2,065 |
| hb_dbk_NE_E | x = 17,748 | 16,069-17,363 | 43-um channel E of hb_dbk_NE | 4,621 | 40,767 | 0.113 | vxl_NE 2,065, vdb_NE 2,065, dbk_mv_NE 229 |
| hb_vms_SW_W | x = 13,295 | 8,499-11,183 | 210-um channel W of hb_vms_SW | 31,492 | 84,599 | 0.372 | hgi_lgsw_wup_1 8,972, hgi_lgsw_rdn_1 8,268, hgi_su_cmd_t10_r00 2,198 |
| hb_vms_SW_E | x = 14,372 | 8,499-11,183 | 43-um channel E of hb_vms_SW | 23,675 | 84,599 | 0.280 | lw_SW 2,317, lk_lk_S0 2,244, lk_lk_S1 2,244 |
| hb_vms_SE_W | x = 17,748 | 8,499-11,183 | 43-um channel W of hb_vms_SE | 22,977 | 84,599 | 0.272 | lw_SE 2,317, vring_NE_SE 2,148, vring_SW_SE 2,148 |
| hb_vms_SE_E | x = 18,826 | 8,499-11,183 | 211-um channel E of hb_vms_SE | 17,620 | 84,599 | 0.208 | xt_SE 4,136, hgi_lgse_wup 2,243, hgi_lgse_rdn 2,067 |
| hb_vms_NW_W | x = 13,295 | 14,700-17,385 | 210-um channel W of hb_vms_NW | 19,481 | 84,599 | 0.230 | hgi_lgnw_wup 2,243, hgi_lgnw_wup_1 2,243, tkm_del 2,180 |
| hb_vms_NW_E | x = 14,372 | 14,700-17,385 | 43-um channel E of hb_vms_NW | 42,454 | 84,599 | 0.502 | vxl_SW 6,195, vrc_cp_wup 2,241, vrc_q_wup 2,241 |
| hb_vms_NE_W | x = 17,748 | 14,700-17,385 | 43-um channel W of hb_vms_NE | 19,875 | 84,599 | 0.235 | vrc_att_wup 2,241, vring_SE_NE 2,148, vring_NE_SE 2,148 |
| hb_vms_NE_E | x = 18,826 | 14,700-17,385 | 211-um channel E of hb_vms_NE | 16,883 | 84,599 | 0.200 | hgi_lgne_wup_1 4,486, hgi_lgne_wup 2,243, hgi_lgne_rdn 2,067 |
| C_x3.8_y2.7 | y = 2,728 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 17,005 | 43,758 | 0.389 | rh_SW 1,623, wl_sm4 1,102, wl_sm5 1,102 |
| C_x7.5_y2.7 | y = 2,728 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 7,446 | 43,745 | 0.170 | lw_SW 2,317, wl_sm7 1,102, wl_sm3 1,099 |
| C_x24.2_y2.7 | y = 2,728 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 13,916 | 43,745 | 0.318 | lw_SE 2,317, wl_sm12 1,102, wl_sm13 1,102 |
| C_x27.8_y2.7 | y = 2,728 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 12,160 | 43,745 | 0.278 | rt_SE 2,165, rh_SE 1,623, wl_sm15 1,102 |
| C_x3.8_y5.1 | y = 5,070 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 9,131 | 43,758 | 0.209 | ks0_SW 1,102, ks1_SW 1,102, ks2_SW 1,102 |
| C_x7.5_y5.1 | y = 5,070 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 6,619 | 43,745 | 0.151 | lw_SW 2,317, wl_sm7 1,099, xh_SW_2a 1,026 |
| C_x24.2_y5.1 | y = 5,070 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 10,781 | 43,745 | 0.246 | lw_SE 2,317, ks0_SE 1,102, ks1_SE 1,102 |
| C_x27.8_y5.1 | y = 5,070 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 6,385 | 43,745 | 0.146 | rt_SE 2,165, wl_sm15 1,099, xh_SE_3b 1,042 |
| C_x3.8_y6.8 | y = 6,763 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 7,525 | 43,758 | 0.172 | xh_SW 2,068, ks0_SW 1,102, ks1_SW 1,102 |
| C_x24.2_y6.8 | y = 6,763 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 6,041 | 43,745 | 0.138 | ks0_SE 1,102, ks1_SE 1,102, ks2_SE 1,102 |
| C_x3.8_y19.2 | y = 19,218 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 3,271 | 43,758 | 0.075 | rt_NW 2,165, ks5_NW 1,102, kdNW_1 2 |
| C_x24.2_y19.2 | y = 19,218 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 4,170 | 43,745 | 0.095 | rt_NE 2,165, ks4_NE 1,102, cd_NE 899 |
| C_x3.8_y20.9 | y = 20,911 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 9,805 | 43,758 | 0.224 | rt_NW 2,165, ks5_NW 1,102, wl_sm22 1,099 |
| C_x7.5_y20.9 | y = 20,911 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 4,459 | 43,745 | 0.102 | ks4_NW 1,102, ks6_NW 1,102, ks7_NW 1,102 |
| C_x24.2_y20.9 | y = 20,911 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 5,626 | 43,745 | 0.129 | ks4_NE 1,102, wl_sm30 1,099, xh_NE_3b 1,042 |
| C_x27.8_y20.9 | y = 20,911 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 5,101 | 43,745 | 0.117 | ks6_NE 1,102, ks7_NE 1,102, wl_sm31 1,099 |
| C_x3.8_y23.3 | y = 23,252 | 2,232-5,879 | SM column channel 3839-4272 (cut C), +- half an SM | 3,441 | 43,758 | 0.079 | wl_sm20 1,102, ks5_NW 1,102, wl_sm19 1,099 |
| C_x7.5_y23.3 | y = 23,252 | 5,879-9,525 | SM column channel 7486-7918 (cut C), +- half an SM | 5,607 | 43,745 | 0.128 | wl_sm21 1,102, wl_sm23 1,102, ks4_NW 1,102 |
| C_x24.2_y23.3 | y = 23,252 | 22,597-26,243 | SM column channel 24204-24636 (cut C), +- half an SM | 4,500 | 43,745 | 0.103 | wl_sm28 1,102, wl_sm30 1,102, ks4_NE 1,102 |
| C_x27.8_y23.3 | y = 23,252 | 26,243-29,889 | SM column channel 27850-28282 (cut C), +- half an SM | 3,405 | 43,745 | 0.078 | ks5_NE 1,102, ks6_NE 1,102, ks7_NE 1,102 |

## SM column channels, channel-only figure (stations and channel-layer wires only, 18.2 tracks/um)

Informative: the die criterion is the table above (the die routes over the SMs on M8 / M9).

| cut | channel um | bits in the channel | tracks | ratio | classes |
|---|---|---:|---:|---:|---|
| C_x3.8_y2.7 | 3,839-4,272 | 17,005 | 7,870 | 2.16 | kv_rows 5,449, weight 3,306, x_trunk 3,110, x_leaf 3,102, result_trunk 1,623, result_leaf 270 |
| C_x7.5_y2.7 | 7,486-7,918 | 7,446 | 7,862 | 0.95 | loader_mem 2,975, weight 2,201, x_trunk 1,026, x_leaf 1,024, expert_req 129, weight_req 89 |
| C_x24.2_y2.7 | 24,204-24,636 | 13,916 | 7,862 | 1.77 | weight 3,306, kv_rows 3,245, x_trunk 3,094, loader_mem 2,975, x_leaf 1,024, weight_req 135 |
| C_x27.8_y2.7 | 27,850-28,282 | 12,160 | 7,862 | 1.55 | result_trunk 3,788, x_leaf 3,102, weight 2,201, kv_rows 1,102, x_trunk 1,042, control 450 |
| C_x3.8_y5.1 | 3,839-4,272 | 9,131 | 7,870 | 1.16 | kv_rows 5,449, weight 1,099, x_trunk 1,042, x_leaf 1,039, control 450, weight_req 44 |
| C_x7.5_y5.1 | 7,486-7,918 | 6,619 | 7,862 | 0.84 | loader_mem 2,624, weight 1,099, x_trunk 1,026, x_leaf 1,024, result_leaf 540, expert_req 258 |
| C_x24.2_y5.1 | 24,204-24,636 | 10,781 | 7,862 | 1.37 | kv_rows 4,347, loader_mem 2,975, weight 1,099, x_trunk 1,026, x_leaf 1,024, expert_req 258 |
| C_x27.8_y5.1 | 27,850-28,282 | 6,385 | 7,862 | 0.81 | result_trunk 2,165, weight 1,099, x_trunk 1,042, x_leaf 1,039, result_leaf 540, control 450 |
| C_x3.8_y6.8 | 3,839-4,272 | 7,525 | 7,870 | 0.96 | kv_rows 5,449, x_trunk 2,068, kv_credit 8 |
| C_x24.2_y6.8 | 24,204-24,636 | 6,041 | 7,862 | 0.77 | kv_rows 4,347, control 899, loader_mem 658, expert_req 129, kv_credit 8 |
| C_x3.8_y19.2 | 3,839-4,272 | 3,271 | 7,870 | 0.42 | result_trunk 2,165, kv_rows 1,102, kv_credit 4 |
| C_x24.2_y19.2 | 24,204-24,636 | 4,170 | 7,862 | 0.53 | result_trunk 2,165, kv_rows 1,102, control 899, kv_credit 4 |
| C_x3.8_y20.9 | 3,839-4,272 | 9,805 | 7,870 | 1.25 | result_trunk 2,705, x_trunk 2,068, x_leaf 2,063, kv_rows 1,102, weight 1,099, control 450 |
| C_x7.5_y20.9 | 7,486-7,918 | 4,459 | 7,862 | 0.57 | kv_rows 3,306, weight 1,099, weight_req 44, kv_credit 10 |
| C_x24.2_y20.9 | 24,204-24,636 | 5,626 | 7,862 | 0.72 | x_leaf 2,063, kv_rows 1,102, weight 1,099, x_trunk 1,042, result_leaf 270, weight_req 44 |
| C_x27.8_y20.9 | 27,850-28,282 | 5,101 | 7,862 | 0.65 | kv_rows 2,204, weight 1,099, x_trunk 1,026, control 450, result_leaf 270, weight_req 44 |
| C_x3.8_y23.3 | 3,839-4,272 | 3,441 | 7,870 | 0.44 | weight 2,201, kv_rows 1,102, weight_req 134, kv_credit 4 |
| C_x7.5_y23.3 | 7,486-7,918 | 5,607 | 7,862 | 0.71 | kv_rows 3,306, weight 2,204, weight_req 89, kv_credit 8 |
| C_x24.2_y23.3 | 24,204-24,636 | 4,500 | 7,862 | 0.57 | weight 3,303, kv_rows 1,102, weight_req 89, kv_credit 6 |
| C_x27.8_y23.3 | 27,850-28,282 | 3,405 | 7,862 | 0.43 | kv_rows 3,306, weight_req 89, kv_credit 10 |
