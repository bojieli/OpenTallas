# QC sle_sc_v1 cl115da35f attempt 2, 22:13 PST

Viewed the exact E8 `3_place` layout and density from `epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V4/items/sle_sc_v1__cl115da35f/attempt_2/gen/sle_sc_v1__cl115da35f/run/layout_review/place/`.

**Fix first.** The macro occupies the upper east. Active standard cells bunch at north and west face entries and along the inner macro edge. Large stretches of the tile remain empty. The scan reports 5.73% fill, 75.18% empty area, pin-to-register p90/max 268.51/356.38 µm, and an 867.51 µm register-to-register outlier. Horizontal and vertical channel demand ratios reach 1.881 and 1.963. Connect the affected register and approach lanes in the scoped SC-DRT-CORNER form before a new route. Prior route evidence stays available.
