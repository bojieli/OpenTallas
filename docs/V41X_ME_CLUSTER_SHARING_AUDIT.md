# V4.1 ME activation sharing boundary

Status: preflight for a finite-resource cluster, 2026-09-28. This audits the
rank-0 TP4 executable layer-0 emitter at `codex/v41-fullshape-emitter-binding`
`9cefba50` and the all-40-layer shape program in `tools/hdc_replay_v41.py`.
Only layer 0 has an executable, bound TP4 ME trace. The other rows below are
placement requirements, not RTL or throughput evidence.

## Which operations can share one activation store?

| ME use | Input reused by output rows? | Store and schedule condition |
| --- | --- | --- |
| `wo_a`, ROM weights | Yes, inside one output group. The exact L0 trace has two distinct 4096-element ACC spans, 1024 outputs each, `xjs=0`, split 0. | Preload each span once. All tiles sharing the store must consume the same group, beat `q`, placement `plg`, and position on each cycle. Groups 0 and 1 need separate epochs or a barrier before overwrite. Distinct users and MTP positions need separate residency/epochs. |
| Router gate, ROM weights | Yes for the output rows of one token. L0 has `K=1280`, `nout=96`, split 2. | The cluster may share the token's XN span after one preload; row tiles need identical beat/placement schedule. Sharing with `wo_a` requires a new epoch and source switch, since XN and ACC differ. |
| Compressor `cwkv`, index-key `iwk`, index-weight projection `iwp`, ROM weights | Yes within a matrix's output rows, but input spans and conditional layer execution differ. | Separate preload epochs for XN or LAT; the same stored XN can be retained across compatible operations only if scheduling proves no intervening overwrite and bank addresses agree. Shape program counts are 4 `cwkv` (one at K1280, three at K2560), 4 `iwk` (K128), and 8 `iwp` (K1280); the executable TP4 traces for these layer types are pending. |
| Vocabulary head, ROM weights | Yes across output rows for a token's XN. | The shape program has one large `K=1280`, `nout=32320` head op. It is a separate epoch and cannot be assumed simultaneous with layer-local matrices. Output placement and distributed argmax still need a bound TP4 implementation. |
| Attention score, HBM KV weights (`me_wsrc=1`) | Query is stable across the scanned rows of **one head**; different heads have different queries. | A shared store can hold one head/group query at a time. The KV source and scan HBM bandwidth dominate; do not apply the ROM-weight `wo_a` preload saving to the KV traffic. The L0 exact op is `K=512` with dynamic row count. |
| Attention value reduction, HBM KV weights (`me_wsrc=1`) | Softmax probability vector is stable across value dimensions of **one head**; heads and positions differ. | Source S can be reused within a head, but selected-row count and per-head `S` differ. Full-shape `T_MAX` reaches 5120, exceeding a single K4096 wo_a epoch, and the KV operand remains HBM served. The L0 exact op has dynamic K and `nout=512`. |
| Index scan, HBM index keys (`me_wsrc=1`) | Quantized index query is stable across rows for one index head; each head differs. | Per-head query residency can help, but scanned keys remain HBM traffic. Cross-head multicast requires equality proof; none is assumed. |

The bound layer-0 ME instructions are at PCs 23 (score), 31 (P·V), 35 and 36
(`wo_a` groups), and 53 (router gate). The `wo_a` bound trace in
`results/rtl/hdc_v41x_fullshape_program_bind.json` has word bases 7680 and
73216, X bases 74272 and 78368, each K4096/1024 rows. The corresponding
checkpoint gate in `results/rtl/hdc_v41x_fullshape_woa_xmacro_full1024.json`
passes 2048/2048 raw FP32 outputs. The all-layer ShapeBuilder still emits its
old grouped `wo_a` descriptor and is unsuitable as executable evidence for
that matrix until regenerated from the bound emitter.

## Port, capacity and cycle contract

The candidate store has 16 analytical 1R1W SRAMs (8 chain banks × 2
positions), each 128×256 bits and 3891.57696 µm² outline, or 0.062265 mm²
per shared store. Eight chain banks each present one 128-bit read **per
position** per cycle; this is 2048 BF16 bits total into one 64-lane, two
position ME tile. The SRAM has one masked write port per bank. A wide preload
is eight 128-bit bank writes per selected position/cycle, so it needs no extra
SRAM port. It blocks narrow writes for that cycle; this phase exclusion is
enforced in the wrapper. Macro TT read tCQ is 351.77 ps in the analytic view.

The source VM candidate reads four 512-bit FP32 bank words per cycle. A
two-stage 64-lane FP32→BF16 RNE converter accepts those 2048 bits in bank
order and produces 1024 BF16 bits, position, element offset and fault flags
after two register stages, then accepts another beat the next cycle. The
checkpoint-backed two-stage gate in
`results/rtl/hdc_v41x_fullshape_woa_pipe2_full1024.json` passes 2048/2048
raw FP32 outputs with 128 preload issues and writes, 131108 weight-bank reads
and 131345 total cycles; its extra fill stage is hidden by the existing
preload barrier. An input register on the 16-macro store is also checkpoint
exact: `results/rtl/hdc_v41x_fullshape_woa_pipe2_inreg_full1024.json` passes
2048/2048 rows in 131347 cycles. That RL4 boundary adds one fill cycle per
group to the RL3 result while sustaining one read beat per cycle. A real
four-bank VM macro slice now supplies the first 16 rows/group through the
same converter and store: `results/rtl/hdc_v41x_fullshape_woa_vmread_first16.json`
passes 32/32 output rows and all 512 returned 512-bit VM words against the
checkpoint. The slice is 384 KiB and initializes resident ACC before timed
service. Its original VM read RTL is physically unclosed, so this establishes
numeric and address order only. A bank-local ME output register also passes
the first 16 rows/group at RL5, adding one cycle per group; its full-depth
and physical gates remain pending. Thus two
K4096 `wo_a` groups have a 128-cycle VM read-issue
floor, plus VM read latency, conversion, store write and any barriers. The
existing four-wide adapter consumes 2048 LOAD issue cycles for those two
groups. The checkpoint-backed matched shared-adapter gate now measures the
isolated LOAD saving: `results/rtl/hdc_v41x_fullshape_woa_preload_matched.json`
binds the same source and fixtures for 2048/2048 exact raw FP32 rows,
133261 cycles with four-wide LOAD versus 131345 cycles with bank-major
64-wide preload, a reduction of 1916 cycles (1.44%) for this two-group op.
Both arms make 131108 weight-bank reads. The wide arm issues and writes
128 preload beats, rotates physical VM bank quarters by two, and charges its
converter and store latency. This is **not a token-rate gain**: the TB supplies
the four VM words and the actual controller/read selector, finite port
schedule, 41-consumer multicast and full cluster route still need gates.

At 83,328 BF16 MAC/cycle, one store per 64-MAC tile would imply about 1302
stores and 81.07 mm² of SRAM outlines, incompatible with the design's 3.41
mm² SRAM ledger. Even 16/32 stores add 0.996/1.992 mm² of outlines, before
macro halos, queues, conversion, registered multicast, routing or energy.
Sharing 32 stores among roughly 41 tiles each is only a candidate: the
whole cluster must prove lockstep requests and bound its 2048-bit fanout.
The 3.41 mm² ledger already covers other memories and cannot absorb these
stores silently.

The direct one-stage converter and direct macro store have not closed a
0.92-ns route. Their source-pinned route records describe the actual setup
and hold failures. The two-stage converter's completed global route has
setup +8.4 ps and hold +15.8 ps at 0.92 ns, but its detailed route was
stopped when the local host ran out of available memory; it is **not** a
routed timing verdict (`results/physical_abi3/asap7/hdc/v41x/ot_hdc_v41x_fp32_bf16_preload64_pipe2/physical.json`).
The input-registered macro store has a negative
physical verdict: post-place setup −371 ps and CTS hold −112 ps after 9507
hold buffers, ending in RSZ-0060. Its wider bank-local path needs another
microarchitecture revision (`results/physical_abi3/asap7/hdc/v41x/ot_hdc_v41x_me_xbank_macro_inreg/physical.json`).
Its 3323 pins fit 20772 sites, and the
converter's 3108 pins fit 18688 sites. These are local pin cuts, not a routed
41-tile multicast. Full die geometry, weight ROM bank
placement and sustained cluster service remain open; no row in this audit
licenses a token-rate claim.
