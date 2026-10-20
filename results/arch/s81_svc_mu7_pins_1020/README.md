# S81 service production ABI pin/slot structural packet

Collected 2026-10-20 07:30 PDT. **MODEL ONLY. No new RTL, die plan, hardened view, physical qualification, or fleet launch.**

The saved p4l plan reproduces 6.727 pins/um at rsv_13/W and rsv_15/W (8,999 active lane bits / 1,337.84 um). Its N/S maximum is 7,755 bits / 1,251.974 um = 6.194 pins/um. The saved plan also records 74 relay overlaps and 32.2 bit-mm lane/body overlap. These failures are preserved; this packet does not claim to fix them.

`model.py` reads archived source bytes and checks the exact production port declarations against **every** width in the saved main caller table. RS_OBS is absent; entry callers are exactly rsv_05/rsv_11. The existing main source already internalizes SM target outputs; w_* are observation-only ports. No source specialization or removal is introduced here. The table has no hardened svc view. Native source/default SRAM configuration and runtime RTL-ref resolution remain admission gaps.

| Inventory | N | E | S | W | Pin-sizing minimum on 43.2-um lattice |
|---|---:|---:|---:|---:|---|
| Current production nonentry | 9,090 | 9,090 | 10,340 | 9,090 | 1728 x 1555.2 |
| Current production entry | 9,652 | 9,652 | 10,340 | 9,382 | 1728 x 1641.6 |
| Historical landed nonentry | 9,646 | 9,090 | 10,340 | 9,090 | historical packing 1728 x 2073.6 |
| Historical landed entry | 10,208 | 9,604 | 10,340 | 9,382 | historical packing 1728 x 2073.6 |

The current source has one ck rather than the historical ck_c/ck_sm split, internal SM target, up_i/up_o rather than split up_d/up_f, and entry pv_x[47:0]. Historical kit geometry must not be relabelled as production geometry. The copied historical generator is an inventory comparator, not a current production kit.

A uniform **1728 x 1641.6** outline keeps maximum aggregate face density 10340/1728 = 5.9838 pins/um. Its sixteen slots add **18.587902 mm2** over the saved p4l slots; preserving all inter-column gaps needs **3808.208 um** more width across eight columns and **607.52 um** more height across two rows. Mixed nonentry/entry minimum slots would add **16.497714 mm2**, but unequal row heights complicate abutments and are not proposed as a coherent die plan. Historical 1728 x 2073.6 packing adds 30.531838 mm2; use that larger height only if the actual production child model requires it.

The active-lane-only lower bound 1296 x 1512 adds4.553778 mm2 but fails the full production ABI (S density7.978). It is not an implementation candidate. No aggregate-six exception follows from using two pin layers.

`production*_pins.json` enumerate every current source bit. `candidate_*_geometry.json` and `.tcl` place each exactly once on actual archived M3/M5 (N/S) and M4/M6 (E/W) track lattices inside the expanded uniform outline. Counts are 37,610 nonentry and 39,026 entry. Generator assertions check source/caller width equality, complete bit coverage, no duplicate face/layer track, and boundary margins. These are candidate grid coordinates, not a physical capacity or PG proof; PG/OBS, pin access, signal/via keepouts, source registration, internal clock/reset/storage, and child packing remain open.

Coherent next model must repack these slots with CTRL's +86.4 array shift and TOPK's518.4 x648 quarters. Do not stack the old +70 placefix blindly. The old placefix's72 extra stations and +2.39% relay bit-stages came from another immutable plan and cannot price this geometry. Recompute every lane/body/relay collision, real Manhattan405 endpoint distance, added station/capture ages, source clock/reset topology, compiler latency and full protocol before requesting source admission or any new gate. A physical failure requires structural redesign.

Source refs: main dd875958b0119c9739332101b4e19334f643fa66, prior placefix6e3559855, historical kit c8cb29cf3. Every archived byte SHA256 and exact original plan failing counters are in model.json. Reproduce with `python3 results/arch/s81_svc_mu7_pins_1020/model.py` (stdlib only, no RTL synthesis or fleet job).

## Conditional hierarchy packing blocker (07:39 PDT)

The pin-sizing minimum is not a full service-slot proposal. The existing SVC lineage `mk_attw_lp.py` expects sixteen hard head groups per attention parent. Evaluating only its geometry section with unchanged std-area parameter190000 and hgrp8 child432 x432 produces2851.2 x2160 um (=6.158592 mm2) for the attention parent alone. Its modeled macro inventory is272 SRAM32x64 inside the groups,32 large centre macros and38 small centre macros. These are source-pinned conditional generator outputs, not admitted current-main children or a qualified view. Dispatch/view integration is still unimplemented.

Even before channels and other units, sixteen432-square child outlines reserve2.985984 mm2, exceeding the uniform source-pin minimum2.836685 mm2. Therefore neither a1728 x1641.6 pin outline nor historical1728 x2073.6 packing can be assumed to hold this parent. Full service/SM/SX/controller/source hierarchy must be composed and re-packed before selecting any final mu7 slot. The hgrp8 gate is still running; no physical closure or adoption is claimed.

The saved die has frame_top24619.44 and height25000, leaving380.56 um above the frames. Uniform two-row service pin growth alone asks607.52 um more height at fixed gaps. A blind upward shift exceeds that local slack even before CTRL changes; this does not prove all repacks impossible. The die owner must solve width/height/slots/track corridors jointly.
