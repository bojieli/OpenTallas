This milestone consumes the final committed DeepSeek native emitter `bed325f89`
and Qwen `8fab95560` plus concrete workspace provider `33b741b4e`. It preserves
`5881a3b92`, `native_r3`, failures and their source hashes. No RTL, hardware build,
main checkout mutation or hardware clock transfer is part of this milestone.

DeepSeek final input is `c7ae6baf3f57d3b8d23b3532dad9d1fa921ac86736b5e8b5a229f644a1994313`.
All 2213 PCs/30 classes and all 1127 templates are consumed. The adapter now uses
each actual all-gather buffer recipe in source order, rather than only the
primary extent-preview recipe. SSA symbols are distinct across buffers. Every
emitted primitive count is independently compared against the producer's
`instruction_batches128_by_opcode`; mismatches reject compilation. Per-PC count
evidence is committed in `final_ds_bed325f89/calendar_r1/native_PC_counts.json.gz`.
Actual LOAD provider descriptors are retained by PC, alongside concrete version
residence indices and source address views. The archived 18-file input/source
closure is validated without another producer worktree.

DS finite interval proof: 6589361 events, 22839443 dependency edges, 21505 occupied
resource slot identities. All-PC primitive count gate PASS. The normal-path
calendar is 2018579897074 positive provisional software ticks, not hardware
cycles. Generation measured 404.33 seconds and 33610096 KiB peak RSS. Reserve
65 GiB free memory. Byte-exact source-pin replay PASS in 228.90 seconds,
39770360 KiB peak RSS. The final emitter changes the
conservative fallback scratch demand to 5459735552 bytes/rank (96 ranks), compared
with the preserved old 8598331392-byte/rank baseline. This is an unallocated
logical successor arena, not actual hardware admission. The producer itself
reports at most 207020036 materialized live tensor bytes, no resident tensor base,
and no streaming tiling proof. The two workspace definitions are not equivalent.

Qwen final input remains `75a3997b07b492c4c1f8eeec55488c8ef754a49987aa297e1cc16648e49c3674`.
R20's 19620 temporary homes are joined to actual admission/retirement intervals
over 1956 rank/PC leases. Version, base, extent, RF slots, within-PC aliasing,
finite highword capacity and premature lease reuse are checked. All 1737 PCs/21
classes pass primitive counts and the resource proof (108441 events, 356675
dependency edges). Its old native_r3 source mismatch is preserved; the new final
source-match proof is true. The separately reserved older padded review arena is
not adopted. Actual compact interval records, including address bounds and
fences, are committed in `workspace_r20_33b741b4e/calendar_r1/workspace_intervals.json.gz`.

All 432 I64 homes have explicit upper-word sidecar intervals. The added software
codec splits signed64 bits into LE lower/upper32 words and rejects mismatched
owner/definition/iteration identities on join. The calendar separately charges
upper-word reads, split/join, conservative sector RMW read+merge, and visible
upper-word writes before consumption/retirement. Split/join and RMW merge each
cost an explicit provisional 32 ticks per 128-word tile; sidecar sector read/write
costs are 106/126 provisional ticks. No missing cost becomes zero. The source
producer primitive VM still uses its own numerical arrays; a full program run
through physical sidecar serialization is not claimed by this standalone codec
and interval proof. The provider's physical codec remains unimplemented/unqualified.
The R20 join produces 1729318542447 software ticks. Generation measured 55.79
seconds and 5810080 KiB peak RSS; reserve 12 GiB. Byte-exact Qwen replay PASS.

The committed 21-test suite covers final DS IOTA execution, portable source
closure rejection, multi-buffer gather counts and mismatch rejection, I64 signed
extremes and identity/extent faults, concrete workspace intervals, overcapacity,
and existing DAG/resource/version/rounding negative controls. Producer receipts
are copied byte-exact: DS 82 tests cover toy native kernels, finite logical
provider joins, exact scalar DIV faults and selected-packet rejection; no trained
checkpoint token. Qwen 31 tests and two reduced-shape 36-layer fixtures retain their
earlier scope. These receipts are not new full-checkpoint numerical executions.

Remaining unsupported: DS native physical scratch bases/leases and bounded
tiling; DS explicit auxiliary/immutable provider payload and physical address
qualification; integrated whole-program sidecar transport execution; measured
provider/native endpoint costs; trained-checkpoint full-geometry regression.
Popper's active bounded-tile compiler worktree was inspected. At this milestone
there is no final source-pinned executable tiled export to consume; its WIP
feasibility model is not substituted for execution. Software work does not wait
for RTL. Parent owns combined system intake.

Regeneration, run from the isolated worktree at this milestone revision:

```sh
python results/uarch/h3_complete_native_calendar_20261002/restore_committed_inputs.py results/uarch/h3_complete_native_calendar_20261002/final_ds_bed325f89
python results/uarch/h3_complete_native_calendar_20261002/restore_committed_inputs.py results/uarch/h3_complete_native_calendar_20261002/workspace_r20_33b741b4e
python results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/export_pinned_input.py
python -m pytest -q tests/test_h3_complete_native_calendar.py
python tools/h3_complete_native_calendar.py --target DeepSeek --native-lowering results/uarch/h3_complete_native_calendar_20261002/final_ds_bed325f89/program_final.json.gz --out /tmp/h3-final-ds-calendar
python tools/h3_complete_native_calendar.py --verify --target DeepSeek --native-lowering results/uarch/h3_complete_native_calendar_20261002/final_ds_bed325f89/program_final.json.gz --out /tmp/h3-final-ds-calendar
python tools/h3_complete_native_calendar.py --target Qwen --native-lowering results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/Qwen_native.json.gz --qwen-providers results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_provider_binding.json.gz --qwen-workspace results/uarch/h3_complete_native_calendar_20261002/workspace_r20_33b741b4e/join.json --out /tmp/h3-qwen-r20-calendar
python tools/h3_complete_native_calendar.py --verify --target Qwen --native-lowering results/uarch/h3_complete_native_calendar_20261002/final_qwen_8fab95560/Qwen_native.json.gz --qwen-providers results/uarch/h3_complete_native_calendar_20261002/inputs/Qwen_provider_binding.json.gz --qwen-workspace results/uarch/h3_complete_native_calendar_20261002/workspace_r20_33b741b4e/join.json --out /tmp/h3-qwen-r20-calendar
```

Bulk native input/calendar gzips remain outside this handoff; committed producer
refs restore inputs and pinned code regenerates outputs. Existing output
directories are immutable: use a new directory, then `--verify` there.
