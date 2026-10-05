The final Qwen calendar consumes producer commit `8fab95560`, its actual recipes,
exact temporary allocation homes, instruction-dependent vector counts and R17
provider commit `570536f48`. The previous `native_r3` Qwen artifact remains an
immutable WIP baseline. `calendar_v2` is the inspected final-source baseline;
its manifest, summary and proof are committed, while bulk gzip is regenerable.

Qwen covers all 1737 PCs/21 classes with 108441 events, 356675 dependency edges,
449 occupied resource slot identities, and independent interval proof PASS.
Every exported primitive vector count matches the expansion. Source-pin replay
is byte-exact PASS. Endpoint latencies are explicit positive provisional inputs;
1728044080239 software ticks do not represent hardware cycles or a clock claim.

Actual producer scratch is 2801511424 bytes/rank, workspace base 4748333056,
end 7549844480. These are concrete software addresses/leases beyond the retained
33554432-byte source spill. They are not qualified physical residence and are not
a bounded tiled allocation. The successor extent is recorded, with source-backed
admission false. No independently sized whole-array double buffers are used for
this final Qwen export.

DeepSeek's preserved `native_r3` baseline covers all 2213 PCs/30 classes with
6589361 events and interval proof PASS. Its source-pinned captured producer is
`inputs/h3_deepseek_complete_native.py.source`, not a final committed producer
export. Scratch is 8598331392 logical bytes/rank over 96 ranks, without native
physical base/lease bindings. The reported byte-arena width is 34 against the
source model's AW27; this is a constrained logical extent demand, not a checked
physical aperture/decoder verdict. Use original code `674c3b932` for exact replay
of that baseline, not the changed final Qwen adapter.

The added `execute_primitive_vm` API executes the pinned producer primitive
machines: DS SSA programs and Qwen instruction/loop recipes. It requires payloads,
source hash, finite scratch and instruction bounds, with explicit Qwen storage/
weights or DS DIV providers when referenced. It does not call a source opcode or
golden numerical implementation. Scratch limits cover resident tensor values,
not NumPy transient/process memory. Numerical runtime never supplies schedule
costs. Tests validate FP32 rounding, source pins, missing providers, finite tensor
capacity and runaway/empty loops. This is a primitive adapter, not an integrated
whole-program DeepSeek provider VM.

Producer numerical evidence copied exactly from `8fab95560`: 31 passing tests,
two deterministic reduced-shape 36-layer fixtures, each executing 1737 PCs,
3474 hashed outputs, 62464 provider publications and releases. It does not prove
trained-checkpoint full-geometry execution or physical/RTL arithmetic. No new
DeepSeek snapshot numerical-suite PASS is claimed.

Remaining unsupported integration: executable bounded tiled Qwen export and its
ordered native/transfer binding; bounded tiled DS compiler and concrete native
scratch bases/leases; DS whole-program auxiliary LOAD/provider orchestration;
full-geometry trained-weight numerical regression; measured endpoint calibration.
Popper's live `tiled_r1/dewey_interface.txt` has been inspected: 32 RF vectors,
17408 shared bytes and zero temporary HBM are currently a WIP preimplementation
model, not accepted executable evidence. Parent owns joined system integration.

Regenerate from this worktree (no main or pinned file mutation):

```sh
python results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/export_pinned_input.py
python tools/h3_complete_native_calendar.py --target Qwen --native-lowering results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/Qwen_native.json.gz --qwen-providers results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_provider_binding.json.gz --out /tmp/h3-final-qwen-calendar
python tools/h3_complete_native_calendar.py --verify --target Qwen --native-lowering results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/Qwen_native.json.gz --qwen-providers results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_provider_binding.json.gz --out /tmp/h3-final-qwen-calendar
python -m pytest -q tests/test_h3_complete_native_calendar.py
```

Measured Qwen generation: 41.20 seconds, maximum RSS 5503456 KiB; reserve 10 GiB
free memory. Replay has comparable cost. Full two-target baseline previously took
about 420 seconds and 30633996 KiB sampled RSS; reserve at least 60 GiB. Do not
launch an all-target rerun for Qwen-only changes. DS bulk input is regenerated
with the committed `inputs/compile_deepseek_snapshot.py`; full bulk can remain
outside git. Existing failure records and producer snapshots are retained.
