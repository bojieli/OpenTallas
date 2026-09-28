# Qwen O4 INT8 weight-HBM supply boundary

The comparator uses the O4 two-die TP-2 core and the **same signed INT8 codes,
BF16 row scales, ISA program, and arithmetic** as the ROM arm. Each die owns
6,144 groups of 16 lanes. One core code read is 98,304 bytes (3,072 32-byte
HBM sectors); the scale port returns one 16-scale word for each group. Four HBM
stacks per die serve both weights and FP8 KV.

`ot_hdc_qwen_int8_pc_window` is a bounded code/scale source behind the existing
one-cycle synchronous core ports. Sector `s` of code word `w` has address
`code_base + w*3072 + s`; pseudo-channel `p` owns sectors `s % PCS == p`.
Each PC has its own tagged sector bank. Scale word `w` is a separate 32-byte
sector at `scale_base + w`; the opt-in full-shape mode takes its ISA base from
`me_wcs`, independently of the code base `me_wbase`. The module fully preloads
an ISA weight operation
before asserting `w_ok`, then serves the ROM read timing without altering the
matrix arithmetic. An operation larger than `WIN_WORDS` faults rather than
silently wrapping. The HBM controller, its KV arbitration, and timing remain
outside this module.

At full G=6,144, the abstract core boundary exposes 786,432 code bits and
1,572,864 scale bits. These are internal lane-local connections, not a
plausible stand-alone die pin interface. Physical implementation must place
the PC sector banks and scale registers beside lane tiles, with hierarchy that
keeps the wide word inside the die. The reduced RTL gate does not prove this
placement or its timing.

The reduced TP-2 gate sets `WIN_WORDS=4096`, enough for its largest unchanged
weight operation. Its two arms are compiled from the same sources with only
`WEIGHT_HBM=0/1`; the same image files supply both arms. Both arms pass 16/16
prompt steps, generated token 1073, and exact logits, vector memory and KV.
ROM weights take 281,485 cycles; the behavioural two-PC HBM matrix source takes
421,965 cycles (+140,480, +49.9%). That historical gate (commit `71eae8af`)
reads embedding codes
and scales from local arrays in both arms. Its delta measures the reduced
serial matrix-operation preload with two 32-byte sectors per code word. It is not a
full-shape bandwidth ratio or chip throughput measurement.

The newer reduced matrix-plus-embedding comparator sources the token's INT8 embedding
row and BF16 scale through HBM sectors before package start; the core's
embedding ports then read only the row bank. Its standalone 5-sector row gate
is source-pinned in `results/rtl/qwen_embed_row_hbm.json`. The matched
matrix-plus-embedding package gate passes 16/16 prompt steps, generated token
1073, exact logits, VM and KV, and zero faults on both arms. ROM takes 281,485
cycles and HBM 422,093 (+140,608, +49.95%) on the **reduced scalar TP-2
vehicle**. Each die fetches 64 embedding code sectors and 16 scale sectors
from its two-PC behavioural HBM source. The standalone gate covers two successive
tokens with two row banks, serving the prior row's trailing reads during and
after the next row's preload. An address outside the current or prior row
latches a fault; it cannot silently return a zero-valued embedding. The
package completion gate also waits for both dies to start after preload, so
the controller cannot reuse a preceding token's held `done` level. The
historical matrix-only cycle delta above is separate from this measured gate.
The new result is source-pinned in `results/rtl/qwen_int8_hbm_matched.json`.
That exact reduced replay is pinned to comparator source commit `b849a7eb`.
The merged full-shape core and emitter have different source hashes; the
422,093-cycle result remains historical until both reduced arms are rerun
on the merged tree. It is not a current-source full-shape timing result.
Both arms still read CROM constants and the reduced KV cache locally. This
serial per-operation preload timing is not a full-shape O4 bandwidth ratio,
controller/KV arbitration result, routed die frequency or chip throughput.
The shipped layer emitter also stores o/down post-TP BF16 row scales in
CROM. Those weight-scale ranges must be mapped to HBM before a full-shape
comparator is described as entirely HBM sourced; they are not exercised by
the reduced matrix-plus-embedding gate.

The separate full-shape layer-0 post-TP scale supply now has a source-pinned
standalone RTL gate: `ot_hdc_qwen_post_tp_scale_hbm` preloads the contiguous
CROM address range [535041, 543233) from the frozen die-0 and die-1 images.
Each die transfers 2,048 32-byte sectors through 32 PC-local banks, then
serves all 8,192 64-bit words bit-exact with the existing one-cycle CROM
read timing. A read outside the owned range latches a fault. The record is
`results/rtl/qwen_post_tp_scale_hbm.json`. This proves the source and layout
for the two true-scale ranges; it has not yet been connected to the running
G6144 layer-0 TB or a shared weight/KV controller. Other CROM constants
remain local, and the all-weight layer/token comparison remains open.
The full-token binding also materializes the lm-head final norm as 4,096
64-bit CROM words at base zero. The same bounded source passes an independent
real-image gate for its 1,024 sectors in
`results/rtl/qwen_head_norm_hbm.json`. That head source likewise awaits
the full-token HBM arm and shared-controller service. Neither standalone
gate changes the matrix-plus-embedding cycle record.
The isolated `tb_hdc_qwen_layer0_tp2_postscale_ab` campaign now binds both
arms to byte-identical real layer-0 program, matrix, scale, CROM and X images
and the same ISA oracle (`qwen_layer0_postscale_ab_prepare.json`). Its
`POST_SCALE_HBM=1` arm preloads this CROM range before the unchanged program
starts, then reads that range through the HBM source while other CROM words
stay local. The copied TB and C++ harness lint and link at G4 with Verilator
5.050. The G6144 two-arm execution and its exact output/cycle verdict have
not run, so no layer-0 timing delta is claimed.

An isolated `tb_hdc_qwen_layer0_tp2_matrixscale_ab` adds the full G=6,144
matrix descriptor to the same layer-0 TP-2 program. Its opt-in `MATRIX_HBM`
path connects `wd_v`, independent code/scale bases, count, useful row scales,
`w_ok`, the one-cycle code/scale ports, and a 32-PC sector source. The four
real layer-0 descriptors require respectively 128/192, 88/256, 512/768 and
264/256 code/scale words. A 512-code-word and 768-scale-word window therefore
covers each complete K round without changing the ISA or FP32 accumulation.
The same HBM arm also preloads the layer's trained Q/K norm constants at
CROM addresses [4,096, 6,656), or 640 sectors per die, while the o/down
true-scale source preloads 2,048 sectors. RoPE values are deterministic and
remain local; this layer starts from an already prepared activation, so it
does not exercise embedding.
The Q/K norm source passes its own real-image, source-pinned, bit-exact
one-cycle CROM gate on both dies in `results/rtl/qwen_qk_norm_hbm.json`.
The PC response tag is 17 bits and a source fault reaches the package verdict;
the local matrix read is disabled in the HBM arm. Both matrix and post-TP-scale
HBM modes lint at reduced G=4 with Verilator 5.050. The real G=6,144 matrix
arm has not run or passed exact vectors, and this stand-alone source has no
shared arbitration with KV. The running `POST_SCALE_HBM` campaign remains
source-frozen on its earlier copied TB, separate from this new opt-in gate.

## Full-shape memory ownership still to close

The compute-cluster contract requires a tensor and buffer owner for every
checkpoint fragment and transfer. The current comparator covers only the
first two rows below; the remaining rows are prerequisites to an all-tensor
or production HBM result. The real layer-0 emitted image has 1,488 allocated
98,304-byte matrix-code addresses, 50,616 scale-ROM addresses and 543,233
CROM constant addresses per die. Its o/down post-TP scales begin at CROM
addresses 535,041 and 539,137. These are address-space facts, not a routed
HBM capacity or traffic measurement.

| Data or buffer | Reduced source-matched gate | Full-shape HBM obligation |
| --- | --- | --- |
| Signed INT8 q/k/v, o, gate/up, down and lm-head codes; BF16 matrix row scales | PC-local sectors for the reduced matrices | Bind every layer, die, lm-head and complete-round chunk to code/scale addresses; share eight package stacks with KV. |
| Embedding INT8 row and BF16 row scale | One token row per die through a two-bank HBM row source | Bind the checkpoint's full TP-2 embedding range, row ownership and 17-bit token IDs. |
| O/down BF16 scales applied after TP reduction; lm-head final norm; other CROM weights, biases and norm constants | Local CROM in both reduced arms; real layer-0 true scales and full-token head norm pass separate standalone HBM sources | Connect both sources to exact layer/head programs, then classify every other CROM range and fetch all weight-dependent ranges from HBM at the same arithmetic and rounding points. |
| RoPE tables or angle constants and program/descriptor metadata | Local constant/program images | Price storage and access, including any HBM-resident portions, without silently omitting traffic. |
| FP8 KV and scales, attention state and user/position metadata | Same local behavioural KV in both arms | Include actual HBM reads/writes, cache occupancy, four-stack-per-die arbitration with weights, and context limits. |
| Activation/accumulator SRAM, masks, queues, double buffers and DFlash speculative state | Reduced VM and package state only | Bind finite capacity, ports, fill/drain and any HBM spills; count both producer work and accepted output. |

Qwen has no DeepSeek Engram or index table; those belong to the separate V4.1
memory ledger. The proposed compute-cluster plan also requires a complete
finite-resource schedule, local placement and routed memory views before an
O4 rate or iso-area comparison can be promoted.

The finite source budget for one active die is at least a 512-word, 48 MiB
INT8 code window for an uninterrupted gate/up K round; the emitted layer-0
matrix scale bank is 1,488 32-byte words in the compact full-token binding
(47,616 bytes), while its code bank is 992 98,304-byte words. The head uses
3,168 code words and 4,752 scale words, scheduled in seven complete-round
chunks. A post-TP true-scale region adds 64 KiB per layer/die and the final
head norm adds 32 KiB; the two-row embedding cache needs at least 8 KiB of
codes plus scales per die at H=4096. These are logical storage and transfer
bounds before macro depth waste, ECC, tags, ports or wire area.

For a physical HBM-only arm, the four stacks on each die must share their
32 PCs per stack among matrix codes, row scales, CROM ranges, embedding and
FP8 KV. Each request therefore needs a source ID, region, sector address,
operation generation and response tag; bounded per-PC credits must prevent
one source from bypassing another's measured queue. Current RTL sources
preload independently and have no such arbiter. Their sector counts establish
layout and exactness, not simultaneous service or a sustainable token rate.

The first shared-service RTL is `ot_hdc_qwen_hbm_service`, which instantiates
128 local PC arbiters as four groups of 32. For physical PC `p`, the stack is
`p/32`, the local channel is `p%32`, and an accepted 32-byte sector address
must have low seven bits equal to `p`. Each PC gives rotating priority to six
traffic owners: matrix code and row scales, Q/K norm, o/down true scales,
embedding, head final norm, and FP8 KV. Per-owner outstanding credits are
finite (16 per PC by default); a prefixed response tag returns an out-of-order
read to its owner, and a write completion releases a KV credit. A delayed
response whose owner is backpressured holds the physical response. The PC
slice passes fairness, credit, backpressure and write-completion checks;
the 128-PC wrapper elaborates cleanly. This is an arbitration boundary,
awaiting the region-map adapter, packed-KV sector packer, shared controller,
finite client windows and source-matched token replay. It does not turn the
earlier independent-bank cycle counts into a four-stack throughput result.
The client ID order is 0 matrix code/scale, 1 Q/K norm, 2 o/down scales,
3 embedding, 4 head final norm, and 5 KV. Code and scale use separate sector
regions but one client credit pool; the CROM owners may be inactive on a
given layer. The layer controller must supply a 0–35 stage ID for the KV page.
With 4 KV heads and 128 dimensions per die, a full 8K stage holds
8,388,608 FP8 bytes = 262,144 physical sectors; all 36 stages need 288 MiB
of HBM per die for one user. The ~19.3 MiB on-die ring is staging, not that
HBM residency. Physical KV sector `base + stage*262144 + (logical_addr>>5)`
packs 32 logical E4M3 elements, with `logical_addr[4:0]` selecting the byte.
Exact FP8 pack/unpack, writes and token read-after-write still need a shared
controller gate.
The shared service uses a 32-bit **physical sector address**. Four modeled
HBM3E stacks provide 90 GB per die (22.5 GB each), or 2.8125 billion
32-byte sectors, which exceeds 28- and 31-bit sector addressing. The core
keeps its 24-bit logical per-layer element address; the layer/user/page
controller translates it to this physical address. The historical HAW28
standalone sources were sufficient for their isolated image slices but cannot
cover the physical capacity or a multiuser KV layout.
`ot_hdc_qwen_hbm_regions` registers a concrete one-die region binding at
stage start. The physical sector ranges do not overlap and each region starts
on a 128-PC boundary: layer code `[0,109707264)`, head code
`[109707264,119439360)`, 36 padded layer-scale pages
`[119439360,119494656)`, head scales `[119494656,119499408)`, 36 Q/K
norm pages starting `119499520`, 36 post-TP scale pages starting
`119522560`, head final norm starting `119596288`, embedding codes starting
`119597312`, embedding scales starting `139045120`, and packed KV pages
starting `139054720`. A layer code page spans 992×3,072 sectors; each layer
scale page reserves 1,536 sectors around 1,488 useful scales, preserving
physical-PC alignment. A user KV page spans 36×262,144 sectors. The last
sector for 283 full 8K users is `2809777791`, below the modeled four-stack
capacity endpoint `2812500000`. This is an addressability ceiling before
controller metadata, ECC, inactive regions and reserves; it is not a user
capacity claim. Invalid stage or user IDs fault closed. The module and its
0/35-stage, 0/282-user boundary test do not yet drive the HBM sources.
An `ot_hdc_qwen_pc_lane_map` sits between each source's PC-local output and
the shared service. It routes every request to physical PC `sector[6:0]` and
returns responses to the original source bank by carrying that bank's 7-bit
lane number in the tag. This is needed for independent matrix scale bases:
gate/up scale base 456 sends source lanes 0 and 63 to physical PCs 72 and 7.
The same rule covers an embedding scale sector selected by `token>>4`.
The adopted G=6,144 KV streamer needs a 25-bit source tag
(`1+LWIN+$clog2(G)+3`, with LWIN=8). The shared service therefore uses a
32-bit client tag (7 lane bits + 25 source bits) and a 35-bit physical tag
after its 3-bit client ID. Elaboration rejects a narrower full-shape tag. Its
lane-mapping RTL passes an out-of-order two-PC response test. Physical tag
storage, cross-PC wiring and route are open implementation costs.
`ot_hdc_qwen_kv_pc_adapter` maps the existing exact FP8 logical-word sector
bridge to the same physical PC fabric, adding the bound user/layer KV base.
It checks every logical sector is inside the 262,144-sector layer page and
uses the adopted 25-bit G=6,144 KV response tag without truncation. The
bridge's half-sector read/modify/write logic and FP8 conversion stay as
implemented. The adapter holds a physical write until the shared PC service
returns its completion tag; request acceptance alone cannot advance the
bridge to a following read. An integrated bridge, adapter and PC-arbiter gate
delays write completion by five cycles and checks read-after-write bytes,
the retained half-sector, the exact physical transaction count and tags.
The inherited bridge permits one logical request at a time, so this is a
correctness path pending a bounded multi-outstanding scheduler and
shared-controller timing gate.

For shipped shape, one indivisible qkv K round consumes 128 code words and
one gate/up round consumes 512. A 512-word PC-local window therefore needs
48 MiB of code sectors per die. The current ISA cannot divide these K rounds
into 32-word chunks while preserving the accumulator order. The `lm_head`
can be divided between complete rounds, but its code and scale addresses
then advance by different strides. The opt-in `INT8_SCALE_WCS_BASE=1` mode
reuses the existing weight-op `me_wcs` field as an independent scale base;
the core descriptor forwards it as `wd_sbase` to the PC window. Reduced
programs keep the shared-base default. The four reduced split/base gates are
source-pinned in `results/rtl/qwen_int8_scale_base.json`. A full-shape chunked
emitter and package token gate using this mode are still pending. At 512 words
and 32 PCs, each PC tracks 49,152 code sectors, so the response tag must be
at least 17 bits including its code/scale selector.
The source-pinned area sensitivity in
`results/rtl/qwen_o4_hbm_weight_preflight.json` gives 16.7 mm² per die for
48 MiB at the architecture budget's modeled KV-buffer density. This is only
a density proxy. The PC bank macros, code/scale muxes, response tags, wiring,
power and route are unpriced, so the iso-area HBM comparison remains
conditional on their physical implementation.
Streaming weight sectors during an uninterrupted 512-cycle gate/up K round
barely changes this bound: the modeled four-stack die bandwidth provides
about 3,277 bytes per core cycle at the Qwen budget's 1.09864 GHz against
98,304 bytes consumed, so at least
46.4 MiB must still be prefetched before the round. A much smaller buffer
requires an exact FP32 accumulator continuation between K chunks or a
pipeline-wide stall. Neither exists in the adopted matvec, and either must
be bit-exact and routed before replacing the 48 MiB staging assumption.
The source also needs an operation-drain protocol or double buffering before
overlapping the next preload with current code and scale reads. Full-shape
bit-exact timing and placement are therefore open.

The byte-traffic and sector-address bounds are source-pinned in
`results/rtl/qwen_o4_hbm_weight_preflight.json` (separate handoff branch).
The PC-window RTL gate is source-pinned in
`results/rtl/qwen_o4_hbm_pc_window.json`.
The matched two-arm record is `results/rtl/qwen_int8_hbm_matched.json`.
