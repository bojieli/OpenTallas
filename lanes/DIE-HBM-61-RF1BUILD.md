# DIE-HBM-61/RF1-BUILD (helper of DIE-HBM-61), started 2026-11-03 19:06 PST
Scope: one HBM-RF1 conservative-form build per non-SPLIT, non-tailx, non-LEC hard-set core. Routed via KW-FIX-4 item_args.
- 2026-11-03 19:37 PST: branch claude/die-hbm-61-rf1-1103@d35a67594c7 (epyc4 wt /srv/opentallas-scratch2/claude/wt/die-hbm-61-rf1). Class fixes: q2_reduce d44v oneclk wrapper; llr RW if-generate names (cp_rxs MPL-0020); RF1 clock regions (+4 derived modules).
- RF1 regions file: /srv/opentallas-scratch2/claude/kit-wave/hbm/rf1_1103/core_clock_regions_rf1.json (intel2+epyc4, sha 69ed115a). Smoke kits: epyc4 .../rf1_1103/smoke (12/12 gen rc 0).
- Recipe sent to KW-FIX-4 for 12 items. Dropped per DIE-HBM-61 19:1x (clock band only, CTS resume): vm_query_n12, vmdel_lane_n, qcore_r13, sfustore_hw, ctlx, cxport_ij_q.
- 2026-11-03 20:22 PST: RESULT posted; 12/12 launched (6 ot-run epyc4 + 6 wave). Kits epyc4 /srv/opentallas-scratch2/claude/kit-wave/hbm/rf1_1103/kits; logs intel2 ~/rf1_1103_logs.
