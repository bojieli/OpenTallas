# P3 SM SRAM packing feasibility, 2026-10-19

The original630.72x2203.2 rectangle admits34 existing children plus4 characterized16x546 dual-clock SRAMs and7 small32x128 pad SRAMs with every origin on43.2um lattice and10.8um pairwise halo. Fleet check PASS:45 rectangles, no overlap/outside/lattice problems, hard fill54.36%. packing.png inspected. candidate.json gives exact positions and baseline positions for changes.

This original packing is geometrically feasible but NOT zero-added-cycle reach qualified. Two dual-clock SRAMs at the BDC rows are too far from the central u_land_s receiver: the north bank has at least605um vertical output span alone. It must not be used as a safe-gate recipe. Matched macro-port reach analysis and a central-four-bank alternative are provided separately when ready. No input pin/clock/routing assumption is waived by the rectangle PASS.

The exact existing matrix frame stays23891.84x32120um=767.4059mm2 if matrix tile dimensions stayunchanged. Increasing tile height43.2/86.4um costs8.2570/16.5140mm2; width43.2 costs44.4027mm2. The ATT432 outline adds69.215mm2 of raw tile-area delta, giving836.6209mm2 arithmetic total. That is NOT a packed die frame: new ATT and VM geometry must be integrated into actual slots before any frame-fit conclusion.

Read-only model only; no edit to live DIE sources, RTL or kits. Fleet recipe: python3 safe_sm_packing.py candidate.json --out out.
