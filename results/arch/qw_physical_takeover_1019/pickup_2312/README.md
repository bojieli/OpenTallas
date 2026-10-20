# Qwen critical physical pickup, 2026-10-19 23:12 PT

Immutable failure receipts only. No REVIEW or submission. Original Claude worktrees and progressing remote jobs retained.

## N59 service split

Both qfd_n59_svc and svc_b gates completed FAIL with CTS rc137 at 23:10 PT. Gate start source 7c76190ee is recorded by each immutable shipping manifest; this packet does not assert equivalence with a later branch HEAD.

Original remote roots: ot-epyc7:/srv/opentallas-scratch/claude/ref_gate/qfd_n59_svc-20261019-220256 and qfd_n59_svc_b-20261019-220259.

Actual floorplan PNGs were viewed. Both show a 518.4x216 um std-cell-only rectangle, full-width rows, ck at N-face centre, signals across the full perimeter, no SRAM macro or interior power island. They are floorplan diagrams, with no placed cell mass: they cannot establish placement, reach or clock proximity. Gate reports actual pin geometry PASS (4471 rectangles, zero inaccessible/outside/missing), synthesized utilization 12%, and 18019 flops. The README's unconditional clock PASS is unsupported and superseded by this failure.

Observed CTS evidence: svc input-pin-flop TT range 327.611633..429.488617 ps (101.877 ps spread), FF 266.2098..357.5597 (91.350 ps); svc_b TT 352.456085..445.063141 (92.607 ps), FF 284.2941..375.199 (90.905 ps). These are intermediate QDM reference ranges in cts.log, not completed signoff clock_rule results. Before repair svc SS setup -356.59 / FF hold -36.97 ps; svc_b -378.11/-55.59 ps. Setup repair reports unable to repair all setup violations. Both then die during hold repair, after 20572 / 20822 violating endpoints. svc is still -25.150 ps after1300 iterations, svc_b -43.582 ps after1010. Exact cause of exit137 (OOM versus stall termination) remains unconfirmed: no OOM claim is made.

Checklist: pins NEEDS FIX (gate textbook finds qb_beat->fault 9 logic levels, despite opt-out claim); reach UNQUALIFIED (no placed result); fanout UNQUALIFIED (no native census); depth NEEDS REVIEW (583.5 ps combinational synth, SS setup failure); storage PASS for std-only service; floorplan NEEDS REDESIGN (13% density, pin-bound perimeter, aspect2.4); clock FAIL in intermediate input-flop ranges above80ps, final signoff unavailable; schedule existing split +1 and landed+4 contract unchanged by collection. Structural successor should localize service logic and clock regions with landed seams and explicitly register bank boundary/fault controls, then price any added edges. Do not rerun this same physical shape as a putative fix.

Qbank and qbank_b remained live in GRT on ot-epyc7 at inspection; preserve them. Their results have not landed.

## CB16 full parent functional blocker

cb16_full_lockstep_mut0.log is the original terminal fleet log (Verilator5.050, oth-ubuntu-183640-1792475865 on ot-epyc7). MUT0 FAR0 and FAR1 both unexpectedly fail: full5847 mismatches and fullb5830 over6000cycles. First full bit516 atcycle82; fullb bit912 (FAR0)/915(FAR1) atcycle100. This is a functional blocker, not a physical route verdict. Diagnose source/bench edge contracts before adoption; do not label it a source defect until isolated. Full parent gates on ep9 were still live in CTS and preserved. Main full uses pre-r1h21855ec80; fullb uses287a73718. A0 remains stand-in and full geometry has off43.2-lattice origins to resolve.

## Live A0 successor

Claude progressed rc7/rc7b at666a22494 (reset landing moved onto ck after rc6 isolated ck_fa4 failure). Four clients210927/210930/210931/210932 remained live at inspection, no terminal packet yet. Preserve; no duplicate launch.
