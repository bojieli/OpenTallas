`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVCX4 (2026-10-17): dsdv_svc_sx_hrow, the CENTRE LEAF of the split score exchange = HALF a score row.  The slice
// (dsdv_svc_sx) instantiates it 8x (4 rows x 2 halves), hardened once; the strap hb picks the half.
//
// Why: the full-row leaf (S81U-SVCX, 14.4k sinks on a 389 um pin ring) measured TT 326..415 ps insertion / 89 ps spread
// at its best CTS setting (gate 3), over the 300 / 80 clock rule.  Halving it gives ~7.3k sinks on a ~238 um ring.
//
// The halves are HEAD PARITY classes: half hb owns heads h = 2 i + hb (i = 0..7) of its row.  A score beat never mixes
// heads in the gather (the node adds lane (r, h) of a to lane (r, h) of b), so the gather splits with no crossing.  The
// scatter moves head SLOTS: a node over heads lo..hi sends lo..mid to the left child and mid + 1..hi to the right child
// shifted down by the left half's size (8, 4, 2, 1).  Shifts by 8, 4 and 2 keep slot parity (local shift 4, 2, 1 inside
// a half); only the pair nodes' shift by 1 would cross halves.  So the pair node does NOT shift: its right child gets
// the lane as is, head 2k + 1 at slot 1 = local slot 0 of half 1, and the leaf of head t taps local slot 0 of half t[0]
// (role head bit 0).  The other half's tap register holds 0 (valid low), so the slice ORs the two halves' 39-b tap
// (the same kind of output glue as its row valid AND / fault OR).  Nothing crosses halves; zero added cycles; the 5-cycle
// hop and the role ROM offsets are unchanged (the scatter lane's slot encoding below a pair node is internal to the
// exchange: only the gather beat at the root and the taps leave it).
// Lanes (per half): gather {v, tag part 5, y 8 x FP32, flags 8} = 270 b = ONE dsfd_dvrly_276 station; scatter
// {v, tag part 5, 4 slots x {flag, y}} = 138 b, the two halves of a row share one 276-b station.  Every pin registered.
// Static schedule (no ready / credit); sticky fault on operand misalignment, tag-part mismatch or a stray valid.
// MUT: bit 0 = right operand's flags not ORed; bit 1 = right scatter split off by one (local) head slot.
// S81-KITS-HROW (2026-10-24): every role-driven mux select is a registered, replicated one-hot (see below); 0 cycles.
// ---------------------------------------------------------------------------------------------------------------------
/* dsdv_svc_sx_hrow: hard macro, header-only view in dsdv_svc_sx_hrow_bb.v (gen_phys) */
