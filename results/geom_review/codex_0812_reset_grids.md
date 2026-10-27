# Independent RESET/START terminal grids for KV FT corridors

Plan-form review PASS; these are proposed reset/start consumer relay sites, not route permission. Existing io_cor/hroot structural data-reach failures remain open. No clock pin, RTL, plan or kit was edited in this review.

Read-only actual b53 placed ODBs are recorded in the JSON. Both have no hard macros. Every existing CLOCK BTerm is centred at y=21.6 um; these intentional bottom band-mesh entries are preserved. Independent RESET/START grids use 345.6-um pitch, snapped exactly to4.32um and fully interior. Neighbour grid hops are345.6um. The global Manhattan covering bound over each whole outline is345.6um, below the380um requested margin, so any synchronous-reset/epoch sink anywhere in the outline is covered even after replacement.

- kv3_io_cor: 1278.72x1036.8um,4x3=12points; all13,422 actualDFF centres have max nearest340.821um. Minimum edge inset120.96um.
- kv3_hroot: 1900.8x838.08um,6x3=18points; all9,003 actualDFF centres have max nearest337.959um. Minimum edge inset73.44um.

The two reset_grid.png figures were rendered from the actual FF centres and viewed directly. Coverage cells span full height while clock pins remain on the bottom band. Sites occupy the open FT corridor rather than moving clock entries; there is no macro wall. This deliberately covers ALL FFs, a conservative superset of control/reset/epoch consumers; future implementation may ignore unused taps while preserving the relay connectivity and max hop. Relay reservation, fanout buffering, deterministic reset/start depth and cycle accounting are the reset-tree implementation's job. New source/plan fields are owned by COVERAGE/QK, outside this review.

Per-type reset.local_taps_um arrays and measured worst sinks are in codex_0812_io_cor_reset_grid.json and codex_0812_hroot_reset_grid.json; codex_0812_reset_grids.json combines them.
