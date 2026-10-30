# HBM-004 re-plan estimate, variant R (DIE-HBM-27, 2026-10-29 ~21:10 PDT), plan d25b / d26a, bind d25b+g4

Labels: bit counts are from the d25b+g4 full-cap bind probe (`die-hbm-26/p_all`, 82,285 b) = CHECKED.
Face capacities (6 pins/um plan budget), cycles and tok/s are plan arithmetic = UNCHECKED. Numbers are per half;
NE is the MY mirror of NW (same widths, same lanes with suffix m).

## 1. Row geometry: why "su00/su20 get a direct hub face" cannot work by row reorder
The hub (8,216.6 x 4,320 um, x 5,140.8-13,357.4 in NW) has an S face and an N face of 8,216.6 um each.
The S and N rows are packed exactly (13,357.4 um each, no slack). spu1 (S, x 6,117-7,586) and spu0 (N, x 5,901-7,586)
are fixed by the spb/spt columns they feed. That splits each row into two exact-width groups:
* S: left {b102 708, b103 708, b111 804, su20 2,004, su21 1,892} = 6,117 um, hub face only 5,141-6,117 = 976 um;
  right {su30 2,065, b100 734, b110 415, su31 1,832, b101 726} = 5,772 um, all of it on the hub face.
* N: left {b113 1,858, su00 2,108, su01 1,935} = 5,901 um, hub face only 5,141-5,901 = 760 um;
  right {su10, su11, b112} = 5,772 um, all on the hub face.
Moves are permutations inside a group. Swapping su00<->su01 (or su20<->su21) only changes WHICH SU owns the
760/976-um face; the hub->su01/su21 traffic then has to cross the same face plus one more partition.
The 760-um face would carry hub<->su01 4,734 + hub<->su00 1,867 planned + 4,053 WIDEN = 10,654 b against a
4,562 cap = 2.3x. Verdict: **the su00/su20 part of V-RP does not fit; do not build it.**

WIDEN (+4,053 b per SU: hub->su 2,846 incl. pgp command 1,904 b at 101 sinks/bit, su->hub 1,207) through the spu ft
partitions instead:
| path | face | cap | used | +WIDEN | load |
|---|---|---|---|---|---|
| N: hub->spu0->su01->su00 | hub\|spu0 1,685 um | 10,110 | 4,848 (spt0 1,849 + L0 2,999) | 4,053 | 0.88 |
| | spu0\|su01 1,572 um | 9,435 | 2,999 (L0) | 4,053 | 0.75 |
| | su01\|su00 1,572 um | 9,435 | 4,880 (L162, L178) | 4,053 | 0.95 |
| S: hub->spu1->su21->su20 | hub\|spu1 1,469 um | 8,814 | 4,861 (spb2 1,849 + L2 2,999 + 13) | 4,053 | 1.01 |
| | su21\|su20 1,555 um | 9,331 | 6,081 (L163, L182, L38) | 4,053 | 1.09 |
All above the 0.6 corridor target; the S side is over 1.0, and the su01/su21 legs need ft stations inside
macro-heavy SU partitions (lane_add A/B: no macro-free station chain through su21). Verdict: WIDEN is not a lane
problem but a bit-count problem. Option to price at the source: the pgp command (1,904 b) is a broadcast; if it is
identical for the two SUs of a column, relay it su01->su00 / su21->su20 inside the SU pair (needs RTL owner
confirmation), which removes 1,904 b of the 2,846 from the hub face.

## 2. V-R1 (recommended build): permute the S-row right group
NW S row right group: today [su30][b100][b110][su31][b101]|root -> **[su30][su31][b110][b100][b101]|root**
(su30 and b101 stay; su31 x 10,800->9,651, b110 10,385->11,483, b100 9,651->11,897; NE mirror).
All five partitions keep their full width on the hub face, so every direct hub lane stays direct.
* Closes as adjacent (2-cycle boundary) lanes: SU3 su30->su31 3,356 + su31->su30 1,399 (face 1,555 um, 0.51) and
  scorer row 0 b100->b101 3,333 (face 1,555 um, 0.38 with L203 rerouted) = **8,088 b/half, 16,176 b die** of the
  40,547-b SPLIT class. Added cycles: 0 (both ends already pin registers in the bind view; NOTE the su30->su31
  bank_read_data sink is a $shiftx, i.e. this SU cut crossing is unregistered: adjacency is the best case, the cut
  itself must be timed by the SU kit).
* Existing lanes touched (NW; NE same): L5 hub->b110 14 cyc (now via su31 or b100, shorter, keep 14 by plan pad),
  L6 hub->b100 7 cyc 2,484 b (b100 face full with L7: split over b101 (room 2,376) + su31->b110 path; su31 hub face
  would reach 0.99 if it took all of L6, so split), L203 root->b100 12 cyc (now root->b101->b100, shorter),
  L34/L35 hub->su31->sm3 and L70/L100/L123 sm3<->b100<->hub (partners still above sm3), L48/L53/L117/L138 row
  chains (same length +-). No lane gets more cycles -> **tok/s change 0 (UNCHECKED)**.
* Right-group hub-span load after the move: 21,564 planned b over 34,632 cap = 0.62 (unchanged sum).
* G0/G0C risk (MEDIUM): 3 partitions move per half -> pin windows of every lane on su30/su31/b110/b100/b101 are
  regenerated (relay router), clock taps / in-core island coordinates of su31/b110/b100 move 1.1-2.2 mm on the
  H-tree lattice (12.2c: node displacement must be re-reported), street demand changes. Kit outlines and
  core_macros unchanged (soft partitions, positions only) -> pin-only re-kit of the 5 partitions per half.

## 3. Scorer contents fix (HBM-055, plan contents, carry into the same plan event)
RTL (ot_hbm_idx_score_quarter_static_h): 2 rows ge[0..1] x 4 chunk leaves gc[0..3] x 8 hcol cores, each row
W->E chained (q 568 + key 2,176 + aux 30 + sum bus 552 = 3,326 b per hop), each row ends in its own E glue + tail
u_t, then one 306-b score register -> xq_N (root).
The plan contents are a sequential fill: b101 = r0c2, r0c3 + **r1c0_k0h0** (17), b102 = r1c0 (7) + r1c1 + r1c2_k0h0,
b103 = rest of r1c2, r1c3 + **tail0 + tail1** + both rows' E glue + the score register. Fix:
* move hard core u_hb_idx__s_Q_r1c0_k0h0 b101 -> b102 and u_hb_idx__s_Q_r1c2_k0h0 b102 -> b103 (whole gc leaves per
  partition): removes b102->b101 1,146 + b101->b102 35 (bind CHECKED per-bit list: 569 q_b + 544 key + 32 hid4 + 1);
* move row-0 E glue (ge[0].keep_pipe/md/u_t = u_hb_idx__s_Q_tail0, $procdff$71730 bus capture) + the score register
  ($procdff$71751/71756) b103 -> b101: removes b101->b103 569 and b103->root 297 (then on unused plan lane L64), adds
  the row-1 tail result b103->b101 (~73 b: v + 4 kv + 64 score + 4 fault, UNCHECKED).
Net per half: -2,047 b +~73 b. Slot check: b102 gets 16 hcol (balanced 16/16/16 + tails at b101/b103).
Remaining scorer far link after V-R1 + HBM-055: row-1 feed b100->b102 2,777 b (11.2 mm after V-R1, vs 8.9 mm today)
+ row-1 result ~73 b. These need hop chains (~28 stations, ~30 cycles) on the index path -> **tok/s UNCHECKED, needs
one token run** (IDX records carry it; DIE-HBM-10 priced IDX +17 cycles inside a +2.98 % total).

## 4. REMAP class re-checked (task 3): the 5 pairs are NOT map-only fixes
| pair | bits | as-built driver -> sink (CHECKED) | suggested lane | real fix |
|---|---|---|---|---|
| NW/NE b103->root | 297 | scorer score reg $procdff$71751 (b103) -> u_hb_idx__xq_N | L64/L64m b101->root (unused) | HBM-055 contents move (sec. 3); map-only would just move the far link to b103->b101 |
| NW/NE b111->hub | 410 | sfucore __cut_lane4..8 kv_wdata/waddr (b111) -> u_sfus_Q__q1 | L81/L81m b110->hub 161 ctl (unused) | width/signal mismatch (L81 is 161-b ctl); this is SFU SPLIT/NEW (b111 has no hub face) |
| root->NE_b000 | 180 | col_idx.prm -> hb_idx__s_SE input reg (NE_b000) | L80m root->NE_b101 171 (unused) | wrong family: NE lacks the mirror of L202 (root->NW_hub->NW_b000 180 b, 25 cyc); fix = add L202m in the plan event |
Unused plan lanes L64/L64m, L80/L80m, L124 and L81/L81m are leftovers: L64 becomes used by HBM-055; L80/L124 carry
the scorer prm (180 b) only if the NW/NE scorer input register moves to b101 (would retire L203, 12 cyc -> 2 cyc,
but adds a b101->b100 180-b hop, adjacent after V-R1); L81 has no as-built user.

## 5. WIDEN 19 pairs (task 4) by face
| pair (per half) | +bits | face | room | verdict |
|---|---|---|---|---|
| hub->su00 / su00->hub | 2,846 / 1,207 | via su01 760 um or spu0 chain | see sec. 1 | does not fit (0.95-2.3) |
| hub->su20 / su20->hub | 2,846 / 1,207 | via su21 976 um or spu1 chain | see sec. 1 | does not fit (1.01-1.6) |
| NW_hub->root | 2,065 | hub\|root 4,320 um, cap 25,920, used 20,240 | 5,680 | fits alone (0.86) |
| NE_hub<->NW_hub | 2,775 + 2,730 | via root: NE_hub\|root used 12,085 + NW_hub\|root | 13,835 / 3,615 | NE side fits; NW side 1.07x with NW_hub->root -> fits only if NW_hub->root goes first and hub<->hub uses 3,615 of 5,505 (rest needs the vsN street) |
| sm0..3->hub | 37 each | sm faces | large | fits (type shared by 4 SMs -> lane_add refused: needs a shared-type lane, all 4 SMs at once) |
WIDEN closable by lanes: NW_hub->root 2,065 + sm*->hub 8 x 37 + part of hub<->hub = ~7.9-9.8k of 24,078 b.

## 6. SFU (b110-b113) contiguity: not possible by permutation
b113 (ctl, N row left group) talks to b110/b111/b112 (1.5-1.7k b each way) and hub/SUs. b112 (N right group) and
b113 (N left group) cannot be neighbours without an exact-width swap (no partition pair has matching widths), and
b110/b111 are in the S row behind the 4,320-um hub. Options for a later event: re-outline b112/b113 (soft) to
swap with an equal-width slot, or move the SFU ctl (sfucore Q_ctl/opstore_a) next to the hub. Not estimated here.

## Recommendation
Build V-R1 (S-row permutation) + HBM-055 (scorer contents) + L202m (NE scorer prm lane) + d26a core_macros as ONE
plan event, then G0/G0C, strict bind. Expected bind: 92 -> ~79 pairs (-6 V-R1, -8+2 HBM-055, -1 L202m), 82,285 -> ~62.0k b (-16,176 V-R1, -4,094
HBM-055, -180 L202m, +146 tail result) (UNCHECKED until bind). tok/s 0 for V-R1; scorer row-1 far link needs a
token run before it is laned. WIDEN su00/su20: ask the RTL owner whether the pgp command is a shared broadcast.
