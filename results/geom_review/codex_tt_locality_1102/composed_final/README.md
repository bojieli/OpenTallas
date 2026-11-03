# TT_C composed zero-cycle source/model proposal

The targeted source model now passes: **45,301 typed capture endpoints, maximum 405.0 µm, zero DATA/reset/macro-port reach violations, and zero old-FF/macro body intersections**. The 16 replacement/new source slots are distinct native-row sites clear of the macros and other modeled FFs. Three old origin FFs are replaced, so the net increase is **13 FFs and zero mission or boot cycles**.

This is a disabled source/model proposal. Ordinary FF coordinates are relocation guides, not a legalized native placement. The original actual `3_place` image was viewed; `composed_source_preview.png` was also viewed as a source preview. It is not a new native LOOK or a route release.

## Coherent changes

- Relocate 2,978 existing FF homes using every first-register predecessor/successor across the actual combinational graph. This includes the boundary banks, TL/native-command readers, internal state/capture stages, and the remaining pad/control paths.
- Translate existing `cal.g_m[0].u_pm` and adjacent `cal.g_fifo[3].u_fifo` by +17.28 µm in x. Their 18.792 µm channel is preserved. Translate `cal.g_m[1].u_pm` by −8.64 µm in x to open the TL reader strip. All 19 selected masters, ports, R0 orientation and PG lattice remain; the outline is unchanged.
- Keep original SF/S0 sampling. Use four same-edge copies of s1/s2/pd and four same-D/CLK/depth raw-reset copies from `rst_rl_85`, retaining the central original raw leaf for S0/core. All 37 receiving instances bind to the corresponding regional start/start_d and raw-reset outputs. Source slots and both wrapper replacements are under `../regional_source/`.
- Price +13 positive-edge clock sinks, +9 qualified-reset consumers, +4 upstream raw-reset data loads, +3 S0 data loads, and +3 strap-pad mux consumers. No new clock input, clock strength, clock waveform, pipeline edge, partition type or interface cycle is introduced.

The final source event is default-OFF through `OT_TT_REGIONAL_ORIGIN=0`, exposed on the outer and bound wrapper. The source-file replacement/append manifest and all new producer sites are explicit. Changing the flag alone does not authorize publication or physical work.

## Exact macro and clock association

The read-only native ODB export matched all 265,172 net indices, all 19 actual macro instances, and 10,249 capture/5,002 launch pin associations without an unknown association. The selected real Liberty synchronous launch/setup/hold arcs and placed R0 LEF pin rectangles were used. Exact connected-pin reach found 611 additional macro-endpoint violations in the original layout; the conservative whole-box count of 672 was not treated as an actual failure count.

The existing SDC defines one named `clk` of period 833 ps over the same 63 ports. All other 2,770 forwarded-clock sinks retain their own cohorts. On these exact final homes the nearest-only peak is 1,251; **51 explicit same-cohort reassociations reduce the maximum to 1,200**, with maximum reach 189.083 µm and no unresolved root. The clock metadata contains 35,493 main-cohort sinks, including the +13 increment. It preserves cell clock edges and polarity paths; it must not bypass an inverter or clock gate.

The association is **not applied to a native tree**. It requires an actual-name join and an explicit phase-preserving pre-CTS policy in the paired source/model event. The old 999-sink receipt and old clock arrivals are not transferred. No arrival, skew, hold, setup or corner qualification is claimed.

## Local functional evidence

`../composed_checkpoint/proof13/` retains the actual frozen origin fragment, concrete raw-relay copies, native Yosys harness and logs. The bounded proof starts with undefined DUT state, exercises arbitrary other inputs and both strap values, and checks default-OFF/ON old origin outputs plus all raw-copy outputs after 64 qualified raw-reset edges, including a warm reset. Production passes; a real one-cycle-late mutant and a missing-regional-reset mutant are caught. This is local mechanism evidence; the original whole-part `UNPROVEN145` receipt remains unchanged.

## Before any physical step

Adopt source, parent/reset producer model, macro homes, register guides and clock associations as **one batch**. Re-derive the global paired plan/sidecar and source-clock/reset associations; perform native GEN/count/KEEP/ABI and actual-name joins, G0C differential with zero new findings, strict bind with zero errors, and the required actual geometry review. Start at the first changed RTL/placement stage; the old checkpoint cannot stand in for this source event. There is no partial 45-flop trial, no duplicate old placement, and no full-proof or route retry in this packet.

Other original die gates are deliberately retained as failures: fill/empty area, pin-register p90/max, channel/collapse/partial-face findings, full-part source proof, and all parent/IO/clock/corner contracts. Their next source work is actual landing-ring-to-pin relocalization and a coupled parent footprint/area proposal if no existing scoped policy applies; no utilization or pin-distance waiver is introduced here. This targeted pass does not sign off TT_C.
