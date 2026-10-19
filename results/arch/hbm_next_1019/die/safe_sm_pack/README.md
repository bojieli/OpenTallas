# P3 SM SRAM packing feasibility, 2026-10-19

The original630.72x2203.2 rectangle admits34 existing children plus4 characterized16x546 dual-clock SRAMs and7 small32x128 pad SRAMs with every origin on43.2um lattice and10.8um pairwise halo. Fleet check PASS:45 rectangles, no overlap/outside/lattice problems, hard fill54.36%. packing.png inspected. candidate.json gives exact positions and baseline positions for changes.

This original packing is geometrically feasible but NOT zero-added-cycle reach qualified. Two dual-clock SRAMs at the BDC rows are too far from the central u_land_s receiver: the north bank has at least605um vertical output span alone. It must not be used as a safe-gate recipe. Matched macro-port reach analysis and a central-four-bank alternative are provided separately when ready. No input pin/clock/routing assumption is waived by the rectangle PASS.

The exact existing matrix frame stays23891.84x32120um=767.4059mm2 if matrix tile dimensions stayunchanged. Increasing tile height43.2/86.4um costs8.2570/16.5140mm2; width43.2 costs44.4027mm2. The ATT432 outline adds69.215mm2 of raw tile-area delta, giving836.6209mm2 arithmetic total. That is NOT a packed die frame: new ATT and VM geometry must be integrated into actual slots before any frame-fit conclusion.

Read-only model only; no edit to live DIE sources, RTL or kits. Fleet recipe: python3 safe_sm_packing.py candidate.json --out out.

## Central-four-bank alternative: conservative local reach PASS

central_candidate.json keeps the original outline and all34children, moving4 row transport children to the free BDC-side slots and all4 SRAMs into the centralband. LandN129.6,950.4 R0; LandS388.8,950.4 MX. Bank0(129.6,1166.4)R180; bank1(129.6,1036.8)MY; bank2(345.6,1036.8)MY; bank3(345.6,1166.4)MY. The macro instance bank number must follow the explicit assignment, not position order. RowwN432,1598.4/S432,475.2; roweN561.6,1598.4/S561.6,475.2. All other positions in central_candidate.json.

Fleet rectanglecheck PASS45rectangles,10.8halo,54.36% hardfill. Matched exactLEF readports rd_out[bit%546] -> u_land_s.d[bit], applying actualR180/MY/MX transforms: worst343.5um L1 over2069bits. Sixty-five sourceu_pb32bit registerregions are in central/source_regions.json, each10.8x8.1um and nonoverlapping, outsideallhardchildren/macros+10.8halo. Every original bin input pin -> its capture region -> its exact SRAMwritepin, plus capture -> u_land_n.d and u_beat_t.d, is conservatively<=361.398um L1 INCLUDING9.45um worstregionoffset. Regionassignment canbe enforced by perbit source-register placement; no new logic edge is required by these local geometric paths.

This does not qualify the4 relocated rowtransport children: their matched parent rin/rout face pin groups mustmove near the new BDC-row slots (authorizedtop-down pinplan), and every fixed localhop mustthen be checked. The die must regenerate exactboundarypins and replan relaystations; no latencycost is assumed zero until that graph is measured. SRAMcontrol/address/clock paths and padSRAM endpoints also require source-specific placement and a realgate. TT/FF timing/hold/clock qualification remains pending. Original rectangle-only BDC-bank candidate remains rejected for zero-extra-cycle reach.

## Pad reach caveat (parent review)

The initial7pad rectangle arrangement includes3 pads at y2116.8. Those cannot implement the south3-edge alignment path row1(y475)->leaf1(y648) at405um/hop; do not use that arrangement for a gate. Parent proposes replacing the pad positions with(432,604.8),(518.4,604.8) and x302.4 at y259.2,302.4,345.6,388.8,432.0. These are an unvalidated successor suggestion: exacthalo plus matched input/readpin reach is stillrequired, especially the lowestpad. If necessary, an existing one of3pad edges may be used as a capture followed by2SRAM edges, preserving3total; no RTL change is authorized by this report alone. Central4SRAM matchedread/source bounds remain valid independently of pad qualification, but adding pads in those proposed positions mustbe rechecked against source-register regions.
