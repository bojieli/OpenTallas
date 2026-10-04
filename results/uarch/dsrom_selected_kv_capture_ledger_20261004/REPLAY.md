# Selected S81 KV/return-capture ledger

Selected source 55e2f0c09d18df83aff8781700ed4bf36e871ff2, Claude decision S81 / 2417 active pairs / BF519 / 368 total dies / RD64 ragged nodes. Every TP rank carries the indexer projection copies. No stage sweep or RD16 candidate. Input snapshots and SHA256 origins are in inputs/origins.json.

```sh
python3 -m pytest -q tests/test_dsrom_selected_kv_capture_ledger.py
python3 tools/dsrom_selected_kv_capture_ledger.py --out /tmp/fresh-S81-ledger.json
python3 tools/dsrom_selected_kv_capture_ledger.py --actual-capacity /absolute/Nash-Claude-S81-capacity.json --out /tmp/fresh-S81-capacity-ledger.json
```

Actual capacity manifest: selected_commit and selected_record_sha256 exactly match inputs/selected.json origins; source_files is a nonempty list of absolute path+sha256 records. rank_dies supplies all324 unique stage0..80/rank0..3 rows: die, stage, rank, stacks (1 or4), batch216, context1048576, integer state_bytes_per_user, other_live_bytes and usable_bytes_per_stack. No inherited uniform per-user state is substituted. Head allocation is separate, not inferred. Capacity pass never becomes physical or latency qualification.

Native node mapping is retained TT component area, with RD64/RST1/BYPASS1. Re-scale only its component count to4706; root logic is not mapped. 31.548mm2 is storage-only;76.921mm2 includes complete node logic plus root storage under FF50. The45.373mm2 difference is not an automatic new debit: Maxwell must reconcile the selected node/storage homes against existing named residual/fixed rectangle containment. Do not add both storage and complete-node reservations. No full-die impossibility or fit claim from this ledger.

Nash retained576-seat local capture uses128 independent69-bit writers and one scalar69-bit record drain per edge. Its2 historical phase stages are not the81 partition stages. Capture replication, selected2417 phase occupancy, consumer deadlines, mutable protection, actual bank macros and PG/clock/routing remain unbound. Stage field6bits needs an explicit local namespace binding or7bits if it names array stage0..80. No guessed capacity or silent truncation.

Maxwell owns selected die PDN/GRT and matching area containment; Claude owns partition/map/refit; Nash owns finite-capture source/count/consumer contract. All old inputs/failures are untouched; no RTL, build or P&R launched.
