# Peer queue bounded successor

Base a7b57f71f, opt-in SAFE_SRAM=1, default 0. Existing four credits, no added edge; this block preserves the existing exceptional peer credit protocol. No adoption or layout gate.

Two queues become two 32x546 p192 SRAM macros; effective capacity remains four each (528 and 512 used bits), allocated 34944 physical bits versus 4160 former queue flop bits. One synchronous read and one write per macro per edge, payload bandwidth 528/512 bits per edge. Read address is post-edge head; captured same-edge data handles SRAM read-before-write collisions. Three kept pointer/count source regions per queue feed at most twelve 16-bit bypass selectors. Captured bypass data is unconditional; payload and bypass have no reset. All controls/counts reset.

Consumption proof: any valid head follows an admitted write after reset. The first write into an empty queue collides with prefetched head and establishes captured bypass. Otherwise a preexisting head is in SRAM before the read, or simultaneous tail write/head advance collides and selects bypass. Unconsumed invalid payload is outside the valid-qualified interface contract. Reset drops both queue counts; no pre-reset payload is consumed. Fault and credit/control outputs must remain cycle-identical.

Remaining full-root families before native census: reset on 1544 payload bits, tx emit/choose mux controls, mailbox capture enable. These require separate <=16-bit control/source/reset partitioning; this queue step alone makes no native32 PASS claim. Pins/reset landing, final geometry/area/clock reach remain HOLD. No layout before complete mapped actual-Lib BUF/INV-effective census <=32, exactness and causal mutants.

Measured source 16c53cf70: Verilator5.050 PASS100000 samecycle; 22438 normal sends, 27960 peer receives, 18705 peer sends. Bypass and wrong-address causal mutants differ at edge5/7. All valid/control/credit/fault/drained outputs compare every edge; payload compares on valid. Resets every1024 edges, malformed frame and overcredit injections included. Initial undercoverage bench failure is retained; seed-once correction establishes real traffic diversity.

Mandatory mapped actual5-family SS Liberty+macroSS census **FAIL**, not a layout candidate: 10257 roots, five offenders, max1639. All 2187 named queue drivers <=32, including bypass32 loads for each16-bit selector. Complete remaining families:

| Net | Loads | Source family | Required next structural step |
|---|---:|---|---|
| rst_n |1639|1544 existing payload reset bits plus control/queue state|remove reset only from proven valid-qualified payload; kept reset leaves for control and pin reset landing|
| _07119_ / _09506_/Y |1045|emit hold/enable, from fault+physical+nn+peer_pending|enable-free tx payload launch and <=16-bit same-age control producers|
| _07140_ / _09541_/Y |1025|take_peer mailbox capture from fault+pending+peer_tx_valid|<=16-bit mailbox source capture controls with retained same-edge state|
| _04054_ / _10747_/Y |993|choose_peer mux from nn+peer_pending+rr|kept <=16-bit selector producers, not buffer copies|
| _04060_ / _10753_/Y |33|opposite-polarity choose_peer upper/tag path|same source partition, all-driver census must include both polarities|

No role errors, no constant functional output bits. Pin-registration/storage contracts remain separately unevaluated by census; direct source inspection confirms two real macros and unchanged four-entry capacity. Strict no-gate/no-submit/no-adoption HOLD until all remaining families, registered peer valid/data output boundary, reset landing, actual mapped area/geometry/reach and clock costs qualify. No native-cell behavioural model proof used: direct RTL miter only, so the HQN model-integrity warning does not invalidate the exactness evidence.
