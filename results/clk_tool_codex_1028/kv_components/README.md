# KV clock c both-edge components from retained routed SDF

Run: intel1:/srv/opentallas-scratch2/claude/codex-clock-components-1028.
Source: die-kv-21-1028/out_c_{TT,FF}/{combo.v,die_<corner>.sdf}, exact
original LEFs/libs and root driving/output loading; read_sdf bc_wc.
Review: results/geom_review/codex_clock_components_1028/review.md.
Unit oth-ubuntu-385088-1793257254, 64GB/8threads admission, exit0.
No reroute. Source-polarity T/N/F/M readout from die_trial at1628fddd8;
final --clock-components exporter from7caabf04b. Own copies only.

Each corner: 1,920 taps, 15,424 nodes, zero missing, all taps/nodes carry
measured source fall. Original saved tap rise arrivals reproduced with
max delta0.014649psTT/0.020019psFF (printed SDF rounding).
Proofs: proof/tap_arrivals_{TT,FF}.json in the run directory.
Initial local export lacked die_sta_related dependency and was repaired
by copying its exact pinned source; this required no repeated STA.
The b154 decomposition is retained as .b154.json history; use the final
7ca source/local input-edge-aware decomposition instead.

Independent traversal of original ctree.v: 89 BUFx24 cells have 54 even
and35 odd inverter-prefix parity. At the32 PHY tap decompositions this
is20 source-rise-input-rise and12 source-rise-input-fall groups. Thus
the parity correction is material on the actual KV tree.

Component model vs old inverter-only spice_edge calibration changes
exactly32 PHY taps and zero others. TT rise late +2.49..12.70ps,
early -0.37..-0.09; FF rise late +1.79..10.32, early -3.63..-0.90;
FF source fall late +2.32..9.08, early -4.12..-0.78. Exact rows in
component_effect.json. This is a clock calibration effect, not a die
setup/hold result. KV owns the gate replay, NUMBER check and adoption.
