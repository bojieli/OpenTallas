# Captured-stage continuation; no full GEN

The strict saved-health stage passed on ep5 under unit `oth-ubuntu-1853164-1792617163` at 8 GB. Original F, original 406.8 um failure and both archived binding inputs remain immutable.

Exact objects:

- Original F: `/home/ubuntu/ot-scratch/claude/qwen-kvsys/kvs14r-c6520b2ee-dsg6f`.
- Repaired health stage: `/home/ubuntu/ot-scratch/claude/codex-k-die-1340/health_replay/run`.
- Health source/view readset: sibling `source/`, `readset_manifest.json`, `profiles.json`.
- Original two-view binder replay: `/home/ubuntu/ot-scratch/claude/codex-k-die-1340/s6c_rebind`; actual native S6C pair passed at source repair `14c536c0d`.

The pipeline supports resuming at this boundary: `kvsys_prep.sh` imports native tile views before expansion/FWD/health; F stopped at the final `kv_tile_views.py check` after health. The saved prehealth LEF therefore already contains the other native tile imports. No tile RTL or native view was changed by either repair.

Publisher preparation for a new successor (never mutate original F):

1. Use a fresh source tree at the published source repair, keeping the actual c652 selected RTL/views and its exact `kv_flags.env`. In particular final-reset-stations stays OFF, c83 PLL fix/HOLD273 remain selected, and this is EMB_WIN595 intermediate.
2. Copy original F's `case_kv`, `libs`, `lint`, and required top-level JSON/env/source records into a new successor. Retain original records separately; do not carry old health failure as a new result.
3. Overlay the repaired health stage's `case_kv/{die.v,place.tcl,elements.lef,die.v.pads.json,die.v.params.json}`, `expand.json`, `health_plane.json`, `health_successor.json` and health-generated libs/`views.json`. The readset manifest records original source files at copy time; the replay deliberately removes old hp parameter-instance entries before emitting the new health tree.
4. Re-run only the two S6C view imports with `bind_views.bind` under actual `KV._set_geometry(True)`, and merge those two records into successor `libs/views.json`. Keep all other original native binding records, source identities and selected views. The strict private-slice correction is `14c536c0d`. Do not replace the whole binding catalog with a two-view-only report. The health case currently still has the original stale two S6C frame macros; importing those views is necessary.
5. Continue the existing post-health PREP commands: final orientation check, native PHY, clocks, `die_port_bind_kv`, `kv_port_bind_v2.sh`, final `kv_tile_views.py check`, window/source-direction/safety exports. These are the normal continuation gates, not a new proof campaign. Keep reset stations OFF. Generate fresh strict-bind records from the repaired die; old FAIL/PASS files cannot stand in for this step.
6. Only after the actual continuation gates pass, use the existing `kvs14r.sh` post-PREP chain: FWD price/age exports, actual reset-window hops, PHY PG application, actual die clock regions and `die_chain.sh` with TT/FF STA. Source provenance must explicitly name captured c652 GEN plus these two generator repairs and the saved-stage hashes. Do not claim a new full GEN or clean-from-zero build.

The health latency price is per leaf. All 298 old/new ages are in `receipt.json` and `health_plane.json`; the worst source `rly_est__f26_28__s0.fault` is 112 -> 113 and requires STATUS1913, within reserved1998. Existing STATUS delay213 and padded period257280 still fit. The original failing f16 source is94 ->95. Other leaf changes range -3..+4; there is no blanket +1. The actual loaded reset release requirement still needs the normal continued die/reset receipt.

Current scope: required saved health PASS; whole-die strict bind, GRT, STA and loaded clock/reset remain PENDING. Actual reticle/per-bit/source contracts remain their separate obligations. No coherent73 image, HEAD ages or STATUS225 transport ages are inferred from this595 case.
