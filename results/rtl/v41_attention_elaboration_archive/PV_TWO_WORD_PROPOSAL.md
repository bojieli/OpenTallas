# PV probability bandwidth proposal — architecture approval required

## Current problem

H16/D512/TD32/NL4 has64 tiles, each with8 output dimensions. A32-row
probability block requires16 existing512-bit words, but its PV compute takes
8 issue cycles. The single-word stationary-bank loader caps sustained issue
utilization at50%, independent of KV fill improvements.

## Proposed minimal interface

* Parameter `PWORDS=2` (default1 retained) selects1024-bit `p_w`, still a
  single ready/valid handshake. Low512 bits contain the earlier existing word;
  high512 bits contain the next. Each existing word has2rows×16heads BF16.
* No new arithmetic: every per-head stationary row receives precisely the
  same BF16 bits, in the same chronological row index. Products and chunk8
  accumulation order are unchanged.
* Job row count determines tail validity: consume `min(2, words_remaining)`;
  unused high-word bits must not write any live row. No cross-block beat.
* Increment loader word index by accepted count. Start PV on acceptance of
  the final block load only when existing fill/credit conditions also hold.
* Tile load writes disjoint stationary rows in parallel. This is not two
  writes to the same scalar cell and must not silently infer a double-clock
  memory. SRAM lowering needs a bank/mask implementation with the same writes.
* Q loading remains one head/beat; the upper load word is ignored in Q mode.

## Bank requirement, proved separately

Use4 stationary banks forPWORDS2, not3. Existing3-bank mode remains unchanged.

For steady8cycle/block scheduling, load blockb at8b..8b+7 and issue it at
8b+7..8b+14. At the engine interface, stationary write reaches storage2edges
later; product operand capture is3edges plus the existing per-row skew later.
A same-edge nonblocking overwrite is safe because the product captures the
old value before the NBA update.

`tools/v41_pv_bank_lifetime.py` exhaustively enumerates row/lifetime events:

*3banks: minimum overwrite margin−8cycles; unsafe.
*4banks: minimum margin0; safe, including the boundary case.

The SV storage-semantic replay independently observes527 corrupted reads
with3banks and0with4banks, across5120 reads/640 writes. This is not numerical
attention verification, and assumes the controller realizes the stated event
schedule. It is a minimum-capacity proof for this particular schedule.

The load guard must change with grouping: `GUARD_P` becomes18 from16, using
`floor(group/PWORDS)` for load time. The existing countdown threshold becomes
3 rather than5. Keep this guard; merely changing bank count without it is not
safe.

## Costs and physical review

* Stationary bits:196608→262144 bytes (+65536B).
* Probability ingress512→1024 bits and corresponding tile-load boundary
  registers. No additional full-probability-stage buffer is included.
* Probability broadcast still reaches64 tiles. Root must budget regional
  registers/buffering, fanout and routes; no zero-cost doubled bandwidth.
* Upstream SU/VM must actually provide four rows/head percycle. A pair buffer
  fed at the old1word/cycle only improves bursts and cannot claim sustained
  acceleration. That producer is a separate contract that must be validated.
* Ideal160 PV issue beats over20full blocks could approach160issuecycles
  afterfill instead of312, but **no such RTL end-to-end result is claimed**.

## Required acceptance sequence

1. Root approves width/storage/physical/upstream-production budget.
2. Parameterized candidate, reduced default unchanged, isolated source.
3. Tile flat numerical equivalence for all64head/lane write coordinates,
   every bank, partial last words and Q/P mode switches.
4. Full-engine numericflat/hier compilation control and exact tests.
5. Actual window source + SU probabilities + numeric engine composition,
   bounded queues, stalls, first/last timings.
6. Physical region with doubled ingress and added bank, then performance
   model update using achieved timing. No rate model gain before these gates.
