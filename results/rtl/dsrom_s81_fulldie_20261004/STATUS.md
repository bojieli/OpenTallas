# DeepSeek-V4.1 ROM S81 die physical: layer die (L20 scan) + 12-way head die (2026-10-04)

Tool `tools/dsrom_s81_fulldie.py` (`plan | real | grt | ir | irm | psmt | record`); records `floorplan.{json,def,svg}`
(layer die), `head_die/floorplan.*` (head die), `feasibility.json` (every OpenROAD case below; the case dirs are kept
on ot-epyc1tb:/srv/opentallas-scratch/claude/dsrom-s81-fulldie/cases).

## What was built
- 33,000 x 26,000 um die (858 mm2). The layer die has 2,417 pairs (1,898 q = REAL routed `ot_v41_rom_elem_q_qp_w10`
  abstract + 519 BF), 16,919 REAL cfg ROMs (`ot_rom_4096x72_m8`), and a 4,706-node ragged return tree. It also has 4
  REAL HBM3E PHYs, 8 REAL pdie SerDes/UCIe macros, 44 clock-region (option C) FIFO blocks, 24 hub FIFO slots and 216
  forwarded-link waypoints. Placed footprint is 428.2 mm2; 24,355 instances.
- The head die has 1,682 content pairs (embed, lm-head, norm and the 7.93 GB DSpark drafter, following the
  partition in b65276167). 211 of them are lm-head pairs carrying the NV5 batched draft head (`dsfd_nvx`). The die
  holds 17,216 instances on a 383.8 mm2 footprint, in the same outline.
- Floorplan changes, r2 -> r7. Each one was forced by a measured failure:
  - VCH widened from 302.4 to 604.8 um. The VM now sends a single x-root broadcast, and the return roots land in
    gather.
  - A 172.8 um routing gap separates each pair of stacked spine slabs.
  - Pin collisions in the generated abstracts were fixed: collective pll/link, bf nv/xbo and fifo r3/k3R.
    `check` now asserts that there are 0 pin clashes.
  - VM E-face service pins are split by direction: S-band services at 120/220 um, N-band services at h-220/h-120.
  - Cost: collective-to-link is now 52 stages at 430 um, up from 51.

## Results (mandatory items)
The legality, pin-access and GRT runs used the final r7 geometry. The IR cases ran on r5, which has the same instance
placement and power; r6 and r7 moved only VM pins.
| item | layer die | head die | verdict |
|---|---|---|---|
| macro legality (OpenROAD sweep) | 0 overlaps / 0 outside, 24,355 | 0 / 0, 17,216 | PASS |
| on-track assert (all signal pins) | 5,686,228 pins, 0 off-track | 5,202,840, 0 | PASS |
| pin access (DRT) | only `xs_q1[151]` of the REAL q abstract | same | FAIL, element abstract |
| GRT k16, 5 iterations, overflow | 3 (M6/M7/M9 1 each) | 2 (M5/M9) | iterate |
| GRT k16, 50 iterations, overflow | **0** | **0** | PASS |
| max use/cap per 4x4 GCell window, M2-M9 (baseline-subtracted), i50 | 1.00, 0 windows > 1 | 1.00, 0 > 1 | PASS |
| PSM IR, rail-to-rail interior, field window (peak in-phase 2.04 W/mm2) | 28.88 mV | 28.95 mV | PASS (35) |
| PSM IR, field_bf / field_nv (hottest frame) | 29.74 mV | 29.34 mV | PASS |
| PSM IR, spine / band_s | 32.19 / 28.56 mV | - | PASS |

The PG coverage the IR results need, and that the GRT ran with, is M8/M9 per net: field 0.128, hub 0.044, svc 0.1639.
The bumps are 45 um, every one a power bump (VDD/VSS pitch 63.6 um), at 0.7 V.

GRT history: r2 overflow 468, r3 309 (at i50 it rose to 576), r4 14, r5 12, r7 3. A probe at heavier PG coverage
(field 0.32 / hub 0.128) gave i5 overflow 524. The 0.128 point holds IR and routing together.

## Method notes
- **IR sign-off is case c.** Case c splits the instance power into 20 um load cells on the M8/M9 grid, then PSM runs
  on the window, using the interior that sits one bump pitch in from the window edge.
  - The window-edge worst values (VSS up to 38.5 mV) come from the window cut, which leaves no bumps beyond the edge.
    They are not die values.
  - The real-abstract case (`irm`: q / cfg / generated M7 PG pins, pdngen, PSM) proves the PDN connects end to end.
    pdngen passes, PSM-0040 reports every shape connected, and each q gets 1,824 V7 vias. Its worst-drop numbers are a
    PSM artefact: PSM concentrates a macro instance's current on a few nodes.
  - The control experiment (`psmt`) shows this. The same 1 W/mm2 on the same grid gives 54.8 mV as one 1 mm2 macro and
    2.39 mV as 2,116 cells.
  - In irm, large slabs show it most strongly: 169 mV at the spine HC slab. On the q element it reads 62.15 mV at 0.128
    and 37.6 mV at 0.25.
- Placement uses snap-only placement (`fplace`) followed by one sweep-line overlap check. It takes 6 s, against more
  than 1.5 h for O(n^2) `ot_mts::place`.
- The IR power comes from `scan_die_power()` at the local peak in-phase densities. The head-die IR window uses its own
  instances, including nvx. The `scan_die_power` block in `head_die/floorplan.json` is the layer die's.

## Open item (owner: q element abstract, S82/W4 `routed_q`)
The pin `xs_q1[151]` (M5, 264.384-264.408 x 126.816-126.9) has no die-level access point. Three things in the
abstract block it:
- an M5 OBS stub [264.432, 126.864, 265.512, 126.899], 0.024 um from the pin;
- M6 OBS [262.693-265.475, ..126.88] over the pin;
- M4 OBS under the pin.

All other 733 q pins, every cfg pin, every PHY/link pin and every generated pin are accessible. The fix is a q
abstract regenerated with that pin's access kept clear, or the pin moved one track, at element level. The die
floorplan does not change. Every OpenROAD result is from a measured run. No part of the die-level route itself is
modelled.
