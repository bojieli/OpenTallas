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
Both arms still read CROM constants and the reduced KV cache locally. This
serial per-operation preload timing is not a full-shape O4 bandwidth ratio,
controller/KV arbitration result, routed die frequency or chip throughput.
The shipped layer emitter also stores o/down post-TP BF16 row scales in
CROM. Those weight-scale ranges must be mapped to HBM before a full-shape
comparator is described as entirely HBM sourced; they are not exercised by
the reduced matrix-plus-embedding gate.

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
| O/down BF16 scales applied after TP reduction; other CROM weights, biases and norm constants | Local CROM in both arms | Classify every CROM range and fetch all weight-dependent ranges from HBM at the same arithmetic and rounding points. |
| RoPE tables or angle constants and program/descriptor metadata | Local constant/program images | Price storage and access, including any HBM-resident portions, without silently omitting traffic. |
| FP8 KV and scales, attention state and user/position metadata | Same local behavioural KV in both arms | Include actual HBM reads/writes, cache occupancy, four-stack-per-die arbitration with weights, and context limits. |
| Activation/accumulator SRAM, masks, queues, double buffers and DFlash speculative state | Reduced VM and package state only | Bind finite capacity, ports, fill/drain and any HBM spills; count both producer work and accepted output. |

Qwen has no DeepSeek Engram or index table; those belong to the separate V4.1
memory ledger. The proposed compute-cluster plan also requires a complete
finite-resource schedule, local placement and routed memory views before an
O4 rate or iso-area comparison can be promoted.

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
