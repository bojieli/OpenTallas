# KV-CAL15 10-20: KV die schedule admission of the route-A per-tile cycle deltas
Gate tools/qwen_kv_die/kvcal15_emb_die_gate.sh @9efbbd54d on ot-epyc6 (Verilator 5.050, verilator.txt): PASS
(p_die GEN9 i13a relays + HROOT_LAND + root/join skew 1 + PIPE_JOIN, p_land LAND law, p_base GEN9 relays unlanded: 5 tokens x 65
join words at the compiled edge, exact data, no fault; mutants m1 no skew / m2 LAND return short / m3 PJ unpriced / m4 relays 0 FAIL).
Relays from ep6 kvs14r-0203e2a07-i13a/case_kv/relay_stages.json (down WS/WN/ES/EN 82/24/71/15, return 66/20/76/31, svc->ctl 4, svc->emb 3).
Embedding fill deadline (kv_static_programme.emb_fill): margin -158 (0 relays) / -320 (GEN9) / -323 (+LAND+PJ) edges vs the row header
slot 191 (+1 slot relay); embed window 272 -> 595 = +323 cycles on token period 249,600 (+0.13 %). See claude-takeover lanes/KV-CAL15.md.
