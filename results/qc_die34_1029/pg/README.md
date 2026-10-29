# DIE-QC-34 — QC provider mixed PG materialization (QC-001 step 2)

Source: Codex QC import reach-fixed provider ODB intel2 `/srv/opentallas-scratch2/claude/codex-qc-import-0824/reachfix/provider/provider.odb`
(sha256 ddab9669…74ca) + Codex complete PG contact candidate `reachfix/pg_candidate` (185,698 contacts, 109,168 groups,
2,947,537 rects, 873,344 vias, 1 M3-jog group). Run root intel2 `/srv/opentallas-scratch2/claude/die-qc34`.
Codex `mixed_apply_access.py` is used UNCHANGED (copy here for pinning).

## Root causes of the Codex "Shapely ABI" failure (three, all environment/harness, none in the PG plan)
1. **Python ABI**: Codex `pydeps` holds cp312 wheels (shapely 2.2.0, numpy 2.5.4, installed from `python:3.12`), but the
   OpenROAD in `openroad/orfs:asap7lock` embeds **Python 3.10.12** (`libpython3.10.so`, EXT_SUFFIX `.cpython-310`), so
   `shapely.lib` (a `cpython-312` .so) is invisible -> `ModuleNotFoundError: shapely.lib`. Fix: `pydeps310` =
   `pip3 install --target --only-binary shapely==2.0.6 numpy<2.3` run inside the same image (Python 3.10). CHECKED.
2. **Float grid match (vehicle)**: `readback/pg_rects.json` stores accumulated-float coordinates (e.g. 11897.615999999885
   for 11897.616); the vehicle's containment test in um failed 49,434/109,168 groups by < 1e-9 um. In integer dbu
   (round(v*1000), as `mixed_apply_access` already does) 0 groups fail (`diag2.py`). Patched in the vehicle only.
3. **Vehicle connectivity model**: the scoped check required each cell's own M1 rail to overlap an access M1 pad;
   a multi-cell rail group (b190: 2 INV + NOR + DFF) has one stack, and the other members reach it through their
   ABUTTING native M1 rails. Patched: contact cells' M1 rails are records, touching edges union.
   Negative control `mixed_import_vehicle_mut.py` (VIA12 of the b190 VDD stack removed) -> FAIL on that contact (CAUGHT).
   Failed logs kept: `run.fail_connectcheck.log`, `full/run.fail_import.log` (missing tools path), `full/run.fail_nogrid.log`.

## Results (own runs, CHECKED; independent NUMBER-CHECK not yet)
- Scoped vehicle (6 cells, 12 contacts incl. M3 jog): PASS_MIXED_ACTUAL_PG_MECHANISM, re-apply idempotent (0 added),
  changed-provider-body control rejected, non-PG hash unchanged (`summary.json`).
- Full materialization (`materialize_full.py`, unit oth-ubuntu-1925056, 68 s): canonical M8/M9 grid 13,304 stripes
  materialized from `readback/pg_rects.json` (provider.odb carries no top grid), then `apply_access` on all
  185,698 contacts / 48,259 provider + 44,590 CKINV cells: added 2,602,853 rects (rest identical-dup) + 867,296 vias,
  non-PG hash before == after (cf78b75a…), out `fullpg_mat/provider_pg.odb` sha256 96515c35…2fe.
- Whole-die contact connectivity census (`pg_conn_census.py`, unit oth-ubuntu-2041155, 101 s):
  **VDD 92,849/92,849, VSS 92,849/92,849 contacts reach a canonical M8/M9 stripe; 0 failed** (`full/census.json`).

## Not established
Canonical M8<->M9 grid vias are not in `pg_rects.json` (grid stays 5,829/5,794 components per net here): whole-grid
continuity, native-cell PG (44,967 native cells, bridges), DRC, IR, clock route are later steps. No freeze claim.
