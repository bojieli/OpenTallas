# REBUILD-17 handoff 2026-11-13 19:32
The 17 = rejudge SIGNED rows on epyc5/6: S81 slice_station t17 t21 t22 t24__cl66b71008 t25 t26 t28 t29__cl2e5c855a t30__cl1653104c t30__cl6a190133 t40__cl1ea9de02 t40__clc8fb2c8c t42__cl4bd1432c t7__cl362204c4 t8; HEAD hd_spn_eshim_rx hd_spn_wshim_rx.
- Already credited (auto_resign SKIP): t30__cl1653104c t30__cl6a190133 t7__cl362204c4 hd_spn_eshim_rx hd_spn_wshim_rx.
- Live copy -> lanes/AUTO-RESIGN.tsv rows (lane REBUILD-17): t17 t21 t22 t24__cl66b71008 (epyc7 kw42/e5reloc). Check: python3 -I rt/tools/autopilot/auto_resign.py status | grep t17; RECORDED = counted next count. FAILED -> read the reason, no blind retry.
- No live routed DB, need rebuild (KIT-OPS-2 asked to add to s81 only_items; already in rebuild_counted): t25 t26 t28 t29__cl2e5c855a t40__cl1ea9de02 t40__clc8fb2c8c t42__cl4bd1432c t8. If not launched, run via ot-run from the e9eda32d41c recipe (plan block unchanged by B1).
- state.json repoint backup: autopilot/state.json.bak-rebuild17-1113 (jobs b7b4d7be1d4f 279a112ae199 e652ae23927e add9e17a1852 da1ca16acb3e daf102ec1455 27c10558bb44 dd82988cc115 got host_before_rebuild17/path_before_rebuild17).
- Lesson: archive of old-src kits = SIGNED-UNVERSIONED (no flow tag), not counted; counting needs re-sign (auto_resign / resign.py) on the same routed DB.
## 23:19 update
- 9 of 17 credited (auto_resign SKIP). KIT-OPS-3 fixed wave take_states/parent names (a99b8e0343a); 8 rebuilds launched on event 7073a6b4a59: t25 t26 t28 t29__cl2e5c855a t42__cl4bd1432c t8 routing/ENQUEUED; t40__cl1ea9de02 + t40__clc8fb2c8c no row yet (asked KIT-OPS-3).
- To finish: grep ~/coord/autopilot/log.txt for "ARCHIVED|PROMOTE .* s81/slice_station__<t>" dated after 11-13 23:00 and ~/coord/autopilot/signed.tsv; post a RESULT per item. A route that ends WAIT-PARENT/SIGNED-UNVERSIONED is re-signed by auto_resign (no action). Do not touch kit_wave_state.json or hand-launch.
