# PLACED-SCAN-1115 READY-ROWS: pv station form (11-15 10:3x PST)

For FABLE-PD-KV-0945 item 5 (143 pv ring bands cannot be 17.28 um): stations per matched group instead of a wider band. MEASURED on the placed `geom.tsv` of the 3 pv types that placed (kv3_pv a4, kv3_pv_v1n a7, kv3_pv_v8 a7); the other 13 pv types (v2, v3, v3n, v4, v6, v6n, v7, v12 ...) have no placed dump (failed place on the band class), so rows for them are by family: same family names, KV-PVGEN re-derives per type with `placed_scan.py --out` on the first placed 7u kit.

Form: per matched group (launch mean -> capture mean of the bits over 405 um), `stations = ceil(leg/405) - 1`, sites evenly on the x-then-y Manhattan leg, hop = leg/(stations+1) <= 405 um. Row layout = plan internal_stations (`conn`=`group:SRC->END`, from_um, to_um, regs_um). The ring-band occupants are the families `u_cland_*/u_ring.dch.u_dsel/y -> u_bin_*` (the band holds the landing ring mux; its output register runs 700-1,880 um to the bin): the station replaces the wider band. Full per-group rows: `<host>:/srv/opentallas-scratch2/claude/placed-scan-1115/runs/<type>_attempt_N/placed_scan_rows.json` (v1n epyc10, kv3_pv/v8 epyc2). Caveat: stations are by Manhattan leg of the placed positions (INFERENCE for 7u: the 7u placement moves the legs), no STA run. Cost = flops: sum below.

## kv3_pv_v1n: 4703 groups, 105 families, 9212 station sites; ring-band families 24 (47 sites)

| family (digits -> #) | groups | bits >405 | stations/group | leg um max | hop um | ring band |
|---|---|---|---|---|---|---|
| `u_pd#_i_vport_E_N_vo_d#_#.q->u_pvg#_p#` | 1639 | 1639 | 3 | 1347 | 405 |  |
| `u_pd#_i_astk_E_u_strip_g_er_chain_u_er_g_owner_N_u_owner_response_data_#.q->u_pvg#_p#` | 1304 | 1304 | 5 | 2270 | 405 |  |
| `u_pd#_i_vport_W_N_vo_d#_#.q->u_pvg#_p#` | 1051 | 1051 | 4 | 1741 | 405 |  |
| `u_cland_i_slg_E_N_rsp_d#/u_ring.dch.u_dsel/y->u_bin_i_slg_E_N_rsp_d#` | 1 | 954 | 2 | 812 | 271 | yes |
| `u_pv_u_T#Q#_#_r#.b->u_bout_o_pvw__u_TNQN_N_rN_b_d#` | 3 | 773 | 2 | 1092 | 386 |  |
| `u_pd#_i_pvw_u_ctl_cmd_#.q->u_pvg#_p#` | 249 | 606 | 4 | 1994 | 404 |  |
| `u_bin_i_slg_W_N_rsp->u_vport_W.d` | 1 | 586 | 2 | 994 | 331 |  |
| `u_cland_i_slg_W_N_rsp_d#/u_ring.dch.u_dsel/y->u_bin_i_slg_W_N_rsp_d#` | 1 | 576 | 1 | 728 | 364 | yes |
| `u_cland_i_slg_E_N_rsp/u_ring.dch.u_dsel/y->u_bin_i_slg_E_N_rsp` | 1 | 550 | 1 | 739 | 370 | yes |
| `u_bin_i_slg_W_N_rsp_d#->u_vport_W.d` | 1 | 535 | 2 | 1136 | 379 |  |
| `u_d#_vport_E_out_v_lo.q->u_pvg#_p#` | 4 | 512 | 2 | 1101 | 367 |  |
| `u_d#_vport_W_out_v_lo.q->u_pvg#_p#` | 4 | 512 | 2 | 996 | 332 |  |
| `u_cland_i_pvw__u_TNQN_N_rN_b_d#/u_ring.dch.u_dsel/y->u_bin_i_pvw__u_TNQN_N_rN_b_d#` | 2 | 510 | 1 | 625 | 312 | yes |
| `u_cland_i_slg_W_N_rsp/u_ring.dch.u_dsel/y->u_bin_i_slg_W_N_rsp` | 1 | 486 | 1 | 656 | 328 | yes |

## kv3_pv: 5264 groups, 43 families, 11694 station sites; ring-band families 5 (8 sites)

| family (digits -> #) | groups | bits >405 | stations/group | leg um max | hop um | ring band |
|---|---|---|---|---|---|---|
| `u_pd#_i_vport_W_N_vo_d#_#.q->u_pvg#_p#` | 1843 | 1843 | 4 | 1930 | 405 |  |
| `u_pd#_i_astk_E_u_strip_g_er_chain_u_er_g_owner_N_u_owner_response_data_#.q->u_pvg#_p#` | 1130 | 1130 | 4 | 1866 | 405 |  |
| `u_pv_u_T#Q#_#_r#.b->u_bout_o_pvw__u_TNQN_N_rN_b_d#` | 3 | 768 | 2 | 1113 | 371 |  |
| `u_pd#_i_vport_E_N_vo_d#_#.q->u_pvg#_p#` | 728 | 728 | 4 | 1792 | 405 |  |
| `u_pd#_i_vport_W_N_vo_#.q->u_pvg#_p#` | 596 | 596 | 4 | 1804 | 405 |  |
| `u_pd#_i_pvw_u_ctl_cmd_#.q->u_pvg#_p#` | 214 | 527 | 4 | 1797 | 404 |  |
| `u_pd#_i_vport_E_N_vo_#.q->u_pvg#_p#` | 405 | 405 | 3 | 1563 | 405 |  |
| `u_pv_u_T#Q#_#_r#.b->u_bout_o_pvw__u_TNQN_N_rN_b` | 1 | 256 | 2 | 815 | 272 |  |
| `u_cland_i_vport_E_N_vo_d#/u_ring.dch.u_dsel/y->u_bin_i_vport_E_N_vo_d#` | 2 | 227 | 1 | 778 | 389 | yes |
| `u_cland_i_astk_W__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data/u_ring.dch.u_dsel/y->u_bi` | 1 | 188 | 1 | 806 | 403 | yes |
| `u_bin_i_astk_W__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data->u_pvg#_p#` | 4 | 128 | 4 | 1632 | 388 |  |
| `u_pd#_i_astk_W_u_strip_g_er_chain_u_er_g_owner_N_u_owner_response_data_#.q->u_pvg#_p#` | 78 | 78 | 2 | 875 | 378 |  |
| `u_pd#_i_vport_W_N_vo_d#_#.r->u_pd#_i_vport_W_N_vo_d#_#.q` | 76 | 76 | 2 | 970 | 404 |  |
| `u_pd#_i_vport_E_N_vo_d#_#.r->u_pd#_i_vport_E_N_vo_d#_#.q` | 42 | 42 | 2 | 973 | 397 |  |

## kv3_pv_v8: 5566 groups, 46 families, 11280 station sites; ring-band families 7 (14 sites)

| family (digits -> #) | groups | bits >405 | stations/group | leg um max | hop um | ring band |
|---|---|---|---|---|---|---|
| `u_pd#_i_vport_E_N_vo_d#_#.q->u_pvg#_p#` | 2027 | 2027 | 4 | 1656 | 405 |  |
| `u_pd#_i_vport_W_N_vo_d#_#.q->u_pvg#_p#` | 2018 | 2018 | 4 | 1947 | 405 |  |
| `u_cland_ft#_i/u_ring.dch.u_dsel/y->u_ft_ft#_o_#` | 1 | 1056 | 2 | 969 | 323 | yes |
| `u_pv_u_T#Q#_#_r#.b->u_bout_o_pvw__u_TNQN_N_rN_b_d#` | 3 | 768 | 2 | 1097 | 366 |  |
| `u_pd#_i_vport_W_N_vo_#.q->u_pvg#_p#` | 664 | 664 | 4 | 1933 | 405 |  |
| `u_pd#_i_vport_E_N_vo_#.q->u_pvg#_p#` | 404 | 404 | 3 | 1538 | 405 |  |
| `u_bin_i_pvw__u_ctl_cmd->u_pvg#_p#` | 5 | 290 | 4 | 1736 | 358 |  |
| `u_pv_u_T#Q#_#_r#.b->u_bout_o_pvw__u_TNQN_N_rN_b` | 1 | 256 | 2 | 838 | 279 |  |
| `u_pd#_i_pvw_u_ctl_cmd_#.q->u_pvg#_p#` | 100 | 252 | 3 | 1296 | 405 |  |
| `u_cland_i_astk_W__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data/u_ring.dch.u_dsel/y->u_bi` | 1 | 183 | 2 | 1043 | 348 | yes |
| `u_cland_i_astk_E__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data/u_ring.dch.u_dsel/y->u_bi` | 1 | 182 | 2 | 1086 | 362 | yes |
| `u_pd#_i_vport_W_N_vo_d#_#.r->u_pd#_i_vport_W_N_vo_d#_#.q` | 92 | 92 | 1 | 675 | 338 |  |
| `u_bin_i_astk_E__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data->u_pvg#_p#` | 4 | 90 | 2 | 940 | 313 |  |
| `u_bin_i_astk_W__u_strip_g_er_chain_u_er_g_owner_N__u_owner_response_data->u_pvg#_p#` | 3 | 80 | 2 | 928 | 309 |  |

READY-ROWS to KV-102 (event) and KV-PVGEN (stages, proof). Family JSON: `~/coord/lanes/placed-scan-rows/<type>_families.json`. Per the 0945 stop list: no pv_v1n tap grid or stations copied to the other 15 types before one pv_v1n CTS result; these rows are the place-stage band answer, to be gated with the 7u event.