# KV HGI clock access under the fixed-reservation frontage option

Exact type `kv3_hgi_v2__cle0015330`. The A5t8 source plan hash begins `87d01254579e` and the retained detailed-placement ODB hash begins `c1adb7bfeadf`. The existing frontage image shows the 2.047 candidate keeps the fixed clock and PG reservations. Its −17.28 µm move of `head2_e2` covers the old local START origin and tap. The 1.219 wider frontage candidate requires replacing eight clock reservations and nine via-stack rectangles.

One same-track option for the 2.047 candidate is a **17.28 µm south shift of the `clk_t40` and shared `rr_t40` START boundary cluster**. The native M7 pin track is x = 159.328 µm.

| Element | Retained y (µm) | Proposed y (µm) |
| --- | ---: | ---: |
| `clk_t40` | 325.664 | 308.384 |
| Shared reader and writer seed | 324.000 | 306.720 |
| `cland_tstart_in[0]` | 324.000 | 306.720 |
| `cland_tstart_out[0]` | 324.810 | 307.530 |
| `cland_raw_reset_out[0]` | 326.430 | 309.150 |

The translated START origin rectangle is [150.688, 300.240, 167.968, 313.200] µm. It clears the shifted `head2_e2` by 6.480 µm and the nearest fixed clock reservation by 14.580 µm. The saved native M7 shapes show minimum PG edge clearance of 0.160 µm at the tap and 0.136 µm at the adjacent START/reset pins. The 17.28 µm shift preserves the 0.27 µm standard row phase and the original vertical M7 track. The narrower 12.96 µm same-track shift leaves only 2.160 µm from the START origin rectangle to the macro. No new parent-access via stack or enclosure has been measured.

There are eight reader and eight writer stage entries at the shared seed. Preserve their identities, shared-trunk behavior, `rr_t40` association, and reset/START release cycles. Keep the external forwarded-clock roots, their 833 ps relationships and edge polarity. `clk_t40` is a `clk` tap. The direct Euclidean length from the moved seed to the first unchanged `ft3_i` reader stage becomes 206.653 µm, up from 190.904. The corresponding Manhattan hop goes from 254.264 to 271.544 µm. For the `ft2_o` writer it goes from 289.616 to 306.896 µm. The other three first unchanged branch hops shorten. The separate eight raw-branch stage points covered near `head2_e4` and `head2_e6` still need source-local seats.

## Source timing conditions for any combined candidate

Rebind the same named tap and its parent access on every affected placement context. Check the exact route and via enclosure against same-phase M7/PG and fixed reservation geometry, then regenerate the tap's parent early and late insertion at TT and FF. The current generated kit has TT source window −11.1 to +9.1 ps for `clk_t40`, and nominal local insertion TT 250 ps and FF 202.5 ps with 40 ps tolerance. Those values describe the existing bind. Retain the intended sink cohort and check the 200 µm tap reach, 3,000 sink cap, and paired setup and hold paths after any reassignment. The stock source sink bins identify a historical checkpoint, so fixed endpoint assignment and reach are still open for this candidate.

Prove the affected TT setup and FF minimum paths with the regenerated parent early/late windows, particularly the two lengthened START handoffs and the tap-dependent reset release. Preserve branch counts, parent clock phase, and forwarded FCLK source-relative launch/capture behavior. No new STA or CAD ran. West demand remains 2.047 and east remains 1.606. Keep the HGI source and kit held.
