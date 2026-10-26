KV v3.2 has four one-bit controls routed independently beside wider data lanes.
The generic checker credits a single widest forwarding path, so it under-counted
these source-bound controls. The generic path rule remains unchanged.

The new optional census-map field `forward_routes` supplies an exact census
source instance/bus and destination instance/bus plus an ordered list of live
plan lane IDs. The checker requires a unique as-built census row, at least two
distinct lane IDs, exact positive widths, canonical control bus names at lane
ends, continuous partitions and matching internal feedthrough slots, and
explicit forwarder grants at every transit partition. Malformed witnesses fail
closed even if unrelated aggregate lane capacity would otherwise cover a pair.
Witness lane capacities are removed before measuring remaining data capacity;
only the independently proved control bits are then added.

`forward_routes.json` contains the four exact current-v3.2 witnesses. Install
its array as the `forward_routes` key of census/census_map_v32.json. The patch
`census_rows_v32.diff` makes that metadata reproducible from the current KV
census generator (its exact source hash is recorded alongside). Lane IDs are
intentionally exact; a changed plan must regenerate and requalify them.
The plan itself, ports, lane inventory, widths and latency are unchanged.

The scoped source-bound replay is in `replay.py`; `witness.json` records its
current plan/map hashes, positive result and all causal negatives. All seven
named route-segment deletions must fail. Also tested: malformed/short/duplicate
witnesses, wrong source/destination, wrong route width, broken internal slot,
and absent forwarder grants. This proves plan/census route identity, not an
RTL source binding or physical result. Full G0 and the complete die-plan test
suite are separately required before integration.

Rejected approach: a generic max-flow replacement passed full G0, but deletion
of actual L746, L2047 and L2051 still passed because aggregate unrelated lane
capacity masked the missing control. That approach was discarded and is not
part of this change. The exact-route declarations make those deletions fail.

Publication scope: the tool/test commit is independent and keeps main's v3.1
behavior unchanged. This packet targets the paused WIP v3.2 (160 partitions /
45 types), whose exact source hashes are in source_manifest.json. Do not apply
these lane IDs to v3.1. No v3.2 plan/generator file is imported by this packet.
The coordinator must source-pin and import v3.2 separately, then apply its
census metadata/generator patch. G1 review of that v3.2 plan is still required;
this metadata-only change does not alter geometry or grant any P&R.
