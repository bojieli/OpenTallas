# Handoff to Codex: WITHDRAWN (2026-10-05)

The owner took the route iterations of this die back from Codex. **Claude (HBM-DS-DIE) owns the DeepSeek HBM accelerator die floorplan and its global-route loop.** Codex must not run the r8 route loop that this file used to describe, and must not launch new cases under `/srv/opentallas-scratch/claude/hbm-die-floorplan/` or `/srv/opentallas-scratch2/scratch/claude/hbm-ds-die-grt/`.

The r8 loop is obsolete for three reasons. Each was found in r9-r14 (see `README.md`, round history):

- **Geometry defect.** The north SM groups' row 1 abutted the hub band; the south side had a 259 um channel there. Every r8 overflow sat on that one boundary line.
- **Pin defect.** Shared hub masters (SU / SFU / HC quarters, index quarters, attention tiles) took every pin from their SW copy. The other copies' quadrant-named ports did not exist: 128 net endpoints had no pin in r8.
- **Face defect.** The E-side quarters were placed R0. Their spine-facing pins sat on the face away from the spine, which forced the SU-to-endpoint detours (53 stages against 4).

Element owners swapping a placeholder for a hardened abstract should hand the new LEF to Claude, who re-runs the round.
