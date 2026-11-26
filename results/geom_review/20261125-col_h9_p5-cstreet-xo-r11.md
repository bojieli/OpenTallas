# S81 R11 P5 XO landing band geometry

Viewed the E11 exact GRT density and path zoom for `col_h9_r0_p5__t1__pvb22875c0` under `S81-ALLFIX-INT/col_h9_r0_p5__t1__pvb22875c0_1125072928/gen/col_h9_r0_p5__t1__pvb22875c0/vis_review/grt-1125-2145PST/`. The east rim group reaches local density 0.986. The worst setup path is internal to `u_cland_xo_i0`, from a ring control flop to `lap_ok`. The lower ROM-bank detour appears on separate frame paths.

Draft for cumulative R11 exact plan `0d5314512c28c176d230a42948c4601e981991d71f873d5b1af4ac9cc86789f3`. Widen the existing 1104-bit XO FF placement band from 38.88 to 64.80 µm toward the interior. Its east edge and its 239.964 µm vertical span stay fixed. Area rises from 9,329.8 to 15,549.7 µm². Modeled ring reserve use falls from 0.475 to 0.285, maximum pin-to-band reach rises from 178.602 to 204.522 µm, and the closest hard macro lies 12.852 µm west of the proposed band. The change carries the same band into the owner, frozen copy, and collector-local records. The pin contract, stages, and physical hard-core placements stay fixed.

Viewed `epyc12:/srv/opentallas-scratch2/claude/FP-S81/refsite/c_street_r11_p5_xo_band_review.png`. Guarded draft operations are in the same directory, `c_street_r11_p5_xo_band_draft_ops.json`. Static review favors a scoped PRE and bind after the current pilot gates. CAD dispatch remains held.

## Pin-slot placement

The exact kit placed all 11,767 ring flops with the native east-face pin-slot mapper at spread 1.000. It left 42,093 ring logic cells to global placement. The preferred proposal couples the wider band with the existing type-specific `cland_strip_rows_types[P5]=6` setting, which raises E/W pin-slot spacing within the expanded site's available capacity. Pin order and the east side remain fixed. The mapper caps the requested spacing at the legal fill spread. This proposal is in `c_street_r11_p5_xo_strip_draft_ops.json`.
