# SRAM CDC PC successor, variant 1e (domain-sided floorplan, not adopted)

1e: 475.2x648 outline, 228 um middle band, every pin + pin flop inside the band beside its clock. 1f: 561.6x561.6, 86 um std-cell strips between each macro column and its IO face, pins over the full face. Both after 1c/1d CTS TT spread 121/150 ps (pins spread along the 38 um strip beside the macros).

KV-HOST6 10-20 structural redesign after gates sram1/sram1b reached CTS and failed TT ck_core pin-flop spread 125.8 ps (insertion 592 ps): ck_core entered W while core data (physical_tx_d in, raw_rx_d out) sat on E and N. Here each domain owns one side: core logic, both core-clocked SRAMs (rx af read side, tx ib), all core pins and ck_core on E; phy macros (rx ib, tx af read side), phy pins and ck_phy_fam on W; host_rst_n on N. Right-column orientation MY (macro W-face pins turned toward the E core face). Data faces ~2.5 pins/um. Same RTL/benches/schedule as sram1 (zero edges changed). Parent slot faces change (slot repack was already owed). Original sram1 README follows.

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

V5.050 exact-cycle miter passes3431/3431 full-width transfers over asynchronous clocks and reset flush. Wrong macro read address and removed same-row bypass both fail with committed witnesses. The full-width saturation leg passes: 1,408 frames / 1,761 read edges = 0.7995 frames/edge against the 0.5 frame/edge production peer service budget, with the same cycle-by-cycle legacy miter (4,185 total transfers).

Measured wrapped synthesis area116,982.02138um2 includes114,050.260224um2 of macro area; standard cells2,931.761156um2. Candidate total fill is approximately48.3% of the core. Both clocks and W/E data faces are ranged into the central band; no placement measurement is implied.

## Collected gate 1e (Codex 10-20)

Actual ed2cf338a gate source and immutable binding retained in gate_result.json: WARN,0FAIL/4WARN; native32 max32; GRT overflow0 (M2worst13.22%); TT setup+40.15ps, FF hold+46.37ps. Boundaryspread coreTT47.1/FF43.5ps, PHYTT59.8/FF54.0ps. Insertion720.3/598.3ps guidance requires per-domain parent compensation/landing; insertion alone is not a failure. Macro->reg+40.1ps/reg->macro+52.1ps; no undeclared crossing setup violation (all timed cross paths positive).

Both floorplan/density PNGs inspected: four macros at(43.2,43.2),(43.2,432),(259.2,43.2),(259.2,432), R0/R0/MY/MY, all43.2um lattice. A full-width228um central standard-cell band separates macro pairs. Clocks sit on opposite data faces in the same band, with core onE and PHY onW. Outline475.2x648um/aspect1.36; full face demand538.3um/face,1187W/1151E pins (<=6/um). Measured totalfill38.6% is below40-60% target; reducing band/face extent already failed previous variants' CTS spread. No hidden density waiver or parent-fit claim: coordinator reviews the pin/clock-constrained cost. Old closed leaf151.2square ->new307929.6um², growth285068.16um², parent repack and boundary compensation owed. Zero leaf protocol edges added, but parent physical wire-hop/calendar changes remain unmeasured.

REACH FAIL: actual5_1_grt.odb transparent BUF/INV terminal audit checks19707nonclock/nontie driver/sinkpairs and finds285>405um, max597.82um; reset and real data paths both violate. Complete pairs/ODB SHA/script/logs are retained in results/rtl/kv_host6_pc_1e_collect_1020. No submission/adoption of1e; structural domain-matched macro placement, all-cell band and centered regional reset distribution are required. The prior textbook 'reach0' is not a substitute for that audit. Canonical inherited dual-role checker adoption (9eeb7aa07/c56d783f4 delta) is separately under ROOT/shared_source_review; this source-pinned gate is preserved, no canonical submit yet. 1f failed PHY TTspread80.8>80; failure receipt preserved independently.
