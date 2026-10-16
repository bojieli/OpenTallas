# core4_sfu2_su2825 v2: measured SFU core and centre HC engine

Status: **UNADOPTED GEOMETRY PROPOSAL.** The active contract
`results/arch/hier_contract_1015/hbm_v15.json` is unchanged; the H-DIE lead adopts after review.

**The audit passes, but the die cuts fail.** With the measured v16 HC_ENG link widths, 376 cut lines are over 0.60. The
HC engine's x_wave transport is not routable as specified; see the HC engine section.

## What was measured

- Die: 790.1 mm², 32,990 × 23,949.682 µm, fits the reticle; 657.82 mm² placed. Quarter RF/reducer core at the inner
  band end; middle SFU group at group 2.
- SM slot: 7,200 × 1,800 µm, from the measured rp4b frame of 7,188.48 × 1,765.44 µm
  (`../xc_rp4b_frame_1016`).
- SU slice: 1,797.12 × 2,825.28 µm. This is H-SU's heavy-slice packing (main d6d9a0ce2,
  `results/arch/hbm_su_f2_static_1014/su_band_v6_0600`). The band is 3,045.28 µm.
- Quarter qcore: 330.48 µm square. Tall VM hub: 480 µm.
- **SFU grant (H-SU, main c63aacafe, `results/arch/hbm_su_f2_static_1014/sfucore_sizing_0600`).** The measured
  ot_hgi_sfu_scheduled_engine needs 1.825 mm² (1.683 mm² hard plus std cells at 60 %). That does not fit the old
  763.56 × 1,936.44 slot plus the 524.88-µm store. The new grant per quadrant:
  - `sfucore_<q>`: 763.56 × 3,001.91, the full band height.
  - `sfus_<q>`: 1,020 × 1,412 in the side-upper bay, y offset 1,611.68.
  - Both come from compact_plan ca0a2d04c; the plan defaults reproduce v1 exactly.
- **HC engine (H-NETLIST main 406a2d5f9, `results/arch/hbm_die_v16`).** `hc_eng` is ot_hbm_hc_eng_static at about
  9.5 mm². Its home is 3,050 × 3,114.754 µm at (14970, 10171.176), in the centre-column void between the S and N IDX
  scorer stacks.
  - Two 100-µm relay rows (the RF cross corridors) stay free: one against idx_s1, one against idx_s3.
  - The IDX glue row (idx_q, idx_sel, idx_link) moves above the engine. hb_ckgen follows idx_link.
  - The programme collars `hc_eng_tgt` and `hc_tbl_tgt` (ot_static_program_target, TARGET 164/165) close the glue row
    on the east at (17933.6, 13305.93/13392.33). Their 86.4 × 64.8 outline is a candidate; synthesis is pending. Each
    collar is 0 relay stages from the engine's N face.
  - The HC_ENG links carry the v16 widths: 8,244 b in per quadrant (x_wave 8,192, word/valid 11, gathered_mix 41) and
    772 b back.

## Cuts and stages (`eval.json`, lane slack 1200)

| Variant | Worst V/H cut | Lines over 0.60 | Weighted stages | HC_ENG stages |
|---|---|---|---|---|
| v1 home (NE channel, 1 mm²), 512-b estimate | 0.493 / 0.574 | 0 | 8.778 | 43.0 |
| centre home, 512-b estimate | 0.493 / 0.595 | 0 | 8.773 | 37.5 |
| v1 home (NE channel), v16 widths | 0.992 / 1.330 | 430 | 11.793 | 43.67 |
| **this plan: centre home, v16 widths** | **0.874 / 0.929** | **376** | **11.337** | 39.0 |
| centre, x_wave over 2 beats (what-if) | 0.586 / 0.664 | 4 | 10.124 | 38.5 |
| centre, x_wave over 4 beats (what-if) | 0.493 / 0.664 | 4 | 9.502 | 38.5 |

The other rows are in `ablation_hc/*/eval.json`, with the same command and the flags shown. The beat what-ifs are
**unadopted RTL changes**: x_wave is consumed once every 4 edges, so a fixed 2- or 4-beat serial transfer keeps the
static schedule but needs H-NETLIST RTL. The 0.664 that remains is the existing band window at y5200,
x13100–14100.

## HC engine home (`hc_eng_home.json`)

The four clients `hc_<q>0` sit at the die's W and E edges (x 100 and x 32,390). Any home between them has the same
summed Manhattan distance, so the centre minimises the worst link. All eight links are balanced:

| Link | Routed µm | Relay stages (500 µm) |
|---|---:|---:|
| hc_SW0 → hc_eng, 8,244 b | 18,655 | 37 |
| hc_SE0 → hc_eng, 8,244 b | 18,655 | 37 |
| hc_NW0 → hc_eng, 8,244 b | 19,237 | 38 |
| hc_NE0 → hc_eng, 8,244 b | 19,237 | 38 |
| hc_eng → hc_SW0/SE0, 772 b | 18,875 | 37 |
| hc_eng → hc_NW0/NE0, 772 b | 19,017 | 38 |

The v1 NE-channel home gave 28–56 stages, worst 56.

**Engine-face cut:** the W and E faces each carry 2 × (8,244 + 772) = 18,032 b over 3,114.75 µm, utilisation
**0.412**, which passes. The centre region itself is not the problem.

**Client side fails.** The band barrier cut (`sfu_barrier_cuts_hc.json` and `sfu_barrier_cuts_roof_hc.json`, with
`--graph-cls HC_ENG`) runs through `su_<q>1`. hc_<q>0's 9,016 b cross it on top of the 2,676 SFU/SU bits, 11,692 b in
all:

- hard frames only: 3.198;
- with the conditional SM-roof borrowing: 1.329.

Even with a 4-beat x_wave, the 2,872 HC bits give 5,548 b, which is 1.517 hard-frame and 0.631 with the roof. That
still fails 0.60.

The structural options are owner/HC-owner decisions:

- move the quadrant HC client (`ot_hbm_hc_q_static`) to the band's inner end, next to the hub;
- serialise x_wave and give it a dedicated channel;
- or distribute the engine.

## SFU barrier (unchanged by the taller SFU core)

The cut through `su_<q>1` is 0.732 with hard frames only (`sfu_barrier_cuts.json`): 2,676 b over a 260-µm channel, where
0.60 needs 317.16 µm. With conditional SM-roof borrowing it is 0.304 (`sfu_barrier_cuts_roof.json`, 625.76 µm). This
is conditional: parent OBS/PG and the clocks of the roof area are unqualified.

## Grants proposal (`grants_proposal.json`)

The audit passes: 0 slots outside the die, 0 overlaps, 0 points in hard blocks. All 576 RF footprints are audited as
rectangles. `tools/hbm_die_v15/rehome_v6.py` has these rules:

- **5.** A plan-block slot without exact pins takes the plan outline. This covers hc_eng (now cell
  ot_hbm_hc_eng_static, 3,050 × 3,114.754) and sfucore_<q> (763.56 × 3,001.91). New FACES_ONLY slots are added for
  `sfus_<q>` (H-SU store partition of the SFU engine, cell pending) and the collars `hc_eng_tgt` / `hc_tbl_tgt`.
- **6.** host_N stays exactly on the N 20-µm edge. The move is dy −0.024 µm, which repairs a v5 rounding overhang.
- **7.** Each calendar_<q> sits against its hub's band-side face across 21.6 µm, so the 187-b hub link has 0 stages.
  Orients are SW R0, SE MY, NW MX, NE R180. The moves from the translated (overlapping) homes are SW 1,125, SE 1,165,
  NW 1,982 and NE 2,369 µm. The cfg and status faces go to host_cp and vm_status4, 6–21 mm away for any home.
- **8.** RF relay homes are the allocated standard-48 footprints. The tools are `rf_centre_routes.py` and
  `rf_centre_allocate.py`; the cross corridors now follow the centre-column blocks.
  - All 16 routes are obstacle-clear. The geometric minimum is 32 stages; the production 36 are kept.
  - 576 / 576 footprints placed, 0 failures, maximum hop 427 µm.

## Images (personally inspected)

- `layout/die_floorplan.png`: the whole die, with plan blocks, non-plan slots and RF footprints.
- `layout_centre/die_floorplan.png`: the hc_eng void with its relay rows, glue, collars and calendars.
- `layout_sw_band/die_floorplan.png`: the SW band with the taller sfucore, the sfus bay and hc_SW0 at the W edge.
- `sfu_barrier_cuts_roof_hc.png`: the barrier cut.

No block sits on a block and no home is on a block. hc_eng now fills the centre void instead of the NE channel. The
images also show the open issue: hc_<q>0 sits at the far die edge, so x_wave must cross all four SU slices of its band.

## Reproduce

```sh
P=results/arch/hbm_die_v15/core4_sfu2_su2825
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3045.28 --su-w 1797.12 --su-h 2825.28 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --sfucore-h 3001.91 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1611.68 --hc-eng-mm2 9.5 --hc-links-v16 --out $P
python3 tools/hbm_die_v15/v6_eval.py $P --slack 1200
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --out $P/sfu_barrier_cuts.json
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --borrow-roof --out $P/sfu_barrier_cuts_roof.json
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --graph-cls HC_ENG --out $P/sfu_barrier_cuts_hc.json
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --borrow-roof --graph-cls HC_ENG --out $P/sfu_barrier_cuts_roof_hc.json
python3 tools/hbm_die_v15/rf_centre_routes.py $P && python3 tools/hbm_die_v15/rf_centre_allocate.py $P
python3 tools/hbm_die_v15/rehome_v6.py --plan $P --out $P/grants_proposal.json
python3 tools/hbm_die_v15/hc_eng_home_1016.py $P --ablation centre_v16=$P nechannel_512b=$P/ablation_hc/nechannel_512b ...
python3 tools/die_layout_render.py --hbm $P --grants $P/grants_proposal.json --out $P/layout   # + --window for the zooms
```

v5 is unaffected (`rehome_compact.py`). Without the new flags, compact_plan and rf_centre_routes reproduce v1 and
core4_sfu2 exactly; the core4_sfu2 RF corridors were checked unchanged.

## Open

- **The x_wave transport into the HC engine fails the band cut**; see the HC engine section. This needs an owner/HC
  decision before the HC home can qualify.
- Programme 476-macro candidate homes and their clocks.
- SKV/collective source homes and roots.
- R23 station reset glue: 11,040 flops in all, unqualified.
- sucx/cij faces. The cij, sfus and collar slots are FACES_ONLY.
- Exact qcore RF per-bit pins.
- Calendar hub-face pin windows.
- The collar outline needs synthesis.
- The sfus cell name and partition, from H-SU.
- Every native view, TT/FF/DRC0 and die GRT/STA.
