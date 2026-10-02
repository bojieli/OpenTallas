W19 production PC10 endpoint successor

Selected source assignment is rank r -> physical die r,32 SMs per die. This comes from W19 TP96/64-head oreduce product, its explicit96-GPU-die machine contract, the unified model96-die row, and the reviewed V1 map; no CPU backing namespace is inferred as a die. The complete3072-entry mapping and49152 source/6144 output tile references are exported in directory_r3.json.gz. Actual zpart/z home indices and slots replace directed state-fragment/slot32 bindings. ProductionPC10 refuses missing PC9 sources, mismatched directory or state-fragment locations, and non-generic calendar executors. ProductionSharedFactory provides the actual per-die/per-SM64KiB directory with existing addressed byte semantics and finite tag credits. It performs no arithmetic.

The matrix-frame adapter selects a512B transient vector in the final16 rows of one actual32KiB macro per L2 bank. Each slice has64 real source macros; macro index=56+bank.32 reservations cost16KiB general L2 capacity per die,0.1953125percent. Cache-miss latency remains UNKNOWN. This is a NEW opt-in allocation requiring explicit cache/directory exclusion, not an installed mapping or a free L2 slot. The original128B-line exploratory directory_r1/r2 is retained but superseded: a full512B reservation allows the parent bank lease to hold through RF mirror publication without requiring early line release.

The executable vector owner is an additive adapter over exact54bf owner source:32 ordered bank-word handshakes (16 writes,16 reads), then both-copy H1 write observations and common host ACK, visibility, consumer, reverse. It retains450 bits,605.64um2 provisional entry footprint, within the576bit bank metadata budget and existing connector reservation. Existing512B C0/V1 destination must stay leased during assembly; actual route and hold bounds remain missing. No extra unpriced wide buffer is assumed.

Counts expose physical RF pair response50,331,648B for25,165,824B contributor payload (unused second RF read remains charged),884736 shared64 commands/56,623,104B, and6,291,456B output mirror writes. The selected matrix-frame L2 path adds2048 write128 and2048 read128 operations:40960 reference leaf-work edges summed across active units,160 per active source SM. These are unqualified source model references. Two new event keys are exported; existing RF/shared/provider/I64/RMW charges are not added again. No automatic latency delta or token rate is assigned.

Source mapping admission PASS; finite production endpoint composition and hardware admission FAIL. All external waits and actual contender inventory remain explicit null. vector_finite_bounds requires positive source-pinned terms and counts all32 words; software ticks are rejected. Qualified block terms alone do not qualify a complete token.

Actual PC0-9 prefix receipt remains FAIL_CLOSED_PRESERVED, reason persistent output needs concrete physical home directory. PC9 producer RF bytes are therefore not claimed ready, and production PC10 was not executed with substitute data. The adapter is ready for the actual live provider once producer publication is repaired. This is independent of other contexts and numerical runs. No engine RTL or P&R job was started.

Replay:

    python3 -m unittest discover -s tests -p test_h4_hbm_w19_pc10_endpoints.py
    python3 tools/h4_hbm_w19_pc10_endpoints.py --out results/uarch/h4_hbm_w19_pc10_endpoints_20261002/directory_r3.json.gz --verify

Source archives include W19 product/machine contract, unified model, actual floorplan/homes/tiles, exact generic calendar, byte provider, and retained owner source. Generator needs only stdlib and no historical Git objects. See handoff.json for exact runtime and owner/calendar interfaces. Historical receipts and original pinned tools/tests remain byte-identical.
