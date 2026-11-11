# Intent sheet: SU-CHAN core moves (hbm-channels-1111, section A)

This sheet follows the COORD INTENT RULE. It covers the `origin_um` moves of the 24 hard cores in each of q_su11, q_su11__physical_v1, q_su01 and q_su01__physical_v1, on base plan_p11t_taps_cyc 29333b2b.

The outlines, buses, faces and windows of these four types do not change. Only `origin_um` moves.

The SVGs are in this directory: `q_su11.svg`, `q_su11__physical_v1.svg`, `q_su01.svg`, `q_su01__physical_v1.svg`. Filled shapes show the new positions and grey dashed shapes show the base. Arrows show dataflow. The machine-readable checks are in `intent_su_chan.json`, produced by `intent_sheet.py BASE EVENT CORE_CONNS OUT`.

## Intent

The base packed the 3x2 exp-lane block and the two plain-lane stacks into one cluster. That left no street for the pass-through ft chains, which are the hub->SM lanes L8301m/L8302/L8314 in q_su11, and L3008/L8007/L8008 in q_su01. It also left no street for the internal-station chains (L5090/L5091) that run from the leaf cores to the S face.

The move opens two N-S streets and one E-W street. Each one is wide enough for a station chain at hop <= 405 um. Every core keeps its row, its column order and its abutted partner.

## Dataflow chain and link roles

The chain runs: in buses at the face, to the 24 cores, to the out buses. The pass-through slots cross the type without touching its cores.

| Link | Role | Endpoints | Treatment |
|---|---|---|---|
| Hub/command in buses: q_su01 S L1214/L1269/L1270/L3004; q_su11 E L5015-L5017, S L5018/L5026/L5039, W L5048_i | broadcast | face -> all lanes | Unchanged (same face and window) |
| exp lane `__l` -> `__s` (sx_*, ci_sfu, y_div, y_exp, fault, v), 48 refs each way per type | point-to-point, same lane | `lane_expN__l` <-> `lane_expN__s` | Kept abutted: gap 0 -> 0 on all 8 pairs. The pair moves as one unit |
| Plain stack p0 -> p1 -> p2 -> p3 (bank0_read_addr/v, lane0_*), 1080 refs | point-to-point chain (serialisable) | `lanes_plain4_7__p*`, `lanes_plain12_15__p*` | Column and order kept, abutted stack moved as one unit |
| Out buses to hub: q_su01 E L1208-L1210, S L1211-L1213/L1271; q_su11 S L5019/L5027/L5040/L5098_o | point-to-point | lanes -> face | Unchanged |
| q_su01__physical_v1 internal-station buses L5090/91/93/94/95/96/99/L5100_o (bank_read_data -> NE_hub q_hub_ne) | point-to-point, registered | leaf -> stations -> S face | Stations re-derived (b2n rule, hops <= 405). L5090 3->5 and L5091 3->4 stations; others keep their count |
| ft slots: q_su11 L8301mx1/L8302mx1/L8314mx1 (S->N, hub->SM 1615/1615/15 b), L8306mx1, L8310mx1, L7504x5; q_su01 L3008x2, L8007x1, L8008x7 | pass-through | in face -> out face | Chains routed through the new streets. +1 station on L8301m/L8302/L8302m/L8314/L8314m |

## Timing-critical pairs

1. **exp `__l` <-> `__s` same lane.** This is the widest core-core point-to-point link. Each pair stays abutted (gap 0), so the move does not lengthen it.
2. **Plain stack p_i -> p_i+1.** The stack stays abutted in the same column.
3. **Internal-station chains L5090/L5091.** These carry bank_read_data to the hub. They are now registered at hop <= 405 um. The extra cycles are +2/+1, priced by HBM-TAPS at +0 under the max-leg rule; L1271 at 66 stays the slowest SU->hub leg.
4. **Hub->SM ft chains L830x/L8314.** These run at hop <= 405 um with +1 station each. Each extra stage is proved equal to the base link delayed +k: see `eq/eq_stations.json`, verdict ALL_EQ_CYCLE_SHIFTED.

## The moves (uniform lattice shifts)

| Type | x shift by column (um) | y shift by row (um) |
|---|---|---|
| q_su11 | -233.28 / -77.76 / -8.64 | -43.20 / -34.56 |
| q_su11__physical_v1 | -233.28 / -77.76 / -8.64 | -17.28 |
| q_su01, q_su01__physical_v1 | 0 / +112.32 / +224.64 | -103.68 / -86.40 / -60.48 / -34.56 |

Every value is a multiple of the 8.64 um site/row lattice.

The checks in `intent_su_chan.json` give the following on all 4 types:

| Check | Result |
|---|---|
| `row_membership_kept` | True |
| `left_to_right_order_kept` | True |
| exp l/s gap | 0 -> 0 |

## Search statement

The core positions were not searched. They are the base positions plus one shift per column and one per row, chosen to open the streets.

Search was used only to legalise station sites. `mk_chan_event.py` `slot_candidates` and `slot_ok` place ft and internal-station regs at free points so that every hop is <= 405 um, which is the reach rule. The station count is the generator-rule count, and each added station is covered by the stage-equivalence proof.
