# KV-OPEN-FWDCLK handoff (Opus 5.5; family lane under KV-ALLFIX; started 2026-11-23 19:30 PST)
GOAL: FABLE-RC-KV 331a59eb item 2: KV forwarded landing clock (fclk) <= 330 ps on 16 types; ONE family row; ROW-REBASED to KV-ALLFIX with before/after per type. Due 22:30.
## Finding (19:35)
- Depth = landing master's own fclk insertion (clock_contract.json fclk pin, read by plan_timing_audit via core_clock_contract.load), not a tap.
- Exactly the 4 masters signed 11-14 are bad: kv_cland_w1057_ew_94a44 637.7 (hgi, hgi_v3/5/6/7/8, pv_v1n/v3n/v7/v1e), w1045_ns_ddbeb 617.6 (hgi_v6/7/8 ft8/ft4), w781_ns_9f2d9 604.9 (pv_v5/5n/5e/5ne), w288_ns_ad575 555.9 (pv_v6e/6ne). All 24 masters re-signed 11-15 = 96-208 ps.
## Fix = re-harden the 4 with the 11-15 recipe (tools/die_plan/cland_ring_master.py prep: related_clocks fclk), exact params, SAME module name/outline/pins (plan_of_record pins file, asserted equal).
- Work dir epyc11 L=/srv/opentallas-scratch2/claude/kv-open-fwdclk: wt (ot-lane-clone main f2156bb449), fwd_prep2.py + fwd_params.py, rk/<m>/kits/<m>_synth0, ck_contract.py (copy of kv-ringmac-r1).
- Then: ck_contract run tt/ff -> write clock_contract; export_view -> L/views/<m>; row ROWS_KV-OPEN-FWDCLK.py swaps lef/lib/budget_owner to physical/die_plan/qwen_kvsys/kvfwd_views_1123/<m> + clk tap insertion; overlay into tree; PRE + earlytap audit on base A2g (KV-ALLFIX: A2g = A2f + ISTPRICE).
