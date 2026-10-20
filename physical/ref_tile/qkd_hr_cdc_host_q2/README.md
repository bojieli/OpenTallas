# HOST6 HCDC qualified SRAM successor

Source proof and native evidence: results/rtl/host6_hcdc_1020/README.md. Exact canonical-event guards remove the prior arbitrary-state reset-copy CDC blocker without changing the checker, reset latency or steady event edges. Original source remains available.

Safe-design checklist before first gate:
- Pins PASS: generated per-family pin registers; all functional outputs registered; native constant_output_bits empty. Core reset lands in two registered stages, with 32-load leaves. Existing host-family boundary registers are retained under the multi-clock recipe exclusion.
- Reach PLANNED: E core / W host faces, pins confined to y302..454 with each clock beside its face registers; five macros centered on 43.2 lattice, no data path crossing >405um planned. Gate native reach must verify actual placed nets; no reach waiver.
- Fanout PASS: full mapped wrapper native max32, zero >32 / zero role errors,6394FF; includes reset+comb drivers. Census uses actual 5 standard-cell SS Libs plus macro SS roles. Repeated inside gate for exact kit.
- Depth PASS: mapped411.7ps, no input-output combinational bits.
- Storage PASS: channels use four 32x546 macros; fence queue uses one32x64 macro (effective8 entries). No runtime-indexed storage above2kb in flops. Pointers/status/copies are finite control state.
- Floorplan PASS: macro channels >=20um; 10.8um macro halos; 43.2um lattice; a full-width middle standard-cell band above fence SRAM (top280.536) and below upper macros (475.2). Full-face pins in152um band, core face <5 pins/um. Outline aspect<1.5. Synthesis fill measured by gate; macro/pin dominated.
- Clock PLANNED: independent core/host roots and exact per-clock-pin dual-SRAM ownership; soft-root bindings cover all7 raw memory clock pins. io_hold_margin_ns0.03. Gate must establish TT/FF pin-flop spread<=80ps; total insertion guidance only.
- Schedule PASS: identical original PIPE2/effective4+8 buffers and fence handshake edges; no extra steady-state or reset-release edge. No added credit protocol or scheduling change.

Gate and physical closure pending. Slot enlargement is explicit; die parent repack/adoption remains pending. No REVIEW.json/submit before passing gates and native proof.
