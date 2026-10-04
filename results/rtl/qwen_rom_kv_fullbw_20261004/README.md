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
