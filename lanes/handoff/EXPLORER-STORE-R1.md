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
