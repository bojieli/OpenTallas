# PCC B1 commit lane spec (generator input), class C-PC-PHY-INGRESS
COORD 11-27: the lane enters via the next KV plan regeneration (CBC assigns windows and ft slots); no delta on D, no hand-written windows.
Spec: PCC-B1-LANE-SPEC.json. Source u_kvpc3 (qkd_kvs_pcc) pcc_b1_commit[90:0] on pc_EN_2/pc_ES_2; 91 bits; route pc hops -> hroot -> hub_Eo -> hub_Ei -> hub_C -> hub_Wi, then stock L751 (hub_Wi -> hgi_WN -> io_W3 -> sys_c) into K SFM port1 kind11. Budget <= ~103 edges (est 77-80 + aggregation). Default-off, single-context.
RTL dependencies: leaf port via rf_kv3_split.py --b1-commit-export; 91 PCC-face pin-table entries (RF-KV1 plan path pending from KV-INT-R3); owner aggregation; HOST kind11 sender + C kind11 decoder (token-r2/kind11 sha12 77e9ccff5166); K port1 mux and C landing patches.
Gates after regeneration: G0, PRE, strict bind, LATCHECK, P-HOOK-RTL-NET, visual reviews.
