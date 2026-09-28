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
sector at `scale_base + w`. The module fully preloads an ISA weight operation
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
ROM weights take 281,485 cycles; the behavioural two-PC HBM source takes
421,965 cycles (+140,480, +49.9%). This delta measures the reduced serial
operation preload with two 32-byte sectors per code word. It is not a
full-shape bandwidth ratio or chip throughput measurement.

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
The source also needs an operation-drain protocol or double buffering before
overlapping the next preload with current code and scale reads. Full-shape
bit-exact timing and placement are therefore open.

The byte-traffic and sector-address bounds are source-pinned in
`results/rtl/qwen_o4_hbm_weight_preflight.json` (separate handoff branch).
The PC-window RTL gate is source-pinned in
`results/rtl/qwen_o4_hbm_pc_window.json`.
The matched two-arm record is `results/rtl/qwen_int8_hbm_matched.json`.
