# core4_sfu2_su2825 v4: band 3153.28, hub pins spread, lane legs charged

Status: **UNADOPTED GEOMETRY PROPOSAL.** The active contract
`results/arch/hier_contract_1015/hbm_v15.json` is unchanged; the H-DIE lead adopts after review.

**Results:**
- Grants audit: PASS (0 outside / 0 overlaps / 0 points in hard blocks).
- Die cut: PASS, 0 lines over 0.60.
- HC-inclusive band barrier: PASS only with the conditional rp4c roof.

## v4 (H-DIE decisions 10-16)

### What changed
1. **Band grows by 108 µm**, from 3,045.28 to 3,153.28. The SU slot is unchanged at 1,797.12 × 2,825.28.
   - Die: 32,990 × 24,164.898 µm = **797.2 mm²**, up 7.1 mm². The width is unchanged against the 33,000 reticle.
   - The tall hub grows with the band to 480 × 3,113.28.
2. **Hub-corner window fixed at the hub face and in the lanes**, picked by measured cut. Neither change widens the die.
   - `v6_eval.py --spread vmh_SW:W:159.84 vmh_NW:W:159.84 vmh_SE:W vmh_NE:W` spreads the hub W-face pin windows over
     the full 3,113-µm face instead of packing them at the corner nearest their peers.
   - On SW/NW the spread keeps a 159.84-µm pin-free window at the centre of the band-side face for the calendar
     (116.64 + 2 × 21.6).
   - `--lanes-mode legs` makes `band_lanes.py` charge each lane's two pin-to-lane legs against the 1-mm windows they
     cross. Without it, the router can pick a lane whose vertical legs overload a hub corner.
   - Both options default to off, so v5, v6 and earlier plans reproduce.
3. **SUCX** stays at the plan's 216 × 194.4 µm. **PENDING:** the barrier tool models the source-compact 720 × 720 SUCX
   (COLL top + 742), which overlaps hc_<q> by 54 µm in x. If H-NETLIST/H-SU adopt that size, the pocket west of the
   calendar is only 358 µm wide, so hc_<q> must reshape (358 wide) or move above the SUCX.

### Hub-corner options, measured on the v4 geometry

| Option | Worst V/H cut | Lines over 0.60 | Weighted stages |
|---|---|---|---|
| none (v3 method) | 0.530 / 0.648 | 5 | 9.205 |
| lane legs only | 0.592 / 0.614 | 1 | 9.024 |
| spread band-side face only (SW/NW W, SE/NE E) | 0.521 / 0.614 | 1 | 9.344 |
| spread band-side face + legs | 0.585 / 0.557 | 0 | 9.202 |
| **spread hub W faces + legs, calendar window (adopted)** | **0.554 / 0.560** | **0** | **9.100** |

### Final v4 numbers (`eval.json`, slack 1200)
- **Cut:** V 0.554 at x 20,400, y 17,500–18,500; H 0.560 at y 6,300, x 13,100–14,100. 0 lines and 0 windows over
  0.60. Weighted stages 9.100.
- **Worst H window** (`cut_worst_window.json`, 0.560):

| Class | Bits |
|---|---:|
| VM_HUB | 2,152 |
| HC_CORE | 1,628 |
| VM_HBM | 1,536 |
| IDX_VM | 1,096 |
| COLL_RING | 826 |
| HBM_VM | 512 |
| KV_DESC | 128 |

- **Old corners:** the v3 corner window (y 5,300) is now 0.388. The NW mirror corner is no longer over 0.60.
- **HC_ENG** (`hc_eng_home.json`, 4-beat x_wave), in / back / round trip in stages:

| Quadrant | In | Back | Round trip |
|---|---:|---:|---:|
| SW | 12 | 8 | 20 |
| SE | 13 | 8 | 21 |
| NW | 15 | 11 | 26 |
| NE | 12 | 10 | 22 |

  Add 3 cycles for the serialisation. The engine-face cut is 0.134.

### Band barrier through su_<q>1 at band 3153.28 (368 µm free over and under the slices)

| Traffic | No roof (record) | With rp4c roof (270.72 µm, 638.72 µm total) |
|---|---|---|
| SFU/SU only, 2,676 b | 0.517 | 0.298 |
| Plus HC, 4,900 b | **0.947 (fails)** | **0.546 (passes)** |

The HC-inclusive pass depends on qualifying the roof: parent OBS/PG and the clocks of the roof area. Without the roof,
HC needs 580.7 µm of channel against 368 µm.

### Grants and visual check
- Calendars: SW (13798.08, 6672.16) and NW (13798.08, 17417.14) sit in the reserved hub-face windows; SE and NE are
  against the E face.
- hc_<q>: SW (13342.32, 6762.88), mirrored.
- RF: 576/576 footprints at 36 stages (33 required), max hop 452 µm.
- XC witness at rp4c regenerated for the v4 SM positions.
- Personally inspected: `layout/`, `layout_centre/`, `layout_sw_band/die_floorplan.png` and
  `sfu_barrier_cuts_roof_hc.png`. No overlaps and no homes on blocks; the only conflict is the 720-SUCX model above.

### Reproduce

```sh
P=results/arch/hbm_die_v15/core4_sfu2_su2825
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3153.28 --su-w 1797.12 --su-h 2825.28 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --sfucore-h 3001.91 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1611.68 --hc-eng-mm2 9.5 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --out $P
python3 tools/hbm_die_v15/v6_eval.py $P --slack 1200 --spread vmh_SW:W:159.84 vmh_NW:W:159.84 vmh_SE:W vmh_NE:W --lanes-mode legs
python3 tools/hbm_die_v15/xc_rp4b_frame_witness_1016.py --tile rp4c --ref e15f1ee76 --candidates core4_sfu2_su2825 --out results/arch/hbm_die_v15/xc_rp4c_frame_1016
# then the barrier cuts, rf_centre_routes/allocate, rehome_v6 --out, hc_eng_home_1016, cut_window_who (h 6300 13100) and the renders, as in the v3 block below
```

## v3 history (H-DIE decision 10-16; numbers are v3's, band 3045.28): HC client at the band's inner end, x_wave over 4 beats

### What changed
- **HC client.** `hc_<q>` (ot_hbm_hc_q_static, the x_wave source) is a new plan block with slot.
  - Candidate outline 432 × 432, pin-limited: about 7.6 kb of pins including the 4-beat x_wave. Synthesis is pending.
  - Home: the inner-end pocket, SW frame (13342.32, 6762.88), mirrored per quadrant. That is west of the calendar
    column (2 × 21.6 + 2.16 µm clear of it) and above the COLL / DMA back / IDX operand stack.
- **Group leaves stay put.** The 16 leaves `hc_<q><k>` (ot_hgi_sfu_lg_pair_leaf) stay at their bank pairs, so LG_HC is
  still 0-stage.
- **v16 group links.** Per leaf: 596 b from the client (lg_rq 34 + lg_wq 562) and 516 b back (c_rr 514 + c_w_done 2),
  class HC_CORE. These replace the 256-b estimates into hc_<q>0.
- **4-beat x_wave** (`--hc-x-beats 4`): 2,048 + 52 = 2,100 b per quadrant to hc_eng, 772 b back.
- **Roof at rp4c height.** H-SM rp4c (e15f1ee76, `smh_tile_rp4c/floorplan.json`) makes the SM tile body 1,529.28 µm
  tall.
  - The roof strip is now 270.72 µm, not 365.76.
  - The XC home moves to y 1,550.88; only 33.12 µm remains above it.
  - Witness: `../xc_rp4c_frame_1016/witness.json`, built with `xc_rp4b_frame_witness_1016.py --tile rp4c --ref
    e15f1ee76`. The rp4b witness reproduces byte-identically.

### Die cuts (`eval.json`, lane slack 1200)

| Variant | Worst V/H cut | Lines over 0.60 | Weighted stages | HC_ENG stages |
|---|---|---|---|---|
| **v3: inner client, 4-beat** | **0.530 / 0.623** | **5** (23 windows) | **9.161** | 10.9 (bit-weighted) |
| v2: hc_<q>0 client, 1 beat | 0.874 / 0.929 | 376 | 11.337 | 39.0 |
| v2 client, 4-beat | 0.493 / 0.664 | 4 | 9.502 | 38.5 |
| baseline, 512-b estimates | 0.493 / 0.574 | 0 | 8.778 | 43.0 |

### HC_ENG round trip (`hc_eng_home.json`, routed, 500 µm per stage)

| Quadrant | In / back stages | Round trip | Plus 4-beat serialisation |
|---|---|---:|---:|
| SW | 11 / 13 | 24 | +3 cycles |
| SE | 8 / 11 | 19 | +3 |
| NW | 13 / 14 | 27 | +3 |
| NE | 9 / 11 | 20 | +3 |

v2 was 74–76 per round trip. Engine-face cut: 0.134.

### Worst window (`cut_worst_window.json`, `tools/hbm_die_v15/cut_window_who.py`)

- Horizontal lines y 5,000–5,300, window x 13,100–14,100: 8,764 b, 0.623. The NW mirror at y 18,700 is 0.608.
- These lines lie in the strip between the SM row and the band, under the SW corner of the hub's W face.
- What crosses it:

| Class | Bits |
|---|---:|
| VM_HUB | 2,690 |
| HBM_VM + VM_HBM | 4,096 |
| COLL_RING | 826 |
| IDX_VM | 548 |
| SM_OUT | 540 |
| KV_DESC | 64 |

- **No HC bits cross it.** The same window is 0.567 in the baseline. The HC links move band_lanes' lane choices, which
  pushes two more vmh→vmb links and the vmb→idx_op links through the window. The excess is 327 b (limit 8,437.5).
- The y 18,700 window does carry HC_CORE 516 b.
- This is a lane-assignment / hub-corner problem, not an HC capacity problem. The fix is a hub-face or lane change,
  not further HC rework.

### Band barrier through su_<q>1 (necessary cut, hard frames; roof at rp4c 270.72 µm)

| Traffic | Hard frames only | With rp4c roof (530.72 µm) |
|---|---|---|
| SFU/SU only, 2,676 b | 0.732 | 0.359 |
| Plus HC: 4,900 b (groups 0/1 ↔ client 2 × 1,112 b) | 1.340 | **0.657, fails** |

- With HC the barrier needs a 580.7 µm channel: 50 µm more than the rp4c roof gives.
- The client cannot sit anywhere better. West of the cut, groups 2/3 and the x_wave/result (2,872 b) would cross
  instead. Leaf traffic plus SFU traffic at this cut is the floor.
- Options:
  - narrow the HC leaf ↔ client links (e.g. time-multiplex lg_wq);
  - roof qualification plus 50 µm more of channel;
  - SFU-side relief.

### Visual check

- `layout_sw_band`, `layout_centre`, `layout` and `sfu_barrier_cuts_roof_hc.png` were personally inspected; no
  overlaps.
- **Conflict found in the barrier plot.** sfu_barrier_cut_1016.py models the source-compact SUCX as 720 × 720 at the
  COLL top + 742. That box overlaps hc_<q> by 54 µm in x.
- If that SUCX size is adopted, the pocket between SUCX and the calendar column is only 358 µm wide. hc_<q> then needs
  a 358-wide reshape or a move above the SUCX. Today's plan SUCX is 216 × 194.4, so the audit passes.

## Grant history (v2, kept below)

The numbers below are v2's, with the rp4b roof; the v2 plan files are at commit 6731a60ce. The files in this directory
now hold v3. The SFU and HC homes, the rules and the audit method are unchanged.

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
python3 tools/hbm_die_v15/compact_plan.py --layout col --core-at 4 --sfu-at-group 2 --core-w 330.48 --core-h 330.48 --core-column-w 276.48 --band 3045.28 --su-w 1797.12 --su-h 2825.28 --smw 7200 --smh 1800 --edge 100 --column 3050 --channel 450 --hub-w 480 --fit --carry --sfucore-h 3001.91 --sfu-store-side --sfus-wh 1020 1412 --sfus-yoff 1611.68 --hc-eng-mm2 9.5 --hc-links-v16 --hc-x-beats 4 --hc-client-inner --out $P
python3 tools/hbm_die_v15/xc_rp4b_frame_witness_1016.py --tile rp4c --ref e15f1ee76 --candidates core4_sfu2_su2825 --out results/arch/hbm_die_v15/xc_rp4c_frame_1016
python3 tools/hbm_die_v15/v6_eval.py $P --slack 1200
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --out $P/sfu_barrier_cuts.json
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --borrow-roof --roof-witness results/arch/hbm_die_v15/xc_rp4c_frame_1016/witness.json --out $P/sfu_barrier_cuts_roof.json
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --graph-cls HC_ENG HC_CORE --out $P/sfu_barrier_cuts_hc.json
python3 tools/hbm_die_v15/sfu_barrier_cut_1016.py --plan $P --borrow-roof --roof-witness results/arch/hbm_die_v15/xc_rp4c_frame_1016/witness.json --graph-cls HC_ENG HC_CORE --out $P/sfu_barrier_cuts_roof_hc.json
python3 tools/hbm_die_v15/rf_centre_routes.py $P && python3 tools/hbm_die_v15/rf_centre_allocate.py $P
python3 tools/hbm_die_v15/rehome_v6.py --plan $P --out $P/grants_proposal.json
python3 tools/hbm_die_v15/hc_eng_home_1016.py $P --ablation v3_inner_client_x4=$P centre_v16_x1=$P/ablation_hc/centre_v16_x1 nechannel_512b=$P/ablation_hc/nechannel_512b ...
python3 tools/die_layout_render.py --hbm $P --grants $P/grants_proposal.json --out $P/layout   # + --window for the zooms
python3 tools/hbm_die_v15/cut_window_who.py $P h 5300 13100 > $P/cut_worst_window.json
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
