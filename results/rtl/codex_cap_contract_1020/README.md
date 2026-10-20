# Fullsix CAP capture calibration, 2026-10-20

The unchanged TOK2 L16/E24 fullsix executable captures all 512 genuine L0
`attn.wq_b` rows correctly when its private source programme supplies 15 real
target-3 CAP descriptors. This is component evidence. **Full-stage consumer
retirement and deadline qualification remains open; P126 remains proposed.**

The baseline input is the immutable P126 run in
`results/rtl/toksim_s81d_wqbp_1020/runs/l0_p126`. Its original diagnostic
intentionally leaves CAP unconfigured: no CFG, no CW, and sticky F9. The replay
changes only source-control words. All 1,019 image hashes match the baseline and
both negative controls. The executable SHA and all input/golden hashes are in
`receipt/candidate/exe.sha256`, `images.sha256`, and `receipt/receipt.json`.
No RTL build, fixture rewrite, data mask, or cycle exclusion was introduced.

Observed complete returns rotate row-flag domains 1,2,3,0. A single descriptor
cannot cover their span within the 11-bit row-count field. `add_fullsix_cap_program.py`
adds 15 descriptors at unused XR control edges. The descriptor uses BF16 RNE,
head-6 storage base plus actual row flags, row count 828, and output base zero.
The first replay's command times are a **calibration from this vehicle's observed
idle windows**. A subsequent private source-derived lowering is described below.
Neither is a released general compiler lowering. No hardware edge is added.

The independent fixture golden computes each row from the released checkpoint's
actual input and weights, verifies its BF16 result against the released shard,
then checks every CW value and address and every VP word/mask/address exactly
five edges later. Results:

| Case | CW / VP words | Missing rows | Sticky cause | Admission |
| --- | ---: | ---: | --- | --- |
| Matched nominal | 512 / 512 | 0 | 0 | Capture component PASS |
| First descriptor wrong row base | 476 / 476 | 36 | F9, `0x100` | Rejected |
| Second descriptor five edges late | 512 / 512 | 0 | F11, `0x400` | Rejected despite numerical match |

Nominal last frame return is edge 3560, last CW 3632, and last VP capture 3637.
The measured frame-to-last-VP tail is 77 edges. The existing priced 195-edge
tail leaves 118 edges diagnostically; this is **not consumer deadline proof**.

The original executable still exits 1 with exactly three legacy source checker
errors. Its latest-GO attribution counts 21 reads in epoch 0 and 27 in epoch 14,
and its serial assertion expects 15 end markers. The pipeline accepts the next
phase before the previous phase's final three source reads and emits one end
marker for its single calendar segment. An independent checker decodes the
frozen physical stream ROM and checks all 360 timed requests, gate bits,
indices, live-half validity, retained-source selection, all 15 GO times, and the
single end marker: PASS, exactly 24 reads per real phase. The original failure
and its raw log are retained. Six admission negatives reject a late read, dropped
half, invalid source, wrong GO phase, extra end, and payload mismatch.

The wrappers record simulator status separately from collection status. A
wrapper's successful collection is never reported as simulator PASS.

Remaining full-stage obligations:

- Integrate the private lowering into the real die compiler for its actual
  eight-frame/11-phase shape, with complete control-slot and lifetime checks.
- Observe runtime per-tag retire actions and tie them to actual final consumers.
- Connect and check the real downstream read/transport/consumer programme and
  its unchanged deadlines. The existing fullsix vehicle leaves the other four
  VP `lo` outputs disconnected and has no complete consumer scoreboard.
- Correct the old bench's serial bookkeeping in a new qualified vehicle; the
  present external schedule proof does not rewrite its historical verdict.

Fleet runs: nominal `oth-ubuntu-473921-1792485229`; wrong-row-base
`oth-ubuntu-494970-1792485445`; late-CFG `oth-ubuntu-494971-1792485445`;
final matched admission and six negatives `oth-ubuntu-522465-1792485697`;
receipt `oth-ubuntu-524328-1792485728`. All are terminal. Original XDIE real-shift
jobs and GL24 owner-view jobs are separate and were preserved.

## Source-derived lowering and additional layers

L2 and L14 separately pass all 512 released-fixture CAP/CW/VP captures, the
360-request source schedule, and zero CAP/landing/VP faults. Their original
simulator exit remains 1 with the same three legacy bookkeeping failures.
Runs are `oth-ubuntu-529131-1792485873` and `oth-ubuntu-529093-1792485873`;
receipts are `receipt/capture_l2` and `receipt/capture_l14`.

`check_fullsix_static_capture.py` retags the frozen source plans with their
semantic rows and actual frame launch-counter flags. Their 625 predicted frame
words match every observed time, lane, tag, value, and error. It then applies the
selected dr6/LD16/ED24 paths and the unchanged CAP cycle model: all 512 CW values,
addresses, and times match exactly, with no model faults. The model's post-edge
outputs are observed by the fullsix pre-NBA positive-edge monitor one edge later;
the component CAP bench checks those same registered values at the following
negative edge. This observation conversion adds no protocol edge.

`compile_fullsix_cap_program.py` now emits the 15 descriptors **without reading
any observed log**. It derives each phase's first FIN edge from the frozen
planned frame returns, the explicitly retained calibrated frame offsets,
selected landing delays, one lane-pin edge and three unchanged return-tree
levels. It emits the XR command three edges earlier and runs the complete CAP
cycle model to reject open-slot, decode, pairing, and port faults before output.
The lowering deliberately refuses profiles other than this private six-frame,
15-phase head-6 vehicle. Three preflight negatives reject wrong CAP delay,
partial frame set, and XR control-slot collision.

Its actual executable replay `oth-ubuntu-541519-1792486114` passes 512 golden
CAP/CW/VP captures, the 360-request source schedule, all 625 source-plan frame
words, all 15 command-to-pin CFG times and the unchanged CAP cycle model.
`receipt/source_compiled` retains the emitted programme, model contract SHA,
raw simulator failure, and every checker result. The first and last descriptor
times differ from the trace-calibrated replay, demonstrating that this path is
driven by the source model rather than copying observed CFG times. Consumer
runtime retirement and deadlines remain unverified, so this proof does not
promote P126 from proposed to the released composition.

The final checker also requires the complete terminal trace and the exact known
legacy source failure receipt, including simulator status 1. Missing terminal
status, a fourth unknown source error, or an incompatible simulator status is
rejected even with all 512 numerical CAP and VP captures intact. These three
causal admission regressions pass. The final matched matrix rechecks all six
nominal/negative/layer/source-compiled cases, each against its original image
SHA manifest and with explicit fixture metadata SHA. Final sealing run
`oth-ubuntu-1144901-1792486931` is terminal PASS. This tightens component admission;
it does not turn the preserved simulator failure into a full-stage PASS.
