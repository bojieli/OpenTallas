# XS literal-lattice successors: pre-gate packet

The old p192c README's lattice claim was false. Five ring origins are off the
43.2um lattice: y83.184/123.168/163.152. Their immutable original gate remains
in physical/ref_tile/smh_xs_ring_p192c_1019. It is NOT approved for submission.
The current ring pitch is86.4um, with at_exact on all11 macros. No compact
3.24um non-pin sliver candidate is being gated.

Candidates: d475.2x388.8 (km32) and e475.2x432 (km64). e translates every macro
and its W/E pin bands43.2um north, preserving all internal macro distances and
N read-output distances, with more space behind S input pin flops. Both have
11 SRAMs: seven32x128 ring and four128x256 x-store. Every macro is R0. Exact
coordinates, immutable LEF hashes, signal/PG rectangles, track checks, and
planned PNGs are included. These PNGs show the exact LEF plan, NOT placement,
new density, or CTS. They were personally inspected.

Native census uses the original immutable mapped source, on active ep7 after
read-only transfer from ep8. It reports102599 cells,26135FF,11 macros,288.4ps
depth, no non-clock driver>32. Explicit reset_ports=rst_a: one direct sink,
one first landing flop; its kept second stage remains. All35 RTL/source files
match the immutable gate archive by SHA256 (source_identity.json). This is
structural evidence, not a native-cell behavioral proof. The root's discovered
Yosys DFFASRHQN model bug does not invalidate fanout counts; no adoption based
on that faulty functional model is claimed.

The actual source gate measured std11255um2 and macro44902.6um2. Approximate
fill is30.4% d/27.4% e. Area growth pays for four actual86.4-pitch ring rows,
>=46.44um N/S channels and>=34.776um W/E pin-face channels. This is a pin and
lattice-bound fill exception for coordinator review; no functionality is cut.

SAFE-DESIGN checklist:
1 Pins PASS source: unchanged input/output registers, io_flop_at_pins; rst_a
 ->rst_l0->rst_l1, raw port only one load. Fixed bit-order pin bands align
 o_iw N43.2..194.688 and o_ix N259.2..410.688; each788b at>=0.192um pitch.
 S bk1 spans43.2..440.448. W rl1 full302.4um span; full coordinates in spec.
2 Reach PASS planning for direct read/output cones: exact LEF rd_out->fixed
 IO capture targets max386.439um Manhattan, or396.439um allowing10um local
 FF displacement (1576 per-bit records). IO_FLOP anchors N FF x to pin x and
 moves y inward. All SRAM addresses/write-data retain existing macro-local
 posedge and negedge captures; the W/E channels admit these local banks.
 Actual complete placed per-net reach still must be measured after placement;
 >405um without a registered hop blocks submission. No Euclidean bounds used.
3 Fanout PASS actual mapped: all drivers<=32, resets included; no waivers.
4 Depth PASS actual mapped:288.4ps. Same ALU/shifter/memory stage boundaries.
5 Storage PASS: mutable ring7SRAM and x-store4SRAM; no new runtime flop store.
6 Geometry FIXED: all11 literal43.2 origins, zero off-track signal pins,
 max SRAM face5.095pins/um. Both W and E have signal pins (old 'W-only' claim
 was also false). Full N/S channels provide PG access; every POWER/GROUND
 rectangle is in *_pins.tsv. No overlaps; continuous full-width N band
46.44um, side corridors>=34.776um. All shapes from immutable native LEFs.
7 Clock PASS planning: same clk/posedge functional interface and existing
 negedge lockups for half-cycle SRAM writes; no phase or edge changes. N entry
 at237.6 between output bands, regional km32/km64, io_hold0.03. Original p192c
 spread42.2/41.6 and insertion618.5/500.7 are history ONLY; new CTS is unmeasured.
8 Schedule PASS: exact same RTL, memory ports and edge counts. Verilator5.050
 original C ring+legacy benches passed, read/write wrong-slot mutants failed,
 committed witnesses in results/rtl/smhxs_ring_1019/safe_ab. No compiler latency
 change; real child footprint replaces the old475.2x302.4 stand-in and needs
 SM/die slot re-plan after a child actually closes.

No gate or submit has been launched for these candidates. Coordinator must
spot-review this packet before the gate;18 prior non-CLOSED routes also make
submission REVIEW_REQUIRED. No REVIEW.json has been written by this worker.
