# QBS node reconstruction pre-placement review

Viewed `node_outlines.png` for the exact generated current-plan LLfu/LLfd/NNfu kits (43.2 x 77.76 um). Verdict **PASS-COND for PLACE prototype after normal SYNTH/LEC gates**. No route or timing qualification is claimed.

The E input buses occupy separate lower/upper bands with the clock/reset pair at the intervening center. LLfu sends data north, LLfd south, and NNfu exchanges north/south, matching their inherited return-tree roles. The 196/196/202 exact plan contacts preserve their ordering and face assignments. The 66-bit horizontal data banks use 0.096-um M5 spacing; E contacts use M4 with ample vertical separation. No macro walls, channels, halos, notches or slivers exist because these are macro-free regular rectangles. The entire outline's maximum Manhattan span is 120.96 um, below 405 um; no extra relay cycle is required. Existing M5 PG stripe and E center clock/reset interfaces stay unchanged.

Conditions: actual placed density, pin-to-register locality, related-register reach, clock tap load and continuous PG must be inspected from the resulting ODB; this pin-outline picture establishes only the plan's geometric feasibility. The parent still needs three actual routed EQ receipts plus the remaining six child joins and parent timing. Nothing here substitutes stub headers for a qualified body.

SYNTH-only jobs use 8 GB/2 threads, with no PLACE or STA until this review and normal proof gates. GEN initial attempt failed solely from missing sparse `physical/common_flow/clock_family.tcl`; fresh gen2 after materializing the tracked directory passed all three. Original failed GEN retained.

## Actual LLfu / NNfu placement followthrough

Viewed `node_placed.png` from the two actual `3_place.odb` dumps. Both PASS-COND for native CTS/GRT prototype. LLfu has 4,187 combinational std cells, 1,972 FFs, 2,082 buffers and 641 physical taps; NNfu 4,202 std, 1,978 FFs, 2,063 buffers and 641 taps. The ORFS placement report is 49% core utilization. The logic fills the rectangle without a central clump, macro obstruction or empty corridor; dense register bands follow the E inputs and N/S outputs. The layout is small enough that even the full-outline Manhattan upper bound, 120.96 um, is below 405 um for every possible launch/capture pair, and below 150 um for every pin/register pair. This upper bound does not claim net-specific STA or routed length. Existing center-height E clock and adjacent reset pins remain accessible. Core fill and geometry support the next prototype; real propagated CTS load/latency, GRT overflow, TT/FF and PG continuity still gate routing. No DRT or sign-off release yet.

Actual native source-to-SYNTH equivalence passed 2,066/2,066 for both, with the existing explicit S81 64-edge reset contract; standalone proof provenance remains absent and does not receive current release credit. Original numerical reports are retained untouched.

## Actual LLfd placement

Viewed the third actual PLACE checkpoint in `node_placed_all3.png`: LLfd has 4,187 std, 1,972 FFs, 2,086 buffers, 641 taps and 196 exact pins. PASS-COND for native CTS/GRT prototype under the same conditions. The south output-register band follows its south data pins, the east input bands remain accessible, and combinational logic is distributed through the available rectangle. There are no macro walls or long unrelayed geometric spans. All three current source-to-SYNTH proofs completed 2,066/2,066; original proof reports remain untouched and their missing standalone provenance remains explicit. No sign-off claim.

## Actual LLfu global routing: DRT release

Viewed `LLfu_grt_review.png` (actual GRT ODB cell/CTS buffer locations and 2.16-um area-density bins). Verdict **PASS for normal DRT**, against this exact current kit/5_1_grt checkpoint. The existing 83 named CTS buffers are spread through the compact register field, without a long off-center trunk. Logic and physical hold repair remain distributed; the denser E register strip has no macro wall or blocked pin channel. Actual global routing reports zero congestion on M2..M5 (total usage 14.49%; M2 24.42%, M5 4.57%). The entire macro-free outline still bounds every possible Manhattan register pair below 120.96 um. Pins/windows, PG grid and outline are unchanged. Detailed-route PG, DRC and pin access remain normal final checks.

Canonical `legacy_gate.py grt` passed on the same GRT database: actual TT setup +10.52 ps, FF standard-overlay hold +9.00 ps, 833 ps / 0-ps TT setup uncertainty / 25-ps FF hold uncertainty (current owner policy). The tool's old `SS setup` log label is stale: configuration explicitly selects `OT_MM_SETUP_CORNER=tc`, with TC and BC libraries; no SS sign-off is used. All 50,291 related register pairs were measured; TT maximum CPPR skew 20.64 ps, no unexpanded hard-child clocks. TT pin-clock mean 247.51 ps, FF 189.91 ps. The +10-ps hold-repair aim is not an additional sign-off gate; the policy itself reports PASS.

No SIGNED or parent-view adoption is claimed here. The actual source-to-SYNTH proof was 2,066/2,066 under the existing reset64 contract; normal final sign-off and own final-netlist equivalence still gate publication. Original proof's missing standalone provenance stays explicit. Neither the original failures nor any historical evidence was rewritten.

## Actual LLfd global routing: DRT release

Viewed `LLfd_grt_review.png`, showing the actual GRT checkpoint, 81 named CTS buffers, registers and 2.16-um density estimate. **PASS for normal DRT**. The compact macro-free rectangle has distributed local clock buffers and logic, with denser E input and S output-register strips beside their corresponding pins. There is no macro wall or unrelayed long geometric span; the same 120.96-um full-outline Manhattan bound covers every register pair. GRT reports zero congestion, and the full canonical TT/FF/related-pair policy reports PASS with TT setup +17.40 ps / FF hold +8.73 ps. Normal final DRC, antenna, PG and exact final-netlist proof still gate publication. No source, reset, interface or latency change was made. This is not SIGNED or a parent-view adoption.
