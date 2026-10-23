# Shared-pointer FIFO tool dependency closure

The earlier standalone async_gray_fifo_constraints change (1d1b8d45d) called REVIEWED_FIFOS and fifo_base without shipping their async_fifo_hierarchy_audit implementation. That incomplete packet failed ROOT tests and was excluded. This bounded successor combines it with companion e709468fd and adds exact-name and causal reset-wiring regression tests. No RTL, physical view, clock budgets, or route records change.

The optional shared-pointer FIFO remains restricted to the coordinator-reviewed source SHA256 16f29b89797521bd683cd58735590492a09e5f49b18da1d04acced37e85a6819, exact Yosys source range, named reset synchronizers, same-domain group leaves, and actual per-slice async-reset wiring. Undeclared optional sources receive no grant. Original FIFO constraints retain their existing behavior.

Verification ran through unpinned ot-run on EP9, unit oth-ubuntu-2101446-1792730805, MEM4/threads2. Five relevant suites ran against both unchanged main and this candidate: 52 tests each, 50 passed and 2 skipped (no new failure). The added strict module-identity and group-reset causal tests ran on fleet unit oth-ubuntu-2084059-1792730627: 2 passed; five reset miswirings and one missing reset flop reject. Earlier harness attempts lacked sparse test support files and are preserved in scratch; they produced no design or tool verdict. Final logs are committed here. git diff --check passes.

ROOT must run its required complete helper checks, merge this complete packet, and sync the daemon before kshare r5a is submitted. This packet itself does not qualify a tile or alter any failed route evidence.
