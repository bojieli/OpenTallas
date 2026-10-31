# HBM die IO-hold table (IO-HOLD A sender_min parent obligations; owner = HBM die owner, DIE-HBM-47 onward)

Each row: a core input bus that does NOT pad its own input hold (kit under OT_IO_HOLD / plan clock.io_hold = sender_min,
io_hold_qualification.py); the parent (die) proves FF seam hold >= 0 with real propagated trees, 25 ps unc, CPPR to the last
common node (tools/die_plan/io_hold_parent.py over die_sta, TT+FF). A row is CLOSED only on that parent receipt on the
routed HBM die clock. Parent remedy if it fails: data hold buffers in the partition glue at the sender station (allowed,
METHODOLOGY v4.6), never in-core padding and never a clock ECO.

| since | core module | instances (d44f) | ports (bits) | sender (plan d44f, glue station) | status |
|---|---|---|---|---|---|
| 2026-10-31 01:10 PDT (COORD 01:03 option A, HBM-CORES-KITS-31 00:56) | ot_hbm_idx_query_static | q_hub_nw + q_hub_ne: u_hb_idx__q_Q__q0 (origin 3663.36,241.92 / 3758.4,241.92), u_hb_idx__q_Q__q1 (5356.8,734.4 / 5633.28,734.4) | block_data (1024 core port; q0 chain 1024 b, q1 chain 512 b), head_weight (16; q1 chain 8 b) | last station of conn u_hb_idx__op_Q.block_data/head_weight -> u_hb_idx__q_Q: q_hub_nw q0 reg (3840.48, 349.92) ~6 um E of the core, q1 reg (5533.92, 842.4) b-d / (5650.56, 669.6) hw; registered glue flops, same partition | OPEN: needs die_sta FF on the routed HBM die clock (HBM-CLKLOC-1) + io_hold_parent receipt. Other 18 port endpoints + rst_n removal stay in-core (kit). Risk: hub regions T028/T029 have the tightest clock budget (CLKLOC estimate 22 ps) -> glue hold buffers at the 1024-b station are the planned remedy if FF seam hold < 0. |
