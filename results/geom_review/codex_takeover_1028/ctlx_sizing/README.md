# CTLX structural sizing: preferred M5 pin-layer candidate

**Proposal, not adopted or routed.** The existing k13/guided2 source is unchanged, with no RTL or fixed core-cycle change. HBM die owner conditionally accepts this estimate/trial scope and prefers the M5 variant if its lower-pin access works. No threshold is relaxed.

The 391.392×416.448 µm lot is sized by its **single-layer external pin boundary**, not its native logic. It has 2,192 E pins on M4, 2,054 N pins on M5, 1,375 S pins on M5, plus 158 W functional pins and clock/reset. At six pins/µm, a single layer still needs at least359.61×382.61µm. Shrinking the current pin table blindly cannot fix the low fill.

Actual guided2 native area is10,652.26µm² standard cells +3,893.85µm² SRAM: free-area fill6.70%. The face shell has2,388 input and3,391 output FFs; the body has13,392 FFs. This is a real functional controller and SRAM, not an empty logical feedthrough frame that should simply be called a strip.

The proposed outline is**216×233.28µm**. Keep every bus on its current face and preserve order on each pin layer, but use two layers:

| Variant | E/W pins | N/S pins | Core ceiling | Added M6/M7 obstruction/core |
|---|---|---|---|---|
| Preferred M5 | M2 + M4 | M3 + M5 | M5 | None |
| Higher-pin fallback | M4 + M6 | M5 + M7 | M7 |50,388.48µm² on each layer |

Exact bit/layer/track coordinates are in `m5_lowpins_pins.json` and `m7_highpins_pins.json`. Nominal per-layer spacing is~0.192µm, snapped to the actual layer grid; measured peak in either candidate is5.2pins/µm. Clock pins stay M5. A small G2 pin-access/capacity probe must establish that the new lower-layer pins land safely:2,890 pins gain two lower via levels, at most104 extra via cuts per10µm of face, for a proposed2.16µm access band. This is a capacity estimate, not a pin-access PASS.

Move the same SRAM, unchanged dimensions/orientation, to(60.48,142.56). Main clock entry is(108,116.64), below the macro; `clk_cal` lands in the upper band at(108,198.72) with a small reserved pin-entry keepout. Resite the same nine driver islands: root centre and two columns×four rows; no new clock/reset feedthrough ports or cells. Coordinates and exact four-array edits are in `physical_contract_delta.json`. The clock roots remain `clk`/`clk_cal`; there is no domain or cycle change.

The projected native-cell map is nonexpansive outside the fixed-size SRAM. It is **not a legal placement**. It predicts free fill22.91%, empty-bin share22.51%, and full native graph r2r296.2µm with zero>405. `ctlx_sizing.png` shows actual guided2 beside the projected alternatives and was personally viewed. Clock entry-to-core-corner reach is216µm; an actual planned tree and STA still have to qualify its loads/insertion.

Keep the new cores within the old rectangles, on the8.64µm placement grid: origin delta(+86.4,+95.04), centre shift(−1.296,+3.456). This frees112,605.94µm²/core,450,423.74µm² across four planned instances. No neighbour can gain an outline overlap from the shrink. Preferred M5 preserves the die's M6/M7 over-routing; the M7 alternative does not and remains conditional on the composed die capacity.

**Parent links must be recomposed; do not claim zero total token-cycle change.** The actual hub graph contains only the two north q1 native CTLX roles, while the plan has four instances. On452 measured native edge groups/26,120 bit pairs, the snapped-centre proposal reduces aggregate endpoint bit-distance from88,160.79 to87,133.00bit-mm, but31 groups/2,642bits cross one additional *minimum*405µm-hop boundary. Existing parent stations may already provide margin; this is not an automatic added-cycle count. The two direct1,024-bit CTLX→p1_bfq3 buses would grow from328.75 to466.73µm and require a structural response.

A concrete optional response is to move the existing p1_bfq3 cores+69.12µm Y in each hub. Their new rectangles have zero AABB collisions with the current plan, and all454 relevant graph groups/26,632 bit pairs were reevaluated: the direct buses become397.61µm, and no non-CTLX BFQ edge gains a minimum hop. The remaining13 groups/540bits still cross a minimum-hop boundary (mostly257-bit bank7 returns and long status paths). See `die_impact_centre_bfq69.json`; clock/reset/FT and actual stations must still be recomposed. Alternative S/SE anchoring worsens aggregate bit-distance and raises affected hop groups to61/118, so it is not preferred.

The graph lacks south q0 CTLX roles and24 host-leaf edges have no matching hard-core identity in this snapshot. No substitute connections were invented. Recompute on the strict full C25c bind before adoption; price any actual new stations in the compiler/model.

Inputs: k13 freeze view `ot_hgi_sm_xload_cl2_ctlx@a49447763f6a`, recipe key `e109b13d19921055b841bd14447183d92ce0ee1cf1381ec9c2b1058337e190e3`, source C25a + KITS5 cmdt387720be57; exact guided2 source/receipt owned by guided2 receipt commit `06b66ec1c`. Plan/graph input hashes are recorded in the impact JSON. `estimate.py` and `die_impact.py` are diagnostic sizing helpers using the preserved artifacts, not production kit generators. Neither P&R nor STA was launched for this proposal.
