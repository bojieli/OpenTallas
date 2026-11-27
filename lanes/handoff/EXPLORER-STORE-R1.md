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

- E8's exact live store was deleted by the FLEET-OPS-R4 manual `ot-delete` pass at 22:44:09 UTC. The delete manifest and retained input tar are under E8 `~/.local/state/delete-manifests/2026-11-26/224409-ot-delete-srv_opentallas-scratch2_claude_explorer-2-work_store.*`. The tar preserved 444 element indexes and 420 other element metadata files, with zero compressed object blobs.
- Restored the canonical configured store path `/srv/opentallas-scratch2/claude/explorer-2-work/store` from real retained layout objects. The exact root is listed in hub PROTECTED-DBS.txt (ed300e8edb6), in E8's live deletion policy, and carries its own `.keep`. No service path or terminology change was needed.
- First 5 signed geometries and second 28 retained geometries were restored with individual geometry-blob SHA-256 matches. Missing optional archive timing-overlay blobs are omitted using the native no-timing manifest representation. Original deleted and archive metadata are retained in E8 `explorer-store-r1/recovery-1126`. At 19:56 PST, 38 complete element indexes were present and 34/605 signed records were viewable (572 archived). S81 9, HEAD 3, QC 14, KV 3, HBM 5. Public Element browser checks for S81, KV and HBM passed after the first tranche.
- The standard E8 ot-run bulk native archive transfer is `oth-ubuntu-1835581-1795750921`. Its rtx-pro managed finalizer `explorer-store-r1-bulk-finalize-1126.service` waits for exact success, installs additional complete records, regenerates the actual cut ledger under its native lock, refreshes the Explorer index, and records final coverage.
- The existing dispatcher runs 235 archive-backed missing layout cuts against retained signed DBs only, two per host, on intel1, epyc7, epyc8, epyc10 and epyc11. No E9, E2 or E12 recovery clients remain. Controller state/log are rtx-pro `~/.local/state/explorer-store-r1/recovery-1126/{state-approved.json,dispatch-approved.log}`. First stock cuts are publishing. Compare actual viewable/archived/signed via `/api/v1/archive/summary`; do not infer closure from presence of a pack.
- At 20:18 PST the direct exact tranches reached 151 complete layout indexes, with 138/605 signed records viewable (134 current, 4 superseded). S81 34, HEAD 13, QC 43, KV 16, HBM 32. The bulk verified native transfer had populated 48/256 object-prefix buckets. Large approved recuts are making progress, including HEAD hd_mesh's completed IDENTICAL cut at 1,177s. The rtx-pro managed `explorer-store-r1-recuts-finalize-1126.service` waits for the dispatcher and retries eligible transient failures once.
- An independent archive-join repair identified exact archived source matches for all 605 census records; its source deployment is separate. Metadata and guarded alias intake for 27 retired cores and five exact special identities is on E8 in `explorer-store-r1/recovery-1126/canonical-exact-aliases.json` and `canonical-explorer-aliases.py`. Aliases require an exact retained signed DB label and IDENTICAL live routed pack, or a verified retained AGIdock pack after its transfer. The TRX identities are four distinct xoffs and cannot share one base pack. The genuine TRX and FTC variant packs are already covered by the approved dispatcher.
