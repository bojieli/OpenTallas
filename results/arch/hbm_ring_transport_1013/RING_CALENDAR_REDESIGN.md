# HBM B2 slice ring: calendar redesign proposal (2026-10-13, Claude ring-station-1013)

Status: PROPOSAL with a first-order model run. Nothing here is a qualification, nothing is re-priced, and no budget is
raised. Numbers: `calendar_sweep.json` (this directory, tool `tools/hbm_ring_calendar_sweep.py`), `calendar_budget.json`,
`station_column_cut.json`, `results/arch/hbm_native_ring_cut_1013/STUDY.md`.

## 1. The problem in three numbers

| | cycles a hop | against the 12 / 11 price |
|---|---:|---:|
| SPEC 5 price (assumed about 9 relay stages, <= 5 mm) | 11-12 | 1.0x |
| Physical floor: 20.0-33.5 mm corridor at 504 um a stage, plain flops | 40-67 (+3 face / arbitration = 44-70) | 3.7-5.8x |
| Measured D8 elastic station on every segment (4 edges a segment) | 168-272 | 14-22.7x |

The price cannot be met by any transport: the four VM slices sit at the quadrant centres of die_v12 (16.5 mm apart in x,
13.0 mm in y), so even a straight wire between nearest neighbours is >= 26-33 stages. The SID order SW0 SE1 NW2 NE3
additionally puts BOTH diagonals on the ring (59-60 and 67 segments).

## 2. End-to-end effect from the existing calendar model

`tools/hgi_e2e/b2.py` (SPEC 5.0 exposure: arrival-after-need on the compiler's s2 schedule) re-run on the current B2
compiler vectors (v8: Qwen L0 P8191; DS L2 / L14 / L20 / L24) with per-edge ring latency. Exposed cycles a layer; loss
is against the same vectors at the price (DS 14,139 and Qwen 35,253 cycles a layer; stalls are not propagated).

| scenario | ring edges (cycles) | DS exposed mean / worst (budget 290) | DS tok/s loss | Qwen exposed (budget 93) | Qwen loss |
|---|---|---:|---:|---:|---:|
| price (control) | 11/12/11/12 | 153 / 279 | 0 | 14 | 0 |
| elastic station every segment | 168/244/172/272 | 3,592 / 3,890 | **19.4 %** | 792 | 2.16 % |
| one elastic per 8 plain stages | 68/95/69/106 | 1,058 / 1,210 | 5.96 % | 294 | 0.79 % |
| plain stages, SID order | 44/63/45/70 | 610 / 756 | 3.10 % | 182 | 0.47 % |
| plain stages, geometric order (vertical edges ESTIMATED 32 segments) | 44/35/45/35 | 398 / 533 | 1.69 % | 126 | 0.32 % |
| plain SID + COLL star at wire length (33, ESTIMATE) | same, star 33 | 915 / 1,121 | 5.06 % | 238 | 0.63 % |
| plain geometric + COLL star at wire length | same, star 33 | 703 / 899 | 3.71 % | 182 | 0.47 % |
| ring at price, star at wire length (isolates the star) | 11/12/11/12, star 33 | 458 / 644 | 2.09 % | 70 | 0.16 % |

Readings:
- No physically possible row stays inside the unchanged exposure budgets (290 / 93). The best physical row is 1.4x (DS
  mean) and 1.35x (Qwen) of budget.
- The per-segment elastic station costs about 19 % of DS tok/s. It cannot be accepted under the owner rule (<= 5 % a
  unit) and should not be routed as the transport.
- Plain registered stages cost 3.1 % (DS) / 0.5 % (Qwen) in the SID order and 1.7 % / 0.3 % in a geometric order: inside
  the owner's accepted-cost rule IF confirmed by a measured end-to-end run.
- The COLL broadcast star is priced at 12 cycles as well and has the same physics (hub to slice is about 15 mm): about
  2 % of DS tok/s on its own. Ring + star in the SID order is 5.06 %, above the 5 % line; in the geometric order 3.7 %.
  The star length is an estimate and needs its own corridor study.

## 3. Proposed transport (structural)

1. **Plain registered stages, not elastic stations, between endpoints.** `ot_vms_relay` (one flop forward, one flop
   credit back, <= 500 um): 2,226 flops a stage against 43,999 for the elastic station. Over the 210 segments x 2
   directions that is 0.93 M flops (about 0.27 mm2 of cells) instead of 18.5 M flops (11.7 mm2 of cells). It also removes
   the station-column cut problem (6,678 link signals over each 410 um station body, M7 cut 1.04).
2. **End-to-end credit, storage only at the receiving ring stop.** Full rate needs credits >= round trip: 2 x S + 4 =
   86-138 entries a VC (SPEC line 206 rule). At 2,224 b that is 191-307 kb a VC, 2 VCs an input: a memory-macro FIFO in
   the regional endpoint (D8 flop storage cannot hold it). The native D3 ring stop gives 0.50 flit / cycle and stays a
   separate, unqualified limit. Alternative that needs no storage: slot-reserved (calendar) transfers, because the
   compiler already schedules every push; that changes the ring-stop contract (no arbitration loss, no VC credit).
3. **Geometric slice order (SW, SE, NE, NW) on the ring.** Removes both diagonals: worst edge 67 -> about 42 segments,
   ring perimeter 210 -> about 147 segments. A relabel of slice ids in the compiler slice map and the die netlist; no
   child moves. Vertical-edge polylines must be measured by the cut study.
4. **Compiler lead.** Exposure is `H + 1/b - lead/c`; a push dispatched >= H cycles before its first reader, or a
   reader that has >= 64 x H local words first, exposes nothing. The dominant exposed ops are FUSED.HC_PRE_NORM,
   COLL.ALL_GATHER, COLL.GROUP_REDUCE_MCAST (DS) and COLL.ALL_REDUCE_SUM (Qwen): the compiler should schedule these
   pushes early with the per-edge H in its cost table. UNMEASURED: needs a compiler run.
5. **Not recommended:** express / chord links (they add a second 4,452-signal corridor across cuts already at 0.55 and
   only replace two ring hops by one diagonal of the same wire length); moving the ring stops to the die centre (hop
   <= 5 mm restores 12 cycles on the ring but moves the same 13-16 mm into every slice's local lanes, which are on
   the serial path of every record, not only the remote ones).

## 4. What stays inside the unchanged budgets, and what needs a decision

| item | inside unchanged budget? | who decides |
|---|---|---|
| Replace elastic stations by plain stages + endpoint storage | cuts the miss from 12.4x to 2.1x of the DS budget; still over | stream (structural default) |
| Geometric slice order | reduces to 1.4x; still over | die lead + compiler lead (slice map relabel) |
| Compiler lead for the five exposed ops | could reach the budget; unmeasured | compiler lead; then no owner decision is needed |
| Residual after 1-4 | DS about 1.7-3.7 %, Qwen about 0.3-0.5 % (model) | OWNER: accepted-cost ledger row; needs the MEASURED run below, unit ratio 3.7-5.8x |
| COLL star at wire length | not priced today | die lead: corridor study; same ledger rule |

The ledger row may only be written from a measured end-to-end run: `tools/comp_regress` B2 harness (`tb_hgi_e2e`
B2 = 1 + B2_RING, ring cycles added to the record hold times) with the per-edge latencies of the chosen row, on the Qwen
and DS vehicles. This model run is the estimate that says the measurement is worth making; it is not that measurement.

## 5. Consequence for the elastic station tile (vms_elastic_ls16_cx)

Its physical gate is still worth finishing as evidence for a D8 regional ENDPOINT buffer slice (the same storage
structure), but it should not be replicated 420 times along the corridor. The route job for a per-segment station is
therefore not the next step even at a 0-fail gate, unless the owner rejects this proposal.
