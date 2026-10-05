# Handoff to Codex: HBM accelerator die, route iterations of the fixed r8 floorplan

Owner until now: Claude:hbm-die-floorplan. The floorplan is fixed at **r8**: `tools/hbm_accel_die_fp.py` `build()` defaults. Do not move blocks. If a route iteration needs a floorplan change, hand it back.

## What is fixed

- The die outline, every block rectangle and orientation, the channel grid, the forwarded-link stations and the die-level nets.
- These are recorded in `floorplan.{json,def,svg}` and `domains.sdc`.
- The PG plan: per-net M8/M9 coverage of 0.0878 over the field, hub and spine, 0.1639 over the stream service, and bumps on the die-anchored 63.64 um VDD/VSS lattice (`floorplan.json` `pdn`).

## The loop to run

Every case runs on ot-epyc2 under `/srv/opentallas-scratch/claude/hbm-die-floorplan/` through `admit.sh`, with sources in `src/` and the source commit recorded in `src/SOURCE_COMMIT`.

1. **Replace placeholders with real abstracts as their elements close.** In `masters()`, swap the generated master for the real LEF, the way the PHY, SerDes and UCIe are already handled (`real_ports()`, `REAL`). Order of arrival:
   - The SM element `hfd_sm`. Its source is the `ot_hbm_accel_sm_v` sm_r2 route (Popper). Keep the 2202.768 x 2072.79 um frame and the context pin regions. If the hardened abstract differs, re-run `plan` and `check` before anything else.
   - The SU halves, the attention tile, the index quarter, the TU endpoint and the stream service, each as it is hardened.
   - The abstract height must satisfy H = 0.024 mod 0.048 for the MX-placed N-side instances (`tools/check_macro_track_alignment.py`).
2. **Re-run the physical cases after each swap.** `grt_all.sh <round>` runs legality, track assert, pin access and GRT at k16 for 5 and 50 iterations. `ir_all.sh <round>` runs PSM IR on all 88 windows.
3. **Record and re-price.** Run the following, then commit the records:
   - `python3 tools/hbm_accel_die_fp.py record --work cases/<round> --out ...`
   - `python3 tools/hbm_accel_die_fp.py price --work cases/<round>/b_k16_i50`
4. **Pass criteria.** Each item is checked as below. A failed round is recorded and never overwritten.

   | Item | Pass criterion |
   |---|---|
   | Legality | 0 overlaps and 0 outside |
   | Track assert | 0 pins off track |
   | Pin access | macroNoAp = 0 |
   | GRT at 50 iterations | overflow 0 |
   | IR, every window | interior rail to rail <= 35 mV |

## Not in this loop

These items still belong to their element owners, not to the die loop:

- SM element route closure.
- SU m6a5 lane closure.
- Attention tile, index path, TU endpoint and cmdproc hardening and their SS/FF sign-off.
- The expert-workgroup steering RTL.
- Detailed routing and STA of the die-level trunks. The stage counts are bounds from routed length at the 430.56 um closing pitch, not STA.

## Starting point (r8, 2026-10-05)

| Item | r8 result |
|---|---|
| Legality | 369 instances, 0 overlaps, 0 outside |
| Track assert | 0 of 1,208,318 pins off track |
| Pin access | macroNoAp = 0 |
| IR | 25.41 mV worst over all 85 load windows |
| GRT k16, 5 iterations | overflow 218 |
| GRT k16, 50 iterations | overflow **128** (M7 37, M9 91); 0 4 x 4 windows above 1.0 |

**First targets.**

1. Bring the 50-iteration GRT overflow to 0.
2. Pull the routed stage bound toward its Manhattan floor. The DS AR cost is +102.4 us at the bound against +30.6 us at the floor (`wire_stages.json` `bases`).
3. Start with the hub nets whose 50-iteration bundles detour, each against its 4-stage Manhattan:

   | Net | Bound (stages) | Median (stages) |
   |---|---:|---:|
   | NE SU quarter <-> endpoint (`hb_su_NE_coll`, `hb_coll_su_NE`) | 53 | 24-38 |
   | SE SU quarter <-> endpoint (`hb_su_SE_coll`, `hb_coll_su_SE`) | 28-31 | 13-20 |

   Also take the worst x-trunk bundle (`xbcast_sm28`): 135 stages at the bound, 81 at the median.

**Levers inside the fixed floorplan:**

- forwarded stations on the long hub nets (today they are direct nets);
- layer assignment of the 2,048 / 2,063-bit trunks to M8/M9;
- per-region PG adjustment (coverage stays at or above the IR-passing 0.0878 / 0.1639).

Remote scripts: `grt_all.sh`, `ir_all.sh` and `stop_round.sh` in `/srv/opentallas-scratch/claude/hbm-die-floorplan/` (ot-epyc2; agidock also has the sources). The status of the remote area is in `STATUS.md` there.
