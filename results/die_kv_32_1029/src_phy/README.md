# KV-006 std-cell PG access: attribution + clean plan + die GRT0 launch (DIE-KV-32-SRC), 2026-10-29 11:53 PDT

Continues claude/die-kv-31-src-1029@0458c6b79. Runtime `intel1:/srv/opentallas-scratch2/claude/die-kv-32-1029/src_phy`. Inputs are read-only:
the DIE-KV-31 src_phy native_grid.odb and overlay.json, codex-kv-pg-0834 grid3_bbox, and the pgh tools.
Rules: COORD 11:12. M7 band_share_obs are a capacity model, so they are soft and charged per band (variant A form, fail if any band is >0.6).
The M8 die clock-leg reservations are real metal and stay HARD. Frozen plan event26a, fix-only. No hand edits.

## 1. Attribution of the variant-A failures (CHECKED, instrumented planner `scripts/plan_access_v32.py --m8-landing off`)
- The run reproduces variant A exactly: 35,970 ok / 9,220 failed groups. Buckets: 4,908 within 1.4 um of a clock leg; 201 within 5.4 um;
  217 within 10.8 um; **3,894 with no clock leg within 10.8 um**. The per-group blocker tags are in `receipts/summary_off.json` and `receipts/attrib_off.json`.
- **Root cause, common to all 9,220 groups: the M9 target selection in plan_access.py.** The planner takes `dst[:3]` = the 3 same-net M9 segments
  nearest in x. M9 PG columns (39.96-um pitch) are cut into y-segments, so all 3 segments are often cuts of ONE column, and none of them
  covers the landing y. Every candidate that cleared the M7 stem and the M8 landing then died at that check (`M9_stripe_y_range`). No candidate ever
  reached the bridge/M9-end checks.
  For the 3,894: 3,716 had all 3 segments in one column. 3,893 have a same-net M9 segment that covers the y but was not among the 3
  (nearest covering dx p50 23.3 um, max 65.0 um). 1 has no covering M9 segment at all.
- Secondary rejections on the 3,894 (per landing candidate, not per group): M8 landing pad vs opposite-net native supply 77,793 and vs
  opposite-net M8 grid stripe 56,537; M7 stem vs opposite-net native supply 6,273; 1 macro M4 pin.
  For the 4,908 near the clock legs, the M8 landing hit the clock leg 190,810 times (then opposite native 49,834 and opposite grid M8 33,927).
  No macro halo or other BLOCK owner shows up as a cause.

## 2. Structural fix in the planner (no blocker relaxed)
- `--m9-select cover`: picks the 3 x-nearest same-net M9 segments that COVER the landing y (this is the intent of the original code).
  On its own (off_c), this brings failures from 9,220 to 1.
- `--m8-landing first`: VIA78 goes straight onto the nearest same-net die M8 PG stripe covering x (M8 PG = horizontal 0.48-um stripes, 4.32-um pitch
  per net; this is real grid metal that the die plan already keeps off the clock legs). Search reach is `--m8-reach 8800` = next stripe. The M7 stem is the only new
  route; there is no M8 bridge and no VIA89. The M9 bridge is the fallback.
- All hard blockers are unchanged: clock-leg M8/M9 reservations, opposite-net metal, macro/cell OBS and pins, die edge. Plan runs (each about 7-13 min, 10 GB):

| run | ok groups | contacts | failed | landing | new M8 um2 | M7 band max / >0.6 |
|---|---|---|---|---|---|---|
| off (= variant A) | 35,970 | 60,453 | 9,220 | M9 bridge | - | 0.107 / 0 |
| fallback (M9 sel x) | 45,154 | 75,892 | 36 | 35,970 M9 + 9,184 M8 | - | 0.107 / 0 |
| first (M9 sel x, reach 4.4) | 45,154 | 75,892 | 36 | 45,129 M8 + 25 M9 | - | 0.107 / 0 |
| off_c (M9 cover) | 45,189 | 75,933 | 1 | M9 bridge | - | 0.107 / 0 |
| fallback_c | 45,190 | 75,934 | **0** | 45,189 M9 + 1 M8 | 12,549 | 0.107 / 0 |
| **first_c (ADOPTED)** | **45,190** | **75,934** | **0** | 45,168 M8 stripe + 22 M9 | **455** | 0.107 / 0 (15,293 gcells) |

- The 36 residuals of first/fallback are rails inside M8-stripe cut windows (for example x 1878-2584 at y 5318, and the PHY edge x~5940, y~26.1-26.5 mm). They close with the next stripe or the cover-select.
- **Why first_c is adopted:** it is the shortest access (rail -> M7 stem -> VIA78 on the grid). It puts 455 um2 of new M8 (inside stripes) against 12,549 um2 of M8 bridges for fallback_c, which leaves the
  leftover M8 to die signals (12.1c). The cost is more M7 (3,107 vs 471 um2), charged per band at max 0.107.
- Independent check `scripts/check_clockleg.py` (CHECKED): 90,424 M8 + 44 M9 access shapes against 7,977 M8 + 6,887 M9 clock-leg reservations
  give **0 within 40 nm**.

## 3. apply_access + render (CHECKED)
- `run_apply.sh plan_first_c` gives `access/access.odb`: IMPORTED_NO_SIGNOFF, 75,934 contacts, 45,190 groups, +936,492 rects, +312,164 vias,
  19,798 grid rects present, non-PG sha cce6226e... before == after. sha256 in receipts/odb_sha256.txt. DRC/IR NOT RUN.
- Renders, both viewed: review/access_v32_render.png and review/access_render.png (stock).
  - access_v32_render.png: all 9,220 formerly failed groups are now connected (9,206 via M8 stripe, 14 via M9 bridge).
  - In the zooms, each VIA78 sits on a same-net M8 stripe and clears the hatched clock legs; M7 stems pass under the legs on a different layer.
  - access_render.png (stock): dense islands with M7 stems.

## 4. Die GRT0 incl clock: LAUNCHED, not collected
- Command: ot-run --mem 256 --threads 16 --priority die --hosts intel1 -- run_grt.sh (grt_loaded.tcl unchanged from DIE-KV-31: 50 congestion iterations,
  signal M4-M7 / clock M8-M9). Unit **oth-ubuntu-3594166-1793299910** on intel1 (key-cardinal), docker dkv32-grt, started 2026-10-29 11:51:50 PDT.
- Collect from `grt/grt.log` (OT_DONE, overflow per iteration), `grt/congestion.rpt`, `grt/grt.odb`, `grt/route.guide`. The client log is intel2 ~/ot-logs/dkv32-grt.log.

## Not done / caveats
- sys_c VDDPHY M7->M8 macro contacts are still outside plan_access scope (pg_regions ot_pg_connect_pins). Same as DIE-KV-31.
- No IR, DRC, routed clock timing, sign-off or freeze claim. The M8-stripe landing puts std-cell current through the 0.48-um M8 stripes to M9 (IR not run; 12.4e: PG IR
  must close before signal GRT is final). 0 cycles added.
- The planner fix lives in a DIE-KV-32 copy of the Codex plan_access.py; the original is untouched. Upstreaming `--m9-select cover` is a shared-tool change and needs ROOT-MERGE.
