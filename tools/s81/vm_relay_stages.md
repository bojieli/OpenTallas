The MTP ledger can consume the selected S81 die's relay-stage table:

```sh
python3 tools/s81/mtp_ledger_1016.py \
  --relay-stages SELECTED/relay_stages.json --vm-paths ACTUAL_VM_PATHS.json \
  --stages ALLOCATOR_STAGE_COUNT --compiled-out COMPILED/relay_stages.json \
  --out COMPILED/mtp_summary.json
python3 tools/die_relay_check.py SELECTED/relay_stages.json COMPILED/relay_stages.json
```

`ACTUAL_VM_PATHS.json` has schema `opentallas.s81.vm-relay-paths.v1`,
`plan_digest` copied from the selected table, `plan` equal to its complete plan
identity, and `legs` containing exactly `write`, `read_request`, `read_return`,
and `commit`. Each leg is a nonempty list of alternative paths. Each path is a
nonempty list of exact bus IDs from the selected table, in traversal order.
Consecutive die buses must meet at the same tile instance. Internal tile
latencies are excluded and stay in the measured service profile/ledger.
Zero-stage buses must be explicitly listed. A missing bus never means zero.

This path does not accept domain conversion: every used bus must have the
known `stream_1p2` domain and the table must use the 1.2 GHz stream period.
Serial VM paths require a separately measured domain/phase conversion contract;
unknown or serial domains are rejected. Equal-age groups must already be padded.
Exporter problems, incomplete tables, missing source commits, stale plan
identities/digests, and disconnected paths are rejected. No diagnostic override
or runtime fallback is provided.

The relay-only conservative cost uses the maximum write alternative plus the
maximum read-request alternative plus the maximum read-return alternative.
The output preserves the original accepted/proposed ledger totals. A separate
candidate projection excludes VM.RELAY from both statuses and adds the selected
relay cost once; selection does not mark that cost accepted or measured. Commit stages are reported explicitly;
existing VM core/commit remainder rows stay charged until the current native
service composition has been measured. The output retains the table digest and
records used bus IDs in a compiled table for the existing mismatch checker.

The path manifest remains an owner-declared coverage input. Its existence does
not prove all native operations, producer ports, SRAM services, physical routes,
or the exact token timeline. Output is always COMPOSED_NOT_NATIVE. As of this
change the c27 owner has no selected current VM relay table or bus manifest, so
there is no new c27 performance number. The prior geometry screen is available
only through explicit `--legacy-relay-screen`, labelled historical.
