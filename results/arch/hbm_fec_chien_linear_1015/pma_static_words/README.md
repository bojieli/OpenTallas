# Separate fixed-word-slice PMA gearbox candidate

`ot_hbm_pma_block_gearbox_static_words` replaces the original full-bank variable
write/read selectors with actual fixed word slices, shared index predecodes and
a balanced read OR tree. Each 8,704-bit bank keeps its actual existing clock
port. It adds no FF state, clock, cycle or port and preserves the original
controller bytes except the q input wire. The source generator pins the exact
original and emits provenance. No existing frozen wrapper or live map is edited.

Four-state Icarus proof compares every original/candidate bank bit and controller
state after clock edges, all q/fault/valid outputs, and an independent expected
full-word stream. It exercises both 16×544→17×512 and reverse directions, repeated
four-bank wraps, five resets per direction (including mid-block), observed-valid
drop, repeated starts and an early-read alignment fault. The positive passes
6,946 edge/state checks and 2,353 independent golden full words in 20.36 seconds.
The drop test preserves the original behavior: missing observed-valid latches a
fault while the compiled transfer continues.

A separate actual Verilator run exercises every one of 8,704 single-bit block
input bases in each direction. It checks 287,232 basis output words, with 289,585
golden words and 581,551 edge/state checks including the protocol cases. Build
and simulation finish in 13.19 seconds; the native simulation uses 7.48 seconds.
This supplements the four-state check rather than replacing it.

Three actual mutants are rejected: the existing last-word MUT1 at output word17,
a wrong write-word predecode at the first write, and a real read-wire inversion
at the first read. Actual mutant sources/logs are retained. `protocol_v0/`
preserves the exact earlier bench/runner snapshots so every receipt hash can be
reproduced; the current bench adds the optional exhaustive basis mode.

All jobs used admitted ot-run scopes, listed in `reviewed_summary.json`, and
returned terminal runner exit 0. The comparison is source/state/calendar evidence,
not an unbounded formal proof. No full FEC/frame/native programme join, mapped
cell area, actual fanout/timing or physical fit is inherited. The original/current
151-edge profile, full 23-root map and existing TT mapper remain unchanged.
