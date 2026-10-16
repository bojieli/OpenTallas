# core4_sfu2_su2825: measured-fit v15 plan and grants proposal

Status: **UNADOPTED GEOMETRY PROPOSAL.** The active contract
`results/arch/hier_contract_1015/hbm_v15.json` is unchanged; the H-DIE lead adopts after review.

## What was measured

- Die: 790.1 mm², 32,990 × 23,949.682 µm, fits the reticle. Quarter RF/reducer core sits at the inner band end; the
  middle SFU core/store sits at group 2.
- SM slot: 7,200 × 1,800 µm, from the measured rp4b frame of 7,188.48 × 1,765.44 µm
  (`../xc_rp4b_frame_1016`).
- SU slice: 1,797.12 × 2,825.28 µm. This is H-SU's measured heavy-slice packing (main d6d9a0ce2,
  `results/arch/hbm_su_f2_static_1014/su_band_v6_0600`). The band is 3,045.28 µm.
- Quarter qcore: 330.48 µm square. Tall VM hub: 480 µm.

## Cuts and stages

From `eval.json`, lane slack 1200:

- Worst cut: V 0.493 and H 0.574. No line and no window is over 0.60.
- Bandwidth-weighted stages: 8.778.

From `sfu_barrier_cuts*.json`:

- The SFU barrier cut through the second SU slice is 0.732 when the hard frames obstruct the route plane. That fails the
  0.60 limit: 2,676 bits cross a 260 µm channel, and 0.60 needs 317.16 µm.
- With conditional SM-roof borrowing (+365.76 µm, giving a 625.76 µm channel) the cut is 0.304. This is conditional:
  parent OBS/PG and the clocks of that roof area are not yet qualified.

## Grants proposal (`grants_proposal.json`)

The audit passes: 0 slots outside the die, 0 overlaps, 0 points in hard blocks. The 576 RF footprints are audited as
rectangles against every die-level footprint and against each other.

The v5→v6 translation alone failed on this plan for three reasons. host_N sat 0.024 µm outside the die. The tall hub
covered hc_eng and the four calendars. Twelve RF homes fell inside hard blocks. The new rules are in
`tools/hbm_die_v15/rehome_v6.py`, rules 5 to 8:

| Slot | Old (translated) | New home | Change |
|---|---|---|---|
| host_N | top 0.024 µm past the 20 µm edge (inherited v5 rounding) | N shoreline exact, (16961.264, 22277.258) MX, 21.6 µm east of ep_N1 | dy −0.024 µm; host_cp link unchanged |
| hc_eng | 560 × 1,785.7 outline at the plan origin (overlapped vmh_NE) | plan outline 410 × 2,439.0 at (18040, 16232.3) in the NE channel | centre moves 401.7 µm; the summed 4 × 512-bit HC_ENG link Manhattan is unchanged at 87,389 µm (SW/SE +251/+401, NW/NE −402/−252) |
| calendar_SW | inside vmh_SW | (13798.08, 6205.6) R0, against the hub W face | centre moves 1,125 µm; hub gap 21.6 µm |
| calendar_SE | inside vmh_SE | (18971.6, 6205.6) MY, against the hub E face | 1,165 µm; gap 21.6 µm |
| calendar_NW | inside vmh_NW | (13798.08, 17409.282) MX | 1,982 µm; gap 21.6 µm |
| calendar_NE | inside vmh_NE | (18971.6, 17627.442) R180 | 2,369 µm; gap 21.6 µm |

How the calendar homes were chosen:

- Each calendar's 187-bit hub-schedule face (E) faces its hub across one 21.6 µm channel, on the band side of the hub.
- The home is clear of every plan block, the hub-face pin windows and the RF footprints.
- This puts the hub link at 0 relay stages. Homes in the centre column would cost about 2.3 mm (about 4 stages).
- The cfg face (W) goes to host_cp and the status face (S) goes to vm_status4. Both are far for any home, at 6.2 to
  21 mm; these are static config/status paths.

RF relays come from `rf_centre_routes.json` and `rf_centre_allocation.json`. The tools are `rf_centre_routes.py` and
`rf_centre_allocate.py`.

- All 16 routes are obstacle-clear. The geometric minimum is 32 stages; the production 36 stages are kept.
- 576 standard-48 footprints (`hbfd_rly_48_*`, af261fbcb) are placed, with 0 failures and a maximum hop of 427 µm.
- The contract `su_rf_relays_v7` homes are now these footprint centres, with the footprints, the path and the hops.

## Images (personally inspected)

- `layout/die_floorplan.png`: the whole die, with plan blocks, non-plan die slots and RF footprints.
- `layout_centre/die_floorplan.png`: the centre window, 12200,4800 to 19800,19200.

No home sits on a block. The calendars sit beside the hubs, and the RF footprints sit in the centre-column channels and
the 40 µm band/SM gaps.

Pre-existing items that are visible but not changed here:

- hc_eng occupies the NE centre channel, by the plan's design.
- The RF relays sit in routing channels (relay rows).

Reproduce:

```sh
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3045.28 --su-w 1797.12 --su-h 2825.28 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --out results/arch/hbm_die_v15/core4_sfu2_su2825
python3 tools/hbm_die_v15/rf_centre_routes.py results/arch/hbm_die_v15/core4_sfu2_su2825
python3 tools/hbm_die_v15/rf_centre_allocate.py results/arch/hbm_die_v15/core4_sfu2_su2825
python3 tools/hbm_die_v15/rehome_v6.py --plan results/arch/hbm_die_v15/core4_sfu2_su2825 --out results/arch/hbm_die_v15/core4_sfu2_su2825/grants_proposal.json
python3 tools/die_layout_render.py --hbm results/arch/hbm_die_v15/core4_sfu2_su2825 --grants results/arch/hbm_die_v15/core4_sfu2_su2825/grants_proposal.json --out results/arch/hbm_die_v15/core4_sfu2_su2825/layout
```

v5 is unaffected: it uses `rehome_compact.py`. compact_v6b has no RF allocation, so it keeps the translated RF homes
(its 12 RF points remain flagged).

## Open

- Programme 476-macro candidate homes and their local clocks.
- SKV/collective source homes and roots.
- R23 station reset glue: 13 reset flops plus 2 synchronizers per 13 × 48 station, 11,040 flops in all. Their footprint,
  placement and release timing are unqualified.
- sucx/cij faces and their exact pins. The cij slots are FACES_ONLY.
- Exact qcore RF per-bit pin grants. The centre-route pins differ from the v5 `su_rf_route_pins` geometry used by
  `grant_core`.
- Calendar hub-face pin windows in the plan pin file. The calendar links are not in `compact.graph.json`.
- The SFU barrier cut fails at 0.732 without the roof. It needs the qualified roof (OBS/PG/clocks) or a structural
  channel / distributed-SFU successor.
- Every native view, TT/FF/DRC0 and die GRT/STA.
