# Peer queue bounded successor

Base a7b57f71f, opt-in SAFE_SRAM=1, default 0. Existing four credits, no added edge; this block preserves the existing exceptional peer credit protocol. No adoption or layout gate.

Two queues become two 32x546 p192 SRAM macros; effective capacity remains four each (528 and 512 used bits), allocated 34944 physical bits versus 4160 former queue flop bits. One synchronous read and one write per macro per edge, payload bandwidth 528/512 bits per edge. Read address is post-edge head; captured same-edge data handles SRAM read-before-write collisions. Three kept pointer/count source regions per queue feed at most twelve 16-bit bypass selectors. Captured bypass data is unconditional; payload and bypass have no reset. All controls/counts reset.

Consumption proof: any valid head follows an admitted write after reset. The first write into an empty queue collides with prefetched head and establishes captured bypass. Otherwise a preexisting head is in SRAM before the read, or simultaneous tail write/head advance collides and selects bypass. Unconsumed invalid payload is outside the valid-qualified interface contract. Reset drops both queue counts; no pre-reset payload is consumed. Fault and credit/control outputs must remain cycle-identical.

Remaining full-root families before native census: reset on 1544 payload bits, tx emit/choose mux controls, mailbox capture enable. These require separate <=16-bit control/source/reset partitioning; this queue step alone makes no native32 PASS claim. Pins/reset landing, final geometry/area/clock reach remain HOLD. No layout before complete mapped actual-Lib BUF/INV-effective census <=32, exactness and causal mutants.
