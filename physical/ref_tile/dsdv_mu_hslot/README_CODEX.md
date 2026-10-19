HSLOT SRAM structural redesign

Position payload47x21 now uses ot_s81ph_mem1r1w SRAM1 WREG1. Return read remains registered; independent binary shadow indices track the existing one-hot start/return walks. User470b stays parallel for duplicate comparison; gap1128b remains for the two registered gap-prefetch reads. Remaining dense flop payload totals1598b, below2kb. Zero added schedule edges.

Verilator5.050 production47-user bench:282starts/282returns, all47users exact, max47outstanding, errs0.10-user bench:60starts/60returns, all10users exact. Collision fault asserted. MUT1(user dropped) and MUT2(collision check dropped) failed with committed run logs.

Safe-design checklist before gate:
1 PASS existing source pin registers, reset_landing2, SRAM write-port registers.
2 PASS outline259.2x129.6, no single wire can exceed405um.
3 PASS design uses kept payload copies <=16 entries and one-hot entry enables. New binary address shadows drive only the SRAM address registers. Synth fanout verification pending.
4 PASS SRAM read replaces registered one-hot position mux, other reads remain registered. Gate timing pending.
5 FIXED987b position table moved into SRAM; remaining associative/gap payload1598b.
6 Macro at43.2,43.2 on lattice;174.12x29.736 macro,10.8halo. Outline aspect2.0, full-width cell channels. Width is set by smallest existing1R1W macro and halo; spare array capacity makes aggregate fill lower than40%. Std estimate2400from HSLOT2 synth2312, conservative until synthesis. Density/PNG review pending gate.
7 PASS io_hold.03, reset2. Measured CTS spread pending.
8 PASS zero additional output edges, static calendar preserved.
