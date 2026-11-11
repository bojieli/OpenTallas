# INTENT SHEET KVLEAF (CPL-S81-SLICE, plan 99f40d35071d)

Delta: `delta_KVLEAF_99f40d35.json` sha256 `ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356`; adopted types 0/4.

**Dataflow.** leafdn_i0 -> u_vs (scatter) and u_vn.u_a (arbiter, staged) -> the 16 vp lanes g_ln[k].u_l (266/257 b
each way, all staged) ; u_vs <-> u_vsw (365 b staged) ; u_ve.u_m -> u_ve.u_s (401 b, 55 um) ; u_rxsf -> u_rxsb (96 b) ;
u_vs -> leafup_o0.  **Timing-critical pairs:** the 60-150 plan stations (arbiter <-> lanes, vs <-> vsw).  **Intended
layout:** arbiter central to its 16 lanes, ve.m/ve.s abutted, vs between its face window and vsw.  The earlier free
search shortened bit-mm but broke ve.m->ve.s (55 -> 798 um) and other chain links; under the intent constraints no
legal move beats the plan -> KEEP (no delta).  KVLEAF-T2 (soft, 0 cores): N windows leafdn_i0 597 b / leafup_o0 668 b
have 60/181 um macro clearance (23/26 um needed), station bands macro-free (+10.8 halo), cuts 0.11/0.08 -> OK, no change.

## Per type

| type | moved | bit-mm | worst cut V/H | entry | rs p99 | chain corr | longer links | SVG |
|---|---|---|---|---|---|---|---|---|
| ot_s81sl_kv_leaf__t1 | 0 | 2269.3 -> 2269.3 | 0.16/0.271 -> 0.16/0.271 | 0.386 -> 0.386 | 1.024 -> 1.024 | -0.453 -> -0.453 | 0 | ot_s81sl_kv_leaf__t1_after.svg |
| ot_s81sl_kv_leaf__t3 | 0 | 2895.6 -> 2895.6 | 0.234/0.318 -> 0.234/0.318 | 1.207 -> 1.207 | 1.103 -> 1.103 | -0.409 -> -0.409 | 0 | ot_s81sl_kv_leaf__t3_after.svg |
| ot_s81sl_kv_leaf__t4 | 0 | 2249.6 -> 2249.6 | 0.163/0.292 -> 0.163/0.292 | 0.656 -> 0.656 | 1.121 -> 1.121 | -0.455 -> -0.455 | 0 | ot_s81sl_kv_leaf__t4_after.svg |
| ot_s81sl_kv_leaf__t5 | 0 | 3409.1 -> 3409.1 | 0.241/0.195 -> 0.241/0.195 | 0.546 -> 0.546 | 1.297 -> 1.297 | 0.351 -> 0.351 | 0 | ot_s81sl_kv_leaf__t5_after.svg |

## Dataflow links of ot_s81sl_kv_leaf__t1 (top 30 by bits; length um before -> after)

| src | dst | bits | role | len |
|---|---|---|---|---|
| core:u_lf.u_ve.u_m | core:u_lf.u_ve.u_s | 401 | p2p | 98 -> 98 |
| core:u_lf.u_vs | core:u_lf.u_vsw | 364 | p2p (staged station) | 304 -> 304 |
| core:u_lf.u_vp.g_ln[11].u_l | core:u_lf.u_vn.u_a | 266 | p2p (staged station) | 601 -> 601 |
| core:u_lf.u_vp.g_ln[12].u_l | core:u_lf.u_vn.u_a | 266 | p2p (staged station) | 601 -> 601 |
| core:u_lf.u_vn.u_a | core:u_lf.u_vp.g_ln[11].u_l | 257 | p2p (staged station) | 551 -> 551 |
| core:u_lf.u_vn.u_a | core:u_lf.u_vp.g_ln[12].u_l | 257 | p2p (staged station) | 551 -> 551 |
| core:u_lf.u_vn.u_a | core:u_lf.u_vp.g_ln[14].u_l | 256 | p2p (staged station) | 544 -> 544 |
| core:u_lf.u_vn.u_a | core:u_lf.u_vp.g_ln[15].u_l | 256 | p2p (staged station) | 544 -> 544 |
| core:u_lf.u_vp.g_ln[14].u_l | core:u_lf.u_vn.u_a | 256 | p2p (staged station) | 494 -> 494 |
| core:u_lf.u_vp.g_ln[15].u_l | core:u_lf.u_vn.u_a | 256 | p2p (staged station) | 494 -> 494 |
| face:leafdn_i0 | core:u_lf.u_vs | 165 | p2p (staged station) | 738 -> 738 |
| face:leafdn_i0 | core:u_lf.u_vn.u_a | 135 | p2p (staged station) | 593 -> 593 |
| core:u_lf.u_rxsb | core:u_lf.u_rxsf | 96 | p2p | 205 -> 205 |
| core:u_lf.u_vs | core:u_lf.u_ve.u_m | 96 | p2p | 212 -> 212 |
| macros@721,962 | core:u_lf.u_vn.u_a | 79 | p2p | 368 -> 368 |
| core:u_lf.u_vs | macros@566,617 | 76 | broadcast | 222 -> 222 |
| core:u_lf.u_vsw | core:u_lf.u_vs | 66 | p2p | 290 -> 290 |
| core:u_lf.u_vn.u_a | macros@721,962 | 48 | broadcast | 192 -> 192 |
| core:u_lf.u_ve.u_m | core:u_lf.u_vs | 41 | p2p | 339 -> 339 |
| core:u_lf.u_ve.u_s | core:u_lf.u_vs | 41 | p2p | 179 -> 179 |
| core:u_lf.u_rxsb | core:u_lf.u_vs | 33 | p2p | 359 -> 359 |
| core:u_lf.u_vs | core:u_lf.u_rxsf | 33 | p2p | 142 -> 142 |
| core:u_lf.u_vs | face:leafup_o0 | 19 | p2p (staged station) | 620 -> 620 |
| core:u_lf.u_vs | macros@721,962 | 18 | broadcast | 514 -> 514 |
| core:u_lf.u_vn.u_a | macros@566,617 | 16 | broadcast | 177 -> 177 |
| core:u_lf.u_vp.g_ln[12].u_l | core:u_lf.u_vp.g_ln[15].u_l | 15 | broadcast | 987 -> 987 |
| core:u_lf.u_vp.g_ln[13].u_l | core:u_lf.u_vp.g_ln[15].u_l | 15 | broadcast | 728 -> 728 |
| core:u_lf.u_vp.g_ln[14].u_l | core:u_lf.u_vp.g_ln[15].u_l | 15 | broadcast | 572 -> 572 |
| core:u_lf.u_vp.g_ln[0].u_l | core:u_lf.u_vp.g_ln[1].u_l | 15 | broadcast | 138 -> 138 |
| core:u_lf.u_vp.g_ln[1].u_l | core:u_lf.u_vp.g_ln[2].u_l | 15 | broadcast | 276 -> 276 |

## Timing-critical pairs of ot_s81sl_kv_leaf__t1

- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_v|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hw_v", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_v|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hw_v", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_j|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hw_j", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 3}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_j|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hw_j", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 3}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_hf|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hw_hf", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_hf|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hw_hf", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hw_d", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hw_d", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hq_v|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hq_v", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hq_v|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hq_v", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hq_d|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hq_d", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hq_d|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hq_d", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hq_d|core:u_lf.u_vp.g_ln[14].u_l", "launch": "core:u_lf.u_vn.u_a.hq_d", "capture": "u_lf.u_vp.g_ln[14].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hq_d|core:u_lf.u_vp.g_ln[15].u_l", "launch": "core:u_lf.u_vn.u_a.hq_d", "capture": "u_lf.u_vp.g_ln[15].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hr_v|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hr_v", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hr_v|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hr_v", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hr_j|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hr_j", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 3}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hr_j|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hr_j", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 3}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hr_hf|core:u_lf.u_vp.g_ln[11].u_l", "launch": "core:u_lf.u_vn.u_a.hr_hf", "capture": "u_lf.u_vp.g_ln[11].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hr_hf|core:u_lf.u_vp.g_ln[12].u_l", "launch": "core:u_lf.u_vn.u_a.hr_hf", "capture": "u_lf.u_vp.g_ln[12].u_l", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vn.u_a.n_go", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vn.u_a.n_pre", "stages": 1, "bits": 128}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vn.u_a.rb_v", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vn.u_a.rb_d", "stages": 1, "bits": 32}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vs.s_v", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vs.s_d", "stages": 1, "bits": 156}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vs.g_v", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vs.g_c", "stages": 1, "bits": 2}
- {"kind": "plan station", "conn": "bus:leafdn_i0", "launch": "face bus leafdn_i0", "capture": "u_lf.u_vs.g_d", "stages": 1, "bits": 32}
- {"kind": "plan station", "conn": "bus:leafup_o0", "launch": "face bus leafup_o0", "capture": "u_lf.u_vs.e_v", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "bus:leafup_o0", "launch": "face bus leafup_o0", "capture": "u_lf.u_vs.e_c", "stages": 1, "bits": 2}
- {"kind": "plan station", "conn": "bus:leafup_o0", "launch": "face bus leafup_o0", "capture": "u_lf.u_vs.e_d", "stages": 1, "bits": 96}
- {"kind": "plan station", "conn": "bus:leafup_o0", "launch": "face bus leafup_o0", "capture": "u_lf.u_vs.fault", "stages": 1, "bits": 1}
- {"kind": "plan station", "conn": "core:u_lf.u_vs.sw_d|core:u_lf.u_vsw", "launch": "core:u_lf.u_vs.sw_d", "capture": "u_lf.u_vsw.i_d", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[14].u_l", "launch": "core:u_lf.u_vn.u_a.hw_d", "capture": "u_lf.u_vp.g_ln[14].u_l", "stages": 1, "bits": 256}
- {"kind": "plan station", "conn": "core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[15].u_l", "launch": "core:u_lf.u_vn.u_a.hw_d", "capture": "u_lf.u_vp.g_ln[15].u_l", "stages": 1, "bits": 256}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_lf.u_vp.g_ln[11].u_l", "dst": "core:u_lf.u_vn.u_a", "bits": 266, "len_before": 601, "len_after": 601}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_lf.u_vp.g_ln[12].u_l", "dst": "core:u_lf.u_vn.u_a", "bits": 266, "len_before": 601, "len_after": 601}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_lf.u_vn.u_a", "dst": "core:u_lf.u_vp.g_ln[11].u_l", "bits": 257, "len_before": 551, "len_after": 551}
- {"kind": "link beyond 396.9-um reach", "src": "core:u_lf.u_vn.u_a", "dst": "core:u_lf.u_vp.g_ln[12].u_l", "bits": 257, "len_before": 551, "len_after": 551}
