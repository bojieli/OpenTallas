# RE-INDEX parent margin boundary (Claude takeover-ds, 2026-10-06)
- RTL: `rtl/dsrom_sys/reindex_parent/ot_dsrom_reindex_io_margin.sv` (default off; wrapped parent files unchanged).
  Inputs flopped at the pin, outputs from flops, 32 request streams and the drain output through full skid slices; +4,029 FF.
- Exact production gate (20 cases x 2 placements, Verilator 5.050, EPYC1), source da3e7736a:
  - `io_margin_off_gate/`: PASS, worst real_rank1_p2 739 cycles (identical to the pinned 739).
  - `io_margin_gate/`: PASS, worst 741 cycles (+2), backpressure PASS; negative control OT_REINDEX_MARGIN_SKID_MUTANT FAILS (kv stack 0).
  - `counter_split/`: tb_dsrom_reindex_counter_split PASS 514,048 checks; +mutant FAILS.
- Cost: +2 cycles on the 739-cycle gather (0.27%); 4 layers x 2 cycles = 6.7 ns per token.
- Route: EPYC1 /srv/opentallas-scratch/claude/takeover-ds/reindex/route_m1 (770 ps route, 833.333 ps SS/FF sign-off).
