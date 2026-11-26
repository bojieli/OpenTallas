# HEAD SPN parent-tied count strap placement

All 31 opposite-face flags in the exact `c83e1d4299b4` E8 detailed placement are count-align K straps. The complete read-only ODB replay reproduced the stock count and offender order. Every flagged pin reaches only the corresponding local `u_cland_*` ring after the first buffers and inverters. The native C83 parent tie audit, manifest and pinned parent top agree on the literal value of every flagged bit on all five SPN instances. The parent count-value audit passed 3,278 bits across the die.

The revised source moves these M5 pin centers from the west-middle cluster to the measured ring sinks. The existing `strap_sites` packing checks apply to every moved point. Its default 20 µm selection cutoff would have covered 17 bits. The exact stock layout check reports all 31 bits, so the scoped replay passes the full verified cohort to the same packing calculation.

| Count strap | Moved bits | Longest old span | Longest projected span |
| --- | ---: | ---: | ---: |
| `ad_i` | 6 | 1,501.689 µm | 23.562 µm |
| `au_i` | 6 | 1,481.439 µm | 20.202 µm |
| `bd_i` | 6 | 1,532.199 µm | 23.283 µm |
| `bu_i` | 6 | 1,513.137 µm | 21.396 µm |
| `hd_i` | 6 | 1,430.949 µm | 41.436 µm |
| `hu_i` | 1 | 1,334.262 µm | 1.911 µm |

Source `05e0572fe7f0` changes exactly 31 site coordinates. Schema passes with the original source assets. The stock opposite-face replay goes from 31 to zero against the retained detailed-placement sinks. The moved sites retain at least 2.16 µm Manhattan clearance to all detailed-placement signal pins. I viewed the exact projected north and south clusters against the retained pins. Plan, per-bit overlay, parent receipts, native sink census and viewed `spn_straps_source.png` are at `epyc8:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/spn_straps_1126/`.

The separate `x_i` FSTART repair is outside this source packet. The candidate needs an actual placed visual review before route. No placement or route was submitted.

## Combined SPN source

Reviewed plan `55d5f18017fa` applies the exact 31 count-strap locations to HEAD's `9e4df395a08a` FSTART seat plan. It preserves sidecar `a95abe5da907` and both corresponding `x_i` band declarations. The band sits at x 17.28–158.812 µm and y 1956.96–2021.76 µm. The nearest moved strap is 286.859 µm away. The re-emitted wrapper is byte-identical to the FSTART-only wrapper.

I viewed the exact combined layout projection and the stock plan render. The stock lean report carries the same inherited reach estimates for `bw_i`, `be_i`, `x_o` and `b_i` as both predecessor sources. The exact c83 detailed placement reported zero station groups or bits over 405 µm and a maximum timed sequential span of 399.6 µm. The separate 712 µm reset fanout advisory measures sink spread for `u_rrl_56`. The successor's actual placement review still needs to examine its reset fanout and the FSTART writer.

Combined source preflight passed with zero findings. Strict parent port binding, parent tie audit and nested bind passed for 27 masters and 359 instances. The published wrapper cohort matched on all 27 types. All 334 lanes passed without a latency delta. G0 reported zero errors and zero pending views. The inherited native release remains conditional for 12 targets. No placement or route was submitted.

The combined plan, exact source support, gate receipts and both viewed renders are mirrored under the same E8 directory as `combined_plan.json`, `combined_source_support.tar.gz`, `combined_gate_receipts.tar.gz`, `spn_combined_source.png` and `combined_lean.png`.

## Actual detailed placement

Stock place-only finished on E7, unit `oth-ubuntu-1390870-1795690747`. The exact `3_place.odb` SHA256 is `66973f928438f9d6bc23bb57927ef4accd1139e20f96857bcfadb52181639936`. The sealed source is `8e1958df4b5f` and the exact pre-submit review form is `1af5b40281dc`. The first submission completed generation and preflight, then stopped before placement because the dispatcher's approved host pool was empty. The retry supplied E7 as the sole approved host with spill disabled and used the same reviewed form.

I viewed the actual layout and density images. The stock report went from 31 opposite-face flags to zero. The longest moved strap reaches its native sink in 41.022 µm. The `x_i` FSTART pin-to-writer span fell from 128.531 to 81.335 µm. The remaining stock fanout marker is the existing `u_rrl_56` sink spread of 712.3 µm. Its 21 exact post-buffer leaves have a longest individual leg of 378.810 µm.

The independent image agent consumed exact private request `0fdcfe677dab5` and published `ISSUES` for pin escape at the north and south density pockets. The densest native bins are 0.673 at N x89.3/y2009.3 and 0.666 at S x189.3/y29.3. There are zero bins over the 0.70 threshold and zero density lumps. The worst 20 µm edge window has 46 M7 pins across 312.5 nominal tracks, or 14.7%. The grid check reports 5,178 pins and 7,648 rail rows passing. Actual routed escape is pending. The independent verdict remains in place and this packet leaves CTS and route held.

Exact actual images and the stock smell summary are in `epyc7:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/spn_55d_place_1126/kit_run_r2/gen/hd_spn/run/layout_review/place/`. The matching read-only native census is in the adjacent lane `native_review/native_paths.json`. The automated review is on Intel2 at `autopilot/private_visual_requests/0fdcfe677dab5d4680a37d7f79ec6ec9eb5f34ab07cc23e704e4fd70892a95bf/visual_review.json`.

## Perimeter escape follow-up

The independent review's concern traced to 29 specific M7 data starts in the exact placed checkpoint. The read-only native audit checked 1,952 M5 and 2,007 M7 pins on the north and south sides using each pin's actual track, first 3 µm of inward continuation, neighboring pin boxes, fixed PG stripes and via enclosures, and routing obstructions. No audited master carries M5 or M7 geometry. The worst native 20 µm M7 window has 45 pins and 274 clear straight tracks through depth 40 µm. The 29 individual denials all come from 27 inboard clock and landing control rectangles.

The two closest conflicts are `ad_i[33]` on the north at x501.600 µm behind `fclk_in_ad_i` and `b_i[283]` on the south at x235.680 µm behind `fclk_in_b_i`. Both lose a straight witness 2.032 µm inward. The other 27 lose it at 2.200 µm. The complete ranked list identifies each pin, blocker, first interruption and spacing.

Reviewed candidate `e2ee9c5d0fc9` moves only the 27 inboard M7 X coordinates, using shifts of 0.064 to 0.320 µm. Its two forwarded input clock tap coordinates follow the same moves. The first projection selected an ordinary track that the stock dual-PG-phase snap moved back to the blocked coordinate. The corrected projection selects a stock snap fixed point for both input clocks. Stock generation confirms all 27 new coordinates. The simultaneous projection clears all 2,007 M7 stubs, preserves data-face pin sites and all 31 CA strap locations, and keeps the `x_i` band and sidecar exact.

I viewed the exact north/south obstruction zoom and stock typed render. Ranked native evidence, source move table, projection and gate receipts are in `epyc7:/srv/opentallas-scratch2/claude/CODEX-CLOSURE-SWEEP/spn_55d_place_1126/native_review/escape/`. Actual post-fix pin escape and an independent review of the new placement are still required. The prior independent `ISSUES` remains recorded on its original checkpoint.

The exact source passed preflight with zero findings, strict and nested port binding, parent tie audit, all 27 wrapper comparisons, all 334 lane checks and G0 without errors or pending views. The inherited 12-target native release receipt passed with its original 26 byte-pinned inputs stored relative to the proof. The reviewed sealed source is `7253d641f54c`. The stock place-only submission on E7 uses exact form `eedcd34d5be6`. CTS and route remain held.

## Actual placement after the escape repair

Stock place-only passed on E7, unit `oth-ubuntu-3094017-1795693531`. Exact placed ODB `0477d7900476e6a668a1d1146aed38ba5abd18c0d8364521f80998ce7d18e0f8` matches reviewed source `e2ee9c5d0fc9`. All 27 moved rectangles landed at the reviewed exact coordinates. The read-only native replay measures a legal inward 3 µm same-layer straight start at all 2,007 north/south M7 pins and all 1,952 M5 pins. All 29 prior denials cleared. The tightest 20 µm window still has 45 M7 pins and 274 clear straight tracks through 40 µm. This measures initial pin access on the placed database. Routed escape and route DRC remain open.

I viewed the exact actual layout, density, and obstruction zoom. The stock report shows zero opposite-face flags and maximum density 0.672 against the 0.70 threshold. Its only flag remains fanout spread, 712.0 µm. The exact pin audit, placed source location checks, per-pin witness data and viewed `actual_spn_escape.png` are under the escape packet's `post_place/` directory.

The automatic independent image review consumed exact request `8e4257fd307915da3275e66c29b2f1ffa5fa1c6cf6b67ae2d70f8da7a0637b8d` and returned `ISSUES` for pin access through the south density band. A second independent pass viewed the same stock PNGs plus the exact native zoom. It confirmed the corrected 3 µm starts and kept `ISSUES` for access through the wider band. Both receipts are preserved. The supplemental receipt is `post_place/escape_supplemental_visual_review.json`.

The deeper native replay in `post_place/dense_window_depths.json` covers the four visible north/south density pockets. Each of the 2,585 pins has a simultaneous straight same-layer witness through 8 µm, and 2,581 have one through 40 µm. The four exceptions each reach beyond 8 µm and meet a fixed peer pin. The sole south exception is M7 `b_i[525]` at x296.16 µm, behind `clk_t2` and `rst_start_raw_1`. North exceptions are M7 `fclk_in_x_i` behind `clk_t39`, M7 `hd_i[271]` behind `clk_t41`, and M5 `bd_i[8]` behind the aligned `strap_ca_k_bd_i[1:5]` sites. These are specific local turns or via-access cases. No missing straight witness was attributed to power geometry or cell density. CTS and route remain held.
