# Scenario C W3 replay

MODEL ONLY. Source base 805cc0c6af2c0ff647cca21e819c4cd85c77a257.
Scenario snapshots are exact git blobs from 3a0c114d8; originals remain untouched.

```sh
python3 -m pytest -q tests/test_dsrom_c_w3_kv_shoreline.py
python3 tools/dsrom_c_w3_kv_shoreline.py --out /tmp/w3-provisional-fresh.json
python3 tools/dsrom_c_w3_kv_shoreline.py --w2-map /absolute/W2-map.json --out /tmp/w3-W2-joined-fresh.json
```

No P&R executable or launch path is provided. No adopted stack, rate, area, power or die reduction.

W2 map schema: DSROM_C_W2_W3_MAP_V1, kind actual_W2_map, full source_commit,
nonempty source_files [{path:absolute, sha256}], stages, ranks_per_stage=4,
rank_dies covering all (stage,rank), and eight head_dies. Each rank die has
unique die, stage, rank, layers (complete layer 0..42 / rank 0..3 ownership),
controller_pseudochannels_per_stack, and contexts 1048576 and 200000.
Each context supplies batch=216, state_bytes_per_user, non_state_reserve_bytes,
non_HBM_stage_us, controller_service_us and transfers [{kind,
bytes_per_stage_service, fixed_latency_us}]. Required traffic: window_KV and
row_gather on rank dies, index_scan on scanning dies, head_state on head dies.
head_bound_us supplies both contexts. Traffic and timing must refer to the same
batch-216 service window; synthetic test data is not an actual W2 enrollment.

Rank stages operate in parallel; within a rank die fixed latency and transfer
times are added conservatively, plus controller and non-HBM service.
The one-stack latency-dominated test compares transfer time to fixed latency.
This is a source-model comparison, not a measured occupancy or cycle claim.

The actual-map join recomputes scanning dies from layer ownership; it does not
force 32 scanning dies or 420 stacks if W2 co-locates layers. All map joins remain
unadopted, and PHY savings remain held for Maxwell W4's explicit debit/rectangle
union. S73 is provisional; no S68/S69 stage credit is applied.

Input SHA256 pins:

- `configs/hardware/technology.json`: `17bcb8af6dffcbbe1817c60600b4b6961a06a6c58a773f9e1eaba88741b36706`
- `results/uarch/dsrom_c_w3_kv_shoreline_20261003/inputs/scenario_c.json`: `8ca0294417dd8975b89861e8e5a01c1f4832bba11349db2fe1dc41d022d5eb42`
- `results/uarch/dsrom_c_w3_kv_shoreline_20261003/inputs/scenario_c_producer.py.snapshot`: `0c08f285b3898d0d499385cffeb1131c9cbfe6f48a265cf049692323a0d89d44`
