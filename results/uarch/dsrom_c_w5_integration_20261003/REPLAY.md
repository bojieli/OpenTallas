Production integration follow-up to W5 milestone `769a0f764`, on the same isolated branch. No RTL change, simulation, fixture repetition, Liberty re-screen, proof campaign or physical job.

Generate the source-bound dependency contract in a fresh directory:

```sh
python3 tools/dsrom_c_w5_integration.py \
  --inputs results/uarch/dsrom_c_w5_integration_20261003/inputs \
  --out /tmp/dsrom-c-w5-production-contract-fresh
```

`inputs/origins.json` identifies exact commits or explicitly uncommitted W2 snapshots and SHA256 hashes. The tool verifies those hashes and the retained RTL predicates, maps 2,682 active pairs into the retained NP4096/128-root storage, and emits eight debt classes. It preserves 1,414 inactive-input storage pairs and assigns no return-area or latency credit. RD4's measured nine-cycle reuse versus the four-cycle target is retained from committed `046bf5026`; the rejected credit successor is not a debt provider.

W2's selected return is RD64/root128. Its new ragged binding and loaded timing are unqualified, and its S73 area screen fails. This mapping is an integration obligation, not admission for that geometry. Prior qualified return evidence is retained at its original scope.

The field's `busy` is `|p_busy` and omits the return network. Node queue counts, valid/add/forward pipelines and RST stages must remain debt. Roots add input-queue occupancy, held sibling validity, every adder pipeline valid stage, and output-delivery/consumer retirement. `add || sv` alone misses the intervening occupied adder stages. The wrapper's `quiet` is simulation-only, defaults to zero in hardware, and is not connected by the retained field. No production empty predicate is fabricated from those ports.

The eight debt classes must be reduced through an explicitly priced, protected always-on path. Source-owned producer admission must stop before isolation. Quiescence snapshots must be coherent across streaming/serial/CDC domains and include in-flight transitions, transaction identities, reverse ACKs, mutable faults and both link directions. Unknown or unconnected obligations assert debt; they never release a credit or authorize sleep. No reset may invalidate an outstanding obligation without the existing coordinated retirement contract.

W2 provider homes and matrix placement are not production wake adjacency. Actual directed operation edges, route/CDC delays, AR/MTP arrival and departure times, and qualified-return retirement calendars remain required. MaxwellPDN must supply real switch/clamp/retention and SerDes standby characterization, slots, ramp/current and concurrent-wake grants, droop budget, and contextual SS/FF routes under the unchanged 60/25 ps uncertainty policy. Engram stays always on. No analog or 10% residual adoption.

The follow-up packet is copied under `/tmp/dsrom-c-w5-coordination-20261003/`. Peer acknowledgment and production binding remain pending. Parent source intake is deferred until its realmem/actual combined-HBM factory context is ready. Historical W5 pass/failure records are unchanged; `r1/model.json` is a new successor contract and `intake_ready=false`.
