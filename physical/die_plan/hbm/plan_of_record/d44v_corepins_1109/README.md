# d44v_corepins_1109: HBM final plan d44v_final4_1109 + event corepins_1109

Built by DIE-HBM-97 on 2026-11-09 with tools/core_pin_event.py (copied here). The input was d44v_final4_1109/die_plan.json.gz (sha256 77bbddd873546ac3). The ruling is COORD 11-09 04:4x, plus COUNT-ARCHIVE-2 RESULT RULINGS (4): the corepins pin delta goes into the d44v final as an EQ-gated plan event.

Plan `die_plan.json.gz` = sha256 3742832d6eb33412 (uncompressed). It differs from 77bbddd873546ac3 only in 24 hard_cores `pins_file` fields and the top-level `note`. No outline, origin, station or cycle changes.

| module | instances | new table | pins | moved |
|---|---|---|---|---|
| ot_wbq_root_g1 | 16 (q_hub_ne/nw u_wbk_Q__q{0,1}__r{0..3}__g1) | cores/ot_wbq_root_g1__216x129.6__vC5.json (d30c289f) | 1373 | 1075 (S M5 re-pitched 0.192, order kept) |
| ot_svgr_own | 8 (q_hub_ne/nw) | cores/ot_svgr_own__129.6x432__RF4T.json (74e165ee) | 4897 | 2395 |

EQ gate (the same as d44v_gqi): each table equals the signed kit's pins.json by name, 1373/1373 and 4897/4897. Layer differences: 0. Coordinates match up to the plan face inset of 0.096 um.
- rootg1c_vC5: kit pins sha256 57716eb4c8b8cb03, the same on epyc4 scratch and scratch2 hbm-cores-b/rootg1c_vC5_eco1/i1/pins.json.
- own_vRF4T: kit pins sha256 f218373ef5c8c9ad, the same on epyc6 scratch and scratch2 hbm-cores-b/own_RF4T_eco1b/i1/pins.json.

Use: this holds the full plan, so it replaces d44v_final4_1109 as the HBM final. For a counter on d44v_gqi, overlay the two cores/ tables and the 24 pins_file fields listed in corepins_1109_event.json. Host types q_hub_ne/q_hub_nw re-key to 3742832d6eb33412; no other type changes.
