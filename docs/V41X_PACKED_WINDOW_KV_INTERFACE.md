# V4.1 packed window KV boundary

The deployed window KV arithmetic quantizes a 512-element row in 16 blocks of
32. For each block, `tools/hdc_golden_v41.py:quant_fp8` computes the maximum
absolute FP32 value, floors it at `1e-4`, sets an E8M0 power-of-two scale to
`2^ceil(log2(amax / 448))`, clamps the scaled values to ±448, and rounds to
finite E4M3 with nearest-even. `qdq_fp8` then returns BF16 values to the
attention math. The stored row contract in
`runtime/prefill/v41_aux_kv_rows.py` is exactly 512 E4M3 code bytes, followed
by 16 E8M0 scale bytes in block order. Codes `0x7f` and `0xff`, and scale
`0xff`, are poison. These 528 payload bytes use 17 consecutive 32-byte HBM
sectors: sectors 0–15 contain codes, sector 16 has 16 scale bytes and 16
unwritten padding bytes. The row pitch is 544 bytes, matching
`runtime/prefill/v41_hbm_placement.py`.

`ot_chip_v41x_window_row_codec` exposes that layout without changing the
existing die prefetch interface. It takes the packed row, absolute position,
window-region sector base/length, and sector or element index. It returns one
sector address, bytes and strobe, plus one exactly decoded FP32 element. The
decode fails closed on poison and FP32 overflow. The 21-bit position is checked
against 1,048,576; its low seven bits choose one of the 128 ring slots. The
30-bit sector address and region end are checked before a transaction; no
arithmetic wrap is allowed. A complete ring uses 2,176 sectors, or 69,632 B,
per window layer per die. A new absolute position overwrites the same slot
after 128 positions; an external absolute-position tag must reject stale reads.

The current core/KVD writes individual FP32 lanes. That stream cannot
reconstruct the original packed bytes. Even one exact decoded value is
ambiguous: E4M3 code `0x38` with E8M0 scale `0x7f` and code `0x30` with scale
`0x80` both decode to 1.0. More importantly, a block's scale depends on all
32 **pre-quantized** inputs. The integration must accumulate a full block of
those inputs, quantize once in the golden's order, then commit its 32 codes
and scale together. An update to an existing block must retain those original
inputs or define a new explicit requantization rule. It must drain that commit
before a later prefetch of the same sector and refetch an invalidated staged
row. This standalone codec neither supplies that quantizer nor proves the
prefetch/arbiter ordering or timing; those are separate integration gates.

`python -m tools.rtl_chip_v41x_window_row_codec` runs an Icarus testbench
against exact rational reference decoding, spanning every sector, scale
boundaries, 1M ring bounds, address wrap, poison, overflow, and a two-row
logical read-after-write sector store. Its source-pinned result is
`results/rtl/chip_v41x_window_row_codec.json`. This gate validates only the
packed window row. Compressed main KV (288 B) and index keys (68 B) have
separate formats and are outside this module.
