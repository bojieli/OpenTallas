# q_b001 / q_b001__physical_v1 cell cut: per-bit pad landing spec (option (a), for KW-FIX-45)

DIE-LAYOUT-HBM 11-12. Paper spec, no plan delta. Base: d53b (ad080c302a2b) + tapsplit-d55.
Option B (a plan-level shift of pad cycles across the q_b001|q_b002 seam) cannot be expressed in the plan:
`internal_stations` rows carry {launch, capture, bits, regs_um} but no bus-bit indices, so the only movable quantity is a
uniform K per bus. K = min over rows of (regs - reach_need) = 0 for L71_i and -1/0 for L15_o. The cut must come
from kit_istations, which has the per-bit nets.

## Per-row data
`pad_rows_d53b.tsv`: one line per internal row of buses L14_i, L15_o, L71_i (q_b001, pv1) and L15_i, L71_o (q_b002, pv1).
surplus = regs - ceil(Manhattan(from, to) / 360) + 1, i.e. registers on the row beyond its own 360-um reach need.

| type | bus | surplus flops |
|---|---|---|
| q_b001 | L14_i (from q_b000) | 28,647 |
| q_b001 | L15_o (to q_b002) | 5,142 |
| q_b001 | L71_i (from q_b002) | 5,836 |
| pv1 | L14_i | 30,076 |
| pv1 | L15_o | 5,654 |
| pv1 | L71_i | 5,302 |
| q_b002 | L15_i (receive side of L15) | 8,192 (already) |
| q_b002pv1 | L15_i | 7,174 (already) |

## Landing rules
1. Cycle preservation per bus bit: for every bit b of a lane, the register count on its full path (source-type row +
   destination-type row) stays exactly as today. A register removed from a q_b001 row is added on the same bit's
   path in the neighbour type. No lane latency, no `fixed_cycles`, no LAT_* change.
2. Reach: every register-to-register step stays <= 360 um (405 hard) on both sides after the move. A row never drops below
   its reach need (column reach_need).
3. **L71 (q_b002 -> q_b001, 274 bus bits fanned out to 7 bank pairs; row bits 3,675): hoist before the fanout.**
   For bus bit b with fan-out set F(b) (the q_b001 rows that bit feeds), h(b) = min over r in F(b) of surplus_r.
   Remove h(b) registers from every row in F(b) and land h(b) registers on the single pre-fanout net in q_b002,
   as face pad stages behind the L71_o window (E face, local y 922-968; pv1 871-917).
   Net cut in q_b001 = sum_b h(b) * |F(b)|, receiver gain = sum_b h(b). Upper bound about 5.8k flops cut for
   at most about 548 added (h <= 2 = lane fixed_cycles).
4. **L15 (q_b001 -> q_b002, 4,128 bits, no fanout): move source-side surplus across the seam.**
   For bit b, s(b) = surplus of its q_b001 L15_o row. Land s(b) registers on the same bit in q_b002 L15_i,
   as face pad stages inside the E-face window (local y 1004-1692; pv1 922-1610), before the bit's own capture row.
   Cut = sum_b s(b), about 5.1k (pv1 5.7k); q_b002 gains the same.
5. Bit order across the seam: the L15_o / L15_i pins are one face pair with the same bit order (lsb order in the
   pins table). The move is per bit index, so the face-pad landing in q_b002 keeps the existing per-bit row mapping
   (bit -> capture pair). Do not re-group bits by pair across the seam. For L71 the hoisted stage sits before the fanout
   on bus bit b, so all 7 pairs see the same added latency.
6. L14 (from q_b000) is not moved: q_b000 has no room (HBM-VSN-XTAP-2 / plan estimate).

## Expected numbers (to be measured by the kit)
q_b001 about -11k pad flops (about -17k cells at about 1.6 cells per flop: a rough two-point fit). HBM-VSN-XTAP-2:
with -11k cells q_b001 is still 400,838 > 400k, so about 6k more cells are needed beyond this (or fallback (c), the cap).
q_b002: 216,180 base + 12,303 latches + about 5.7k flops (about 9k cells) = about 237k, far under 350k.
The L15/L71 hops are boundary pad cycles, not counted station hops (HBM-VSN-XTAP-2); the seam crossing stays
in the parent's io_hold_parent class.
