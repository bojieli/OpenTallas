# DIE-KV-39-PVBAL: kv3_pv_pair quadrant-island clock balance (KV-012 'bal' variant)

Root cause (KV-KITS-T, CHECKED on 29f7719e90c0): the 4 plan quadrant islands mp_pv_ck_isl0..3 get independent
TritonCTS leaf trees; one gets an extra level -> inter-island skew -> GRT hold repair eats TT setup.

Fix: `island_balance.tcl` (sourced from the kit `post_cts_setup.tcl`, before the setup-only repair) measures each
island's mean register-sink insertion (TT, placement RC) and inserts dont_touch BUF delay cells on the branch input
(port -> chain -> mp_pv_ck_br<k>) of every faster quadrant up to the slowest quadrant's mean. The chain sits upstream
of br<k>, so island k flops and its planned SRAM chain mac<k>_* shift together. This is the tap_balance (KV-P6) form
applied to the quadrant roots; no data-path change.

Dry run on DIE-KV-38 m20 4_cts.odb (dry2_m20_4cts.txt): island means 232.95/260.59/248.82/285.68 ps
(spread 52.7) -> 280.41/285.91/293.62/285.50 (spread 13.2), 5 cells added. Live build: intel2
/srv/opentallas-scratch2/claude/die-kv-39-1029/pvpair/bal (copy of the m20 kit: setup margin 20 / hold 15).
