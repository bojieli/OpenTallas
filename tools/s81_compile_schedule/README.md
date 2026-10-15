# S81 fixed cycle calendar compiler

`compile_calendar.py` lowers already scheduled stage jobs to exact physical VM
edges. It has no runtime inputs and never adjusts execution in response to
credits, readiness, queue occupancy, observed completion, or fixture values.
Compilation rejects memory/transfer conflicts and requires a revised offline program.
The optional `--schedule-native-jobs` pass assigns fixed job issue cycles
offline using owner-provided native durations, predecessor completions, one
in-flight job per physical engine port, and exact recurring clock phases. It
reports the changed makespan and leaves performance acceptance false. It never
uses priced graph durations in place of missing measured native durations.
Operator fusion and endpoint remapping must precede this scheduling pass.

Every native job needs its real endpoint, native engine, fixed duration, tag,
client, start phase, and explicit accesses. Durations must match the scheduled
program, including physical transport. Evidence pins the implementing RTL and
its separately measured timing/port contract by path and SHA256. Accesses use
stream-relative issue/response/commit/deadline cycles and VM-relative ingress,
bank enqueue and service cycles. The VM origin is the last VM edge at or before
the scheduled job start. Templates only apply at the declared recurring clock
phase; their phase period must repeat both clocks exactly.

Every tensor requires explicit physical base row, row count, native producer
(or declared external input/resident constant), consumers, and pinned allocation
contract evidence. Reads of native-produced rows require complete word-mask
coverage from actual native writes. Overlapping live allocations are rejected.
A C++ snapshot allocator is not a production allocation contract. Internal
reference/fixture tensors are rejected, even if their numerical results match.

The generated schedule is checked using
`tools/s81_suhc/static_vm_reservations.py`. Any missing binding, stale evidence,
unsupported native operation, latency mismatch, timing conflict, or unproduced
read prevents **all** dispatch and emits no partial execution calendar.
`qualified` remains false: source-backed native RTL replay, physically mapped
memories, digital links, die binding/timing and throughput gates are separate.
Compiler tests qualify only this lowering mechanism.

```sh
python3 tools/s81_compile_schedule/compile_calendar.py \
  --programs results/rtl/s81_ctrl_20261008/programs \
  --bindings actual-owner-bindings.json --contract actual-native-vm-contract.json \
  --out compiled-calendar.json
python3 -m unittest discover -s tools/s81_compile_schedule -v
```

The current 59 committed stage programs contain 2,367 jobs: 920 SU, 560 HC,
332 field, 210 collective, 168 service, 97 selector, 59 hop, eight collector,
eight Engram, four head, and one embedding. These programs are arithmetic
operator graphs with ASAP duration estimates. They do not supply the complete
native tensor producer allocation or fixed physical memory calendar. The
fullshape compiler test therefore proves all 59 programs reject absent owner
bindings, not that 2,367 native jobs have been implemented. SU/HC snapshot
addresses and ideal LVM10 response timing cannot be promoted to production
bindings. The native VM service, field/collective mapping and owner-provided
operand contracts must be connected before full-native dispatch is possible.
