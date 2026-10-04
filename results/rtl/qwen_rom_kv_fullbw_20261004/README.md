# Qwen3-8B ROM: full-bandwidth KV path (4 HBM3E stacks a die, STREAM4)

Owner rule: every HBM load reaches >= 90 % of the attached stacks' peak.  Qwen ROM weights are on-die ROM; the only
HBM load is the KV window (FP8, 2 KV heads a die, 4 MiB a layer at P = 8191).

Peak a die: 4 stacks x 32 PCs x 32 B / 1.024 ns (controller CK/2) = 4.000 TB/s = 104.2 sectors a 1.2 GHz core cycle.

## Standalone service bench (standalone/, final RTL with the hardened per-tile landing merge)

`rtl/test/qwen_rom_runtime/realmem/tb_qwen_rt_kv_stream4.{sv,cpp}`: ot_qwen_rt_kv_stream4_service +
ot_qwen_hbm_stream4_ack (4 x ot_hbm_r14_stream_stack RTL, WR_EN=1, picosecond DRAM checker, 0 violations), every
slice word of the 1,536 tiles and the written-back token K/V checked against an independent map.  15/15 PASS.

| case | fill cycles | sectors/cycle | TB/s | % of 4.000 TB/s peak |
|---|---|---|---|---|
| ISO P8191 (whole window, first-sector latency included) | 1,353 | 96.88 | 3.720 | 93.0 % |
| ISO P4095 | 715 | 91.66 | 3.520 | 88.0 % (latency share larger) |
| before (REAL_MEM, 1 stack, realmem-ctx8k P8191 L0) | 9,893 | 13.25 | 0.509 | 12.7 % |

Cross-layer prefetch (early_go: next layer's stream released at kv_free) + posted write-back:
CHAIN_P8191_early_posted B fill exposed after start = 0 (kv_ok 65 cycles after start vs 1,740 without the straps);
with only 400 MLP cycles the exposure is 912 = 1,312 - 400.

Landing: per-tile merge `rtl/hdc/kv/ot_qwen_kv_land_merge.sv` (<= 12 sources a tile under the striped map); lockstep
vs the service's rule: 200,000 random cycles, 0 mismatches (standalone/land_merge_lockstep.log).

## Runtime, one layer at P8191 (runtime_P8191/, exact vs the GPU golden realmem-ctx8k/gold/P8191)

TP4 REAL_MEM runtime with the STREAM4 die (tools/qwen_rom_rt_token_stream4_w12.py, AR256, WBW 4), X of all 4 dies and
the token K/V written back to HBM bit-exact.  The whole 8K history (8,191 positions, 131,072 sectors a die) is read with
no fault (the one-stack HBM_STREAM path faulted at P >= 2048; P1023/P4095/P8191 bench cases and this run cover it).

| L0 isolated, P8191 | cycles | fill cycles | sectors/cycle | TB/s | % of 4-stack peak |
|---|---|---|---|---|---|
| REAL_MEM one stack (before) | 14,574 | 9,893 | 13.25 | 0.509 | 12.7 % |
| STREAM4 (this) | 6,468 | 1,348 | 97.23 | 3.734 | 93.4 % |
| KV_IDEAL (compute bound) | 5,290 | - | - | - | - |

## Tagged near-row read port on the SAME controllers / array (tagged/; for the combined STREAM4 die)

Additive successor backend `rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv` (top `ot_qwen_hbm_stream4_tagged`; the
`ot_qwen_hbm_stream4_ack` port list unchanged plus `t_*`), served by the same 4 x `ot_hbm_r14_stream_stack`
(new default-off `AQ_RD=1`: tagged reads enter each pseudo-channel's write-back queue = access queue, in order;
background to the stream with a 64-cycle starvation bound) and the same `mem`. Native hook
`tools/runtime/qwen_combined/stream4_tagged_rows_hook.cpp` (`bool qwen_stream4_wire_native_tagged_rows(Vdie&,Vhbm&)`,
pin wiring only; compile/link checked against the real Vhbm: tagged/hook_check.log).

Bench (`tb_qwen_rt_kv_stream4_tagged.sv` + `tb_qwen_rt_kv_stream4.cpp -DTAGGED`, t_clk 1.0 GHz beside the
1.2 GHz core, 4 clients, 16-sector reads of the current layer's history, every beat checked against `mem`):

| case | stream fill | stream % of 4.000 TB/s | tagged during fill | total % | tagged beats exact | DRAM violations |
|---|---|---|---|---|---|---|
| TAG_ISO_P8191_r5  | 1,387 cyc | 90.7 % | 0.072 TB/s | 92.5 % | 3,488 / 3,488 | 0 |
| TAG_ISO_P8191_r15 | 1,394 cyc | 90.3 % | 0.091 TB/s | 92.5 % | 5,520 / 5,520 | 0 |
| TAG_ISO_P8191_r30 | 1,393 cyc | 90.3 % | 0.092 TB/s | 92.6 % | 5,392 / 5,392 | 0 |

Slices and token write-backs exact in all; TAG_NEG_write (read-only port) and TAG_NEG_other_layer (not the current
descriptor row) fault as required.

## Stream-aware refresh pull-in (pullin/)

The prefetched (early_go) fill depended on the refresh phase: 1,310 .. 2,064 cycles (63 .. 100 % of peak) with the
strict REFpb schedule (forced REFpb of banks the stream needs). `ot_hbm_r14_stream_pc PULLIN=N` (default 0, lockstep
identical to main on 3 x 200k cycles) refreshes up to N REFpb ahead while not reading and skips that many slots
while reading. Phase sweep (pullin/phase_sweep.txt): worst B fill 2,064 -> 1,464 (N=8) -> 1,398 (N=16, 90.0 %),
typical 1,307 (96.3 %); 0 DRAM violations; full regression with N=16 15/15 PASS (pullin/).
