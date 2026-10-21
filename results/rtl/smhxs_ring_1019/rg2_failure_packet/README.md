Terminal rg2 is FAIL. Trial GRT finished with zero overflow (1561s), but actual TT/FF boundary pin-flop spread is149.5/136.4ps against80ps. All-sink spread185.9/153.6ps is reported separately. TT placement diagnostic register→macro read-address setup is−79.999ps; hold+35.379ps. Macro→reg+123.4, reg→reg+144.8, reg→output+121.2ps. This is preserved failure evidence; no REVIEW or submission.

The independent graph reads the actual final4_cts.odb, without rebuilding or modifying its tree:20550sinks=20542FF+8SRAMs. Native I/O4536clockpins and8SRAM clockpins all traverse16buffer stages.20534phase0FF are16stages; exactly8intentionalnegative-edge wce3/rce3 controls are17 through their own phase inverter. Final physical inventory854BUFx24+8INVx1; the prior in-memory reconstruction had one shared inverter before physical replication. Phase classification does not waive the measured spread failure.

Inspected floorplan/density PNGs in physical/ref_tile/smh_xs_ring_rg2_1019/gate_layout: eight macros on43.2lattice,34.776/45.36um inter-macro channels, full faces, contiguous southern standard-cell mass, sparse north. Final floorplan occupied standard-cell area11254.1um2 differs from conservative preflight synthesis13468.217um2; hard envelopes31132.616um2. Preserve both measured scopes. Final fill28.39%; parent approved geometry waiver for lattice/channel constraints.

All8 SAFE review:
1. Pin/reset: PASS previous face registers and2reset landing stages retained;4543actualpinrectangles accessible/ontrack/inside. No new external transport edge.
2. Reach: retained prior data-stage boundaries; regional successor must remeasure full physical reach. No release qualification while clock partition is unresolved.
3. Fanout: source-bound actualmapped11678straproots max32, middle28. Regionalreset33 is an explicit parent-accepted one-load exception. Never infer a copy count from source text.
4. Depth/timing: source logic~288ps/under20level budget; TT reg→macro half-cycle address path−80ps is a blocker for successor design, not waived by logic depth.
5. Storage: PASS8SRAMs;788b×3long flop delay replaced by4-slot ring with4newSRAMs. No runtime wide flop array/long flop delay.
6. Floorplan: WAIVED lowfill for43.2lattice/channel/full-face constraints; inspected macro channels/fullwidthstdcellregion. Geometry432×345.6, aspect1.25.
7. Clock: FAIL boundary149.5TT/136.4FFps>80; macro clock slews and placement address timing also need regional/native correction.16/17phase counts explicit. Holdmargin.03.
8. Schedule: PASS staticII1; full788b3000edges seed23 zero mismatches +wrongslot mutant rejected; same3startup and0addeddataedges. Any new boundary edges require explicit model/compiler pricing.
