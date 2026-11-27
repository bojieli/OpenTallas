# EXPLORER-STORE-R1 handoff (Opus, COORD lane)

Goal: every signed-off record on ANY plan shows its routed layout on the explorer (https://opentallas.01.me).

## State (2026-11-22 03:0x PST)
- LV store created: epyc8 /srv/opentallas-scratch2/claude/explorer-2-work/store (2.3 TB free disk).
- Live explorer (explorer-fable.service, epyc8:8770 -> rtx-pro ssh -L 8765 -> cloudflared opentallas.01.me) now runs
  pinned main worktree epyc8:/srv/opentallas-scratch2/claude/explorer-store-r1/srv (main 787530142d). Unit backup:
  explorer-store-r1/explorer-fable.service.bak-1122. Public URL checked 200.
- Port 7860: nothing configured anywhere (cloudflared config, systemd units on rtx-pro/epyc8/intel2, crontabs, repo). Not brought up.
- main 787530142d: tools/fleet_viz/any_plan_records.py + server.py (/api/v1/records, any_plan in archive/summary + dies,
  superseded_records in closure, superseded nodes open) + auto_export.py step 5 (view-packs worker: every new 'done'
  unit is cut on its build host under ot-run and published to the store). Tests: test_any_plan_records.py, test_auto_export_viewpack.py.
- Packs, three sources:
  1. AGIdock _view-packs copy-out (read only, via intel2, 6.5 GB) -> store/incoming-agi -> alias_agi.py publishes under
     record ids (332 ids from the INDEX pack column + 379 AGIdock element ids).
  2. dispatcher on rtx-pro ~/.local/state/explorer-store-r1/dispatch.py (state.json, dispatch.log): 196 records without a
     pack + 12 current sign-offs without an INDEX row; DB = record's own build DB if still on its host, else streamed (zstd)
     from rtx-pro signed-export-1114; cut under ot-run, 2 per host (intel1 epyc2 epyc7 epyc8 epyc9 epyc10); publish on epyc8.
  3. new sign-offs: AUTO-EXPORT step 5 (hub, automatic).
- Host runtime for cuts: <scratch>/claude/explorer-store-r1/{venv (brotli), bin/node, tmp/} on every gen host
  (scratch2 path on all hosts = OT_VIEWPACK_ROOT default).
## Next
- when the dispatcher ends: rerun failures once (dispatch.py todo_cut.json), reconcile state from the store, start
  explorer2-refresh.service so index nodes carry layout.store, report coverage per die (signed / archived / viewable).
- known: qwen_compute.t.phy_serdes / phy_serdes_b / phy_ucie_kv are 2 KB placeholder DBs (hard IP, not counted).

## Result (2026-11-23)
- Any-plan viewable 565/572 (archived 571). Per die signed/archived/viewable: s81 142/142/141, head 41/41/41,
  qc 194/193/188, kv 103/103/103, hbm 92/92/92. Before: 0/545 (store missing).
- Not viewable: qc phy_serdes, phy_serdes_b, phy_ucie_kv (2 KB hard-IP placeholder DBs, not real layouts);
  qc qfd_qc_su_lane_w_l1_m44s1_views (cut admission failure, retry); 3 sign-offs newer than the backfill
  (qc sle_hc1__cl22c1ff36__pve289215f, slw_fe_v1__cl95cd1d0c, s81 slice_station__t51) -> AUTO-EXPORT step 5.
- main 4b5f6e510b: step 5 now calls ot-run by path (hub timer PATH lacked ~/.local/bin: every queued cut failed until
  then; those jobs retry on the next drain once rt/current carries the fix).
- Not archived: qwen_compute.t.coll_ftc (no AGIdock row / rtx-pro record found).

## Recovery after the 2026-11-26 cleanup

- E8's exact live store was deleted by the FLEET-OPS-R4 manual `ot-delete` pass started at 22:44:09 UTC. The directory was absent by 23:01:44 UTC. The delete manifest and retained input tar are under E8 `~/.local/state/delete-manifests/2026-11-26/224409-ot-delete-srv_opentallas-scratch2_claude_explorer-2-work_store.*`. The tar preserved 444 element indexes and 420 other element metadata files, with zero compressed object blobs.
- Restored the canonical configured store path `/srv/opentallas-scratch2/claude/explorer-2-work/store` from real retained layout objects. The exact root is listed in hub PROTECTED-DBS.txt (ed300e8edb6), in E8's live deletion policy, and carries its own `.keep`. No service path or terminology change was needed.
- First 5 signed geometries and second 28 retained geometries were restored with individual geometry-blob SHA-256 matches. Missing optional archive timing-overlay blobs are omitted using the native no-timing manifest representation. Original deleted and archive metadata are retained in E8 `explorer-store-r1/recovery-1126`. At 19:56 PST, 38 complete element indexes were present and 34/605 signed records were viewable (572 archived). S81 9, HEAD 3, QC 14, KV 3, HBM 5. Public Element browser checks for S81, KV and HBM passed after the first tranche.
- The standard E8 ot-run bulk native archive transfer is `oth-ubuntu-1835581-1795750921`. Its rtx-pro managed finalizer `explorer-store-r1-bulk-finalize-1126.service` waits for exact success, installs additional complete records, regenerates the actual cut ledger under its native lock, refreshes the Explorer index, and records final coverage.
- The existing dispatcher runs 235 archive-backed missing layout cuts against retained signed DBs only, two per host, on intel1, epyc7, epyc8, epyc10 and epyc11. No E9, E2 or E12 recovery clients remain. Controller state/log are rtx-pro `~/.local/state/explorer-store-r1/recovery-1126/{state-approved.json,dispatch-approved.log}`. First stock cuts are publishing. Compare actual viewable/archived/signed via `/api/v1/archive/summary`; do not infer closure from presence of a pack.
- At 20:18 PST the direct exact tranches reached 151 complete layout indexes, with 138/605 signed records viewable (134 current, 4 superseded). S81 34, HEAD 13, QC 43, KV 16, HBM 32. The bulk verified native transfer had populated 48/256 object-prefix buckets. Large approved recuts are making progress, including HEAD hd_mesh's completed IDENTICAL cut at 1,177s. The rtx-pro managed `explorer-store-r1-recuts-finalize-1126.service` waits for the dispatcher and retries eligible transient failures once.
- An independent archive-join repair identified exact archived source matches for all 605 census records; its source deployment is separate. Metadata and guarded alias intake for 27 retired cores and five exact special identities is on E8 in `explorer-store-r1/recovery-1126/canonical-exact-aliases.json` and `canonical-explorer-aliases.py`. Aliases require an exact retained signed DB label and IDENTICAL live routed pack, or a verified retained AGIdock pack after its transfer. The TRX identities are four distinct xoffs and cannot share one base pack. The genuine TRX and FTC variant packs are already covered by the approved dispatcher.
- Latest observed at 20:40 PST: 218/605 signed records viewable, all 605 archive identities joined, 246 verified layout indexes. Actual per-die viewable S81 53, HEAD 20, QC 61, KV 34, HBM 50. Additional archived geometry transfers and ODB recuts are still in progress. Rtx-pro `explorer-store-r1-retained-drain-1126.service` processes successive exact signed geometry batches, refreshing the design index as each completes.
- Canonical recovery now reuses exact signed ODBs already queued for 61 additional historical IDs. E8 recovery source list is `canonical-exact-aliases.json` in `explorer-store-r1/recovery-1126`. The native producer writes `store/recovery-identities/<canonical-id>.json` using `opentallas.explorer.recovery_identity.v1`, census key, latest job, manifest hash, ODB hash and signed record hash. The optional `record_basis=signed-store` tags exact ODB/generated-receipt stock cache joins for legacy INDEX rows without IDs. Pack manifests and blobs remain immutable. Both bulk and recut finalizers run the canonical producer and re-index.
- Qualified supplemental bodies are in the managed second pass. The HBM q_spb1/q_spt2/vsN1 final ODBs match the stock count cache SHA-256 exactly. Stock count accepts their local SIGNED results with only io_hold_parent outstanding, so view recovery leaves full parent release unchanged. Both exact KV suffix ODBs were fetched from the durable archive with stock target SHA verification on E8. The three QC hard-IP placeholder receipts have no routable ODB. The legacy qfd_qc_su_lane_w_l1_m44s1_views archive has a LEF and abstract metadata only, so the OpenDB failure is terminal for that alias and omitted from retries.

- At 22:06 PST Explorer served 314/605 signed layouts and exact archive joins for all 605. Verified target coverage is 601 of 605 across retained packs, native recuts and exact aliases. The excluded four are the three QC hard-IP placeholders and the LEF-only historical views record described above. E8 bulk transfer reached 203/256 object-prefix buckets at 22:05:47. Native dispatcher had published 113 and was running 10; the only recorded failure remains the diagnosed LEF. The retained tranche service drained successfully. The bulk and recut finalizers and the two-minute exact alias publisher (`explorer-store-r1-publish-follow-1126.service`) remain active.
- The two exact KV shapes use durable signed records, original ODB hashes and current pin-shape keys. Native Intel1 IDENTICAL jobs `6_final_b4bdac4480` (e2) and `6_final_ea66d52339` (PV join) are live in Explorer as of grouped source release `92084f8e4a8` at 22:06:30 PST. Their immutable association receipts use `record_basis=signed-store-exact-shape`. The two verified successes were removed from the standby recut list to avoid duplicate extraction.
- Bulk completed at 22:44:53 PST (E8 `oth-ubuntu-1835581-1795750921`, rc0) and native import completed at 23:14 PST (E8 `oth-ubuntu-535787-1795761906`, rc0). It restored complete objects for 392 of 395 retained AGIdock labels, left 641 total store indexes and rebuilt `cuts.json` through the stock ledger from 557 identical cuts. Public summary was 541 of 605 sign-offs viewable, 447 current and 94 superseded, with all 605 archive joins. Sixty of the 64 missing geometries are covered by the live native recut/alias queue. The remaining four are the three hard-IP stubs and the LEF-only historical view. FTC f6391a15ef and TRX xoff24 95a37e0cd9 now have their exact canonical native receipts. The final xoff8 variant remains queued.
- Recovery completed at 00:47 PST November 27. All 605 signed records join exact archives. Explorer serves 601 layouts, including all 484 current-plan sign-offs. Per die S81 148/148, HEAD 42/42, QC 209/213, KV 107/107, HBM 95/95. The four explicitly unavailable physical layouts are QC phy_serdes, phy_serdes_b and phy_ucie_kv hard-IP placeholders and the historical qfd_qc_su_lane_w_l1_m44s1_views LEF-only abstract.
- Final mismatches in two retired QC core aliases were separate same-name NOMCAP bodies. Native recuts used the exact archive record bodies, ODB 54371e709dc9 and 7ce62555f63b. E8 `oth-ubuntu-207576-1795768653` emitted both QC identity receipts and the older HEAD hd_turn_a receipt. Every TRX xoff and exact FTC body also serves independently.
- Three HBM exact signed records q_spb1, q_spt2 and vsN1 all cut IDENTICAL from retained native ODBs on E10, E8 and Intel1. This recovered their layouts while their enclosing-die parent timing remains pending for full release. The HBM jobs were split out of the pending second-pass manifest before launching independently. Both normal finalizers ended rc0 and the final stock refresh rebuilt 616 IDENTICAL cut entries. No recovery jobs remain.
