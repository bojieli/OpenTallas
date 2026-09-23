# Maximum tree over precomputed sortable keys

The isolated candidate converts each score to its sortable binary32 key once at
the tree leaves. Interior nodes compare and select keys; the root decodes the
winner. This removes repeated sign/zero conversion from each comparison level.
No state or cycles are added. Valid-lane masking and left-child tie preference
remain unchanged. Both signed zeros become +0 at root decode, earlier than the
baseline's existing public-output canonicalization; raw internal `max_scan`
signed-zero identity is intentionally not an equivalence claim. Nonfinite
admission remains unchanged and rejects before consuming that maximum.

The candidate retains baseline historical comments in its snapshot; the changed
representation is described here and at the decode. It is not production RTL.

Validation uses `tests/test_softmax_lane_write.py`: baseline/candidate sources,
Icarus/Verilator, lane counts 1/3/64/65, 256 random maximum patterns (including
nonfinite raw codes and signed-zero ties) and 24 cycle-by-cycle controller
transactions per case. The controller test uses a fault-controlled exponential
stub. The real `tb_a3_softmax_block` numerical corpus separately checks nine
cases and two refusals with the actual exponential engine; its log is retained.

Synthesis comparisons use identical current exponential and arithmetic sources,
changing only the softmax tree. The pending physical record names are
`key_tree_synth_sta_1ns.json` and `key_tree_baseline_synth_sta_1ns.json` beneath
`results/physical_abi3/asap7/a3_attention_softmax_block`. An improvement here would
still need routed qualification before a high-clock claim.
