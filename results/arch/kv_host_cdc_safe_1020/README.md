# SRAM CDC PC successor (not adopted)

The original six host gate candidates fail the binding native driver limit. Their mapped census is preserved in old_gate_native. The pc/host CDC leaves each had 2,187-load pointer roots and runtime-indexed payload arrays over2kb implemented with flops. Gate PASS/WARN used the old3,000-load threshold. Those old closures cannot establish current qualification.

The isolated SRAM channel replaces both receive and crossing arrays with real existing-interface SRAMs. Effective receive depth4 and asynchronous depth8, credits, reset release edges and PIPE2 transfer timing stay unchanged. Zero-address padding uses32-row macros; no additional usable credits/capacity are advertised. Source state, reset-bank leaves and16-bit bypass selects are kept and checked after canonical mapped synthesis. No legacy source is switched by default.

The distinct p192_mir macros follow the existing QW pin-access recipe: unchanged storage and port semantics, 0.192um pitch (<=5.21pins/um), stretched177.768x160.392um abstracts, and conservative M4 lead RC in TT/FF/SS setup/clk-to-Q/caps/energy. All old views remain immutable. Fourmacro area114,050.26um2 drives a475.2x518.4 candidate, versus151.2square. Origins43.2/259.2 by43.2/302.4 are on the43.2um lattice; an approximately98.8um full-width middle band remains. Parent/die repack is UNGRANTED; no fit or unchanged-die-latency claim.

The expanded Gray-FIFO tool remains opt-in. It fingerprints the new source, behavioral macro, blackbox and all3 Liberty corners; verifies every declared read/write pin role against actual Liberty; checks actual mapped input-family cones; and preserves the existing Gray publication/synchronizer proof and finite crossing budgets. No false path or data multicycle is added. Actual full-PC proof and wrong-writer-clock negative pass; all24 existing Gray-FIFO tests and7 new tests pass (31 total). ROOT must review/adopt the helper before any layout gate.

Native qualification uses the source-pinned94de8573f mandatory census prototype, with the actual5 ASAP7 SS libraries plus2 macro SS views. The generated pin/reset wrapper has7,826flops, depth278.4ps, one raw reset sink, and max32 dynamic terminal loads through actual Liberty BUF/INV functions; role errors0/violations0. candidate.json pins the mapped SHA and library hashes. This is pre-layout evidence.

SAFE checklist:
1 PASS: data faces registered, actual per-port wrapper/table archived; kit2-stage reset landing, native raw reset1sink.
2 PLANNED: central band and local macro pairs; physical reach must be checked in layout, no measured reach claim.
3 PASS: mandatory functional-Liberty BUF/INV terminal-union maximum32, resets/macro contacts included.
4 PASS pre-layout: full-wrapper mapped depth278.4ps; macro TT clk-to-Q373.5ps from priced view. Routed SS/FF remains owed.
5 PASS: both >2kb runtime payload arrays in SRAM; effective4/8 depths retained.
6 PASS geometry: four on-lattice macros, p192 faces, central full-width band, explicit macro halos; actual placement/PNG review remains owed.
7 PENDING physical: same two real independent family roots, no weakened budget; spread/PG/boundary references need gate/native audit.
8 PASS leaf steady schedule: zero edges changed in member miter; parent wire-hop/calendar consequences unmeasured until repack.

V5.050 exact-cycle miter passes3431/3431 full-width transfers over asynchronous clocks and reset flush. Wrong macro read address and removed same-row bypass both fail with committed witnesses. A full-production-shape saturation leg at the one-frame-per-two-read-edge budget is being collected separately before adoption.
