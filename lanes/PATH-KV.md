# PATH-KV -- one complete KV path (owner priority 10-25 08:10)
Lane started 2026-10-25 08:10 PDT (Claude). Plan base codex/kv-plan-0719@b0b916f1d (v3.9g/f7); own branch claude/path-kv-1025,
sparse WT epyc1:/srv/opentallas-scratch2/claude/wt/path-kv-1025, scratch epyc1:/srv/opentallas-scratch2/claude/path-kv.
Path: PC_EN_0 (kvpc0 h_head_p, kvpc1..3 kvs_pc) -> PHY_EN_0, HG_EN_0/HGI_EN_0 heads 0..3, ASTK_EN in hub_Eo, sys_c UCIe + 4 SRAM.
"Signed off" = GEOM PASS + route + TT setup / FF hold sign-off (per-corner basis) + bound in die (+ token exercises it).

## Item list (state at 08:10; updated in place)
| # | item | type/master | state | owner / next |
|---|------|-------------|-------|--------------|
| P1 | pc_EN_0 | kv3_pc (G2 12.1/um proven) | NEEDS-KIT (no face err) | kit after C1/C2 recut lands |
| P2 | phy_EN_0 | kv3_phy | NEEDS-KIT (no face err) | kit; ck_phy PHY pad/adapters only |
| P3 | hg_EN_0 | kv3_hg (G2 13.2 proven) | NEEDS-KIT (no face err) | kit after head masters |
| P4 | hgi_EN_0 | kv3_hgi_v3 (no G2) | G0C FAIL 4 face errors (N/S L2045 522b@70um, E L2075_1 1056b@85um, W L2075_2 1056b@106um) | PATH-KV structural re-window |
| P5 | hub_Eo | kv3_hub_Eo (no G2; 0 face err) | G2 f5 LIVE epyc1 unit 2069954 | collect G2; kit |
| P6 | sys_c | kv3_sys_c | NEEDS-KIT; 5-macro detour WIP 0ed44e59d; PHY PG domain hook NOT written | kits; PG hook |
| C1 | kvpc0 core | qkd_kvs_pc_h_head_p | FIX: shared 305 + ft 1 open (recut 4c6e890d93, WIP 5dc2556f5 local-only, tree pruned) | PC recut |
| C2 | kvpc1..3 core | qkd_kvs_pc | FIX: shared 1085 + ft 1 open (o_prev +1 hop, o_grp copies) | PC recut |
| C3 | head even master e0 (HID/BSEL straps) | kv3_head_eighth_e0 | autopilot ROUTING 3ffc2afa4c46 (old variant?); master not signed | KV-HEADCLK |
| C4 | head even master e2 | kv3_head_eighth_e2 | GEOM-REQ; FF hold -10..-15 structural verdict (regional tap/lane) | KV-HEADCLK |
| C5 | head even master e6 (serves e4) | kv3_head_eighth_e6 | diagnostic only TT -71.64 / FF -73.96, no per-corner basis | structural: per-lane taps + MCMM basis |
| C6-C9 | odd heads e1/e3/e5/e7 | kv3_head_eighth_e{1,3,5,7} | SIGNED (historical views) | verify pins == f7, bind |
| C10 | ECTLK q0..q3 in hg | qkd_ectlk | FIX (pin drop 413->271 approved) | KV-CORES |
| C11 | ASTK_EN | kv3_astk master (strap_corner 11) | LEC PASS 28432/28432, fanout <=64; TT -61.24 (WRITE-addr zn3.tq->sd) FF -54.96 | structural write/decode fix |
| M1 | sys_c macros | UCIe 777.6^2 + 4x d2d_sram_64x137 | views present; placement proposal PASS-COND | with P6 |
| D1 | plan G0C | f7 | FAIL 20 face errors (6 no-G2 types) | PATH-KV |
| D2 | native bind | f5 run3/run4 | graph complete; FAIL 14 TYPE_SPLIT (79 fn vs 40 phys) | KV parent |
| D3 | R8 landing | f5 run3 | FAIL 3 families (hg_v1 cal_exp, pc/pc_v1 x_tok) | KV parent |
| T1 | START bootstrap role | reset_tree start_role | DEADLOCK: global START gates HOST/hub_Wi bootstrap | CLOCK-RESET |
| T2 | KV boot160 (whole E) | kv43abcd vehicle | LIVE epyc2 unit oth-ubuntu-2377587-1792938490 (384 GB/16 thr) | collect |
| T3 | token pass on this path | QC<->KV link sys_c.u_ucie_rom | not started (needs T1, QC peer) | PATH-QC + PATH-KV |
Signed off now: 4 of 25 (odd heads e1/e3/e5/e7, historical views; f7 pin equality still to verify).
2026-10-25 08:11 PDT FLOW-INFRA/DIE-PROTO -> PATH-KV: qwen_kvsys die-top GRT (plan ee1aee20 = main) overflow 0 (M4-M7 all 0; usage M6 10.7%/M7 8.7%) BUT render vs 25% FT share peaks 1.86 on M6 (4643 windows>1) in two vertical FT trunks x~3.5/7mm y14-26mm + y12-13.5 cross band; 240 slots/12042 bits over 405um after GRT -> per-bit lattice successor (KV). Clock 2.27/2.46 PASS; die STA ideal+tree TT live epyc1. claude/die-proto-1025@bd51e6310 results/die_proto_1025/SUMMARY.md
