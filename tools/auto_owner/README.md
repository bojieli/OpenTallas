# AUTO-OWNER (owner 2026-10-18)

Every open element of the current dies must have a live job or a live owner, without a human noticing.

- `element_owner_watch.py`: computes ACTIVE / STALE / UNOWNED for every open current-die element (fleet-viz `/api/elements`), takes the automatic actions (main's `submit_exact` for passing non-critical kits, gate-and-submit for kits without a gate, `flow_failure` resubmits of admitted re-routes, critical tiles to `lanes/COORD-REVIEW-QUEUE.md`) and writes `UNOWNED.json`, the input contract for the coordinator's hourly check: every element with `needs_agent: true` gets a fresh family agent.
- `release_tree_render.py`: the release-tree renderer (fleet-viz `/release`) with the ACTIVE / STALE / UNOWNED banner.
- `systemd/`: `element-owner-watch.{service,timer}` (user units, every 30 min).

Deployed copies run from `~/claude-takeover-20261007/tools/`; this directory is the version-controlled source.
