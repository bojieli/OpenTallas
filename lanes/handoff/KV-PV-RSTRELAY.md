# KV-PV-RSTRELAY handoff (Opus 5.5, from COORD split 21:1x PST, FABLE-RC-KV ruling 21:12)
Job: -721 reset relay path u_rrl_54 -> u_cland_fstart_* (pv_v3 D28 kit) as its own family row on the KV-ALLFIX plan.
## Cause (measured)
- v3 kit epyc10 .../KV-D28/private/OPUS-FIX-KV-PV-R7/kv3_pv_v3_1122231545/gen/kv3_pv_v3 4_cts_post_hook.rpt: u_rrl_54 = tap 111 relay, depth 11, Q rst_n_t111 at (37.8,1458.5); all 11 chain stages on that one site. rst_n_t111 = cland_start_raw = sync raw reset of all 11 FSTART face flops (ot_dp_landing_relay). 34 BUFx6/x16 stages, ~1460 ps wire, arrival 1806 vs req 1085 -> -721.
- Family (A3f bind census): every pv type with FSTART flops (pv, v1, v12, v2, v2n, v3, v3n, v4, v4n, v5, v5n, v6, v6n, v7, v8) takes cland_start_raw from ONE relay, 1.5-2.4 mm Manhattan from far FSTART pins; only v1n has clock.landing_raw_branches. The branches were stripped at re-floors (recipe: strip, strict bind, kv_start_corridor_event raw) and never re-derived for pv.
## Row
- Form: existing DIE-KV-58 clock.landing_raw_branches via rt tools/die_plan/kv_start_corridor_event.py raw --bind-rtl <strict bind of base> (same-depth literal copies, 0 cycles, +flops only, LEC same release cycle).
- Lane dir epyc10 /srv/opentallas-scratch2/claude/kv-pv-rstrelay (dry*.sh, row_A3g.sh, pre_A3g.sh, bind_A3g.sh, ROWS_KV-PV-RSTRELAY.py).
- Base: KV-ALLFIX A3g plan b258e3e34f22 (grow/A3g/plan.json), ABN asbuilt_allfix_A3f.json, rt 9b19260c1cde. Bind of A3g needed (gate_A3g running).
## Log
- 21:11 TAKING. 21:22 census + dry run on A3f bind: 14/15 pass, v5 base site on macro clearance ring.
- 21:34 row ROWS_KV-PV-RSTRELAY.py e0cf2bbd9aad on A3g bind: 15 types, 422 branches, 1255 copies, max hop 300, 0 cycles; plan b258e3e34f22 -> 3d130f381902 (epyc10 kv-pv-rstrelay/A3g/plan.json, report rstrelay_report.json). PRE running (pre_A3g.sh, also base PRE for diff). Scoped strict bind script bind_A3g.sh waits for A3g gate end (ALLFIX: fork tree after its gate), then ot-tree-fork grow/tree -> kv-pv-rstrelay/tree.
