# TYPE-KVPCF (kv3_pc__cl5a95b461 / __cl254f2e73 PDN-0006) - 2026-11-14 08:28 PST
- 19:3x successor: private cl5a95b461 route waiting admission (epyc2); ctscan canary KV-102 epyc8 pending; waiter ~/typekvpcf/wait.sh
ROOT CAUSE (corrects the brief): the failing instance u_kvpc0_f is master qkd_kvs_pcf_h_head_p (not qkd_kvs_pcf). Its prov_view_sources list only epyc4 detail + epyc2 plain base, so the kit got the plain base LEF 575677ce (blanket M1-M7 OBS, 22770 um2 on M6 and M7) -> PDN-0006. qkd_kvs_pcf (a4c5fe6c, detail 2a908d42) is already fine.
FIX BUILT: detail view of pcf_h_head_p from signed ODB pcfh_k (ss29/resign/pcfh_k, odb sha = dkv100/pdncls/pcfh_sig/6_final.odb), M6 8400 / M7 3194 exact OBS, bloat 0, sha f57da6f7 (same as the lost epyc4 kv-types-6 receipt out). check_ok true with access-clear-um 0.035 (rst_n[0] M5 pin has a real 0.032 M6 wire across it; 0.08 um gaps either side; default 0.05 probe says no access, 0.035 passes, no window needed). Final DRC decides.
STAGED: epyc9 + epyc10 /srv/opentallas-scratch2/claude/kvpcf-view-1114/qkd_kvs_pcf_h_head_p (lef, libs, pins, core.json, detail_view.lef, detail_receipt.json).
PDN PROOF (epyc10 probe /srv/opentallas-scratch2/claude/type-kvpcf/probe): baseline 2_3 tapcell odb + pdn.tcl + pdngen reproduces PDN-0006 for u_kvpc0_f; with detail view swapped (DEF round trip) pdngen exits 0, only PDN-0007 partial (2.8-3.9 %) + PDN-0110 notes.
NEXT: KIT-OPS-3 puts the epyc9/epyc10 entries FIRST in kit_wave.json dies.qwen_kvsys.prov_view_sources.qkd_kvs_pcf_h_head_p + retry keys for the pc types; then follow to R-MINIMAL and add AUTO-RESIGN rows.

## 2026-11-14 16:43 PST status
- Fix confirmed in real kits: both kv3_pc types passed 2_4_floorplan_pdn with the detailed pcf_h view (PDN-0007 only). Wave cl254f2e73 (a2/a3/a4, view 581413 B) and private cl5a95b461 (epyc2 /srv/opentallas-scratch3/claude/type-kvpcf/cl5a95b461/kv3_pc__cl5a95b461, OT_ALLOW_RESYNTH=1) both reached CTS.
- cl254f2e73 wave: post-CTS gate lost to earlyoom (infra-oom) twice, attempt 4 launched 16:28. Not a PDN problem.
- cl5a95b461 private: in 4_1_cts at 16:40; waiter armed for FAIL/signoff. Wave a2 of cl5a95b461 died at PDN-0006 (old view), ignore.
- AUTO-RESIGN: no row yet (no sign-off).
