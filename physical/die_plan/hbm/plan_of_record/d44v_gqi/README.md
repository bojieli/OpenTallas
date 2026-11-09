# d44v_gqi: HBM plan of record d44v_epm + event gqi8_1108

Built by HBM-HARD-9, 2026-11-08, with tools/die_plan/drop_face_shell_pins.py at main c8fb6dec7cf, from d44v_epm/die_plan.json.gz and d44v/cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_split.json.gz.

ot_hgi_coll_gqi_issue (4 instances, q_hub_ne/nw u_hcollgi_Q__q0/1__i) pin table drops aq0_e[9:8] and aq1_e[9:8] (dead inputs: RTL truncates to 8 bits, HBM-HARD-7 18:31 proof). 6618 -> 6614 pins, remaining pins and sites unchanged; the table equals the signed kit pins.json by name. Same outline, no stations, no cycles. Holds only the changed files; use it as the last overlay after d35a, d35b, d35c, d44v, d44v_epm.

Counter: makes the existing re-signed routed view (intel1 hbm-hard-6/resign/gqi_vLF2_np1_fc) match, with no rebuild.
