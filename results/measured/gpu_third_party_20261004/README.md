# GPU decode baselines from third-party publications (2026-10-04)

> OWNER RULE 2026-10-04: speculative-decoding acceptance and the DeepSeek-V4.1 GPU decode baseline must come from PUBLISHED THIRD-PARTY sources (MLCommons, LMSys/SGLang, vLLM, model vendors, NVIDIA/AMD, ...), never from our own measurement. OWNER CORRECTION: cite this registry instead of re-researching.

THIRD-PARTY PUBLISHED figures (not our measurements) - the directory sits under results/measured only because that is the repo's GPU-baseline area. Our own H100 runs stay in results/measured/h100_nvls_20261004/.

## DeepSeek-V4.1 per-user decode (published)

| GPU | tok/s per user | Context | Source | Mismatch |
|---|---|---|---|---|
| H200 | 240 | 900K | `nvls:lmsys_dsv4_day0` | DeepSeek-V4-Flash (V4.1 not published); speculation most likely ON (EAGLE-style MTP; Figure 2 does not state it); SGLang Day-0, TP4, single batch, OSL 4096 |
| B200 | 180 | 900K | `nvls:lmsys_dsv4_day0` | DeepSeek-V4-Pro 1.6T / 49B active (Flash is 13B active); speculation most likely ON; TP8, single batch |
| B300 | 383.7 | not stated (repro: 256 in / 256 out) | `acc:LMSYS` | DeepSeek-V4-Pro + DSpark accept ~5; short context |
| H100 | [40, 50] |  | `nvls:sglang_disc_39791` | unsupported target (user report); context not stated |

Gap: No published DeepSeek-V4.1-Flash per-user decode figure at 1M on any GPU was found (NVIDIA's Dynamo V4.1 recipe explicitly carries no performance claim). The closest published long-context figures are V4-Flash on H200 (240 tok/s at 900K) and V4-Pro on B200 (180 tok/s at 900K).

## Qwen3-8B (target 8K context)

| Mode | GPU | tok/s per user | Context / drafter | Source |
|---|---|---|---|---|
| no_spec | B200 | 230 | MATH-500 (short)  | `new:dflash_table3_table4` |
| no_spec | H20 | 151.81 | <=1,024 out  | `new:angelslim_qwen3_eagle3_card` |
| no_spec | H200 | [140.14, 234.95] | NIM 8B-class, BF16/FP8  | `calib:nim_h200` |
| spec | B200 | 1175 | MATH-500 (short) DFlash block 16, tau 8.01 | `new:dflash_table3_table4` |
| spec | H20 | 257.52 |  EAGLE-3 k=2, tau 1.99 | `new:angelslim_qwen3_eagle3_card` |

Gaps: No published Qwen3-8B per-user decode figure at ~8K context was found; the 8K points remain our measured H100 runs (TP1 FP8 180, TP8 FP8 299 tok/s; results/measured/h100_nvls_20261004). No published Qwen3-8B speculative per-user figure at 8K context was found.

## Corrections

- results/measured/h100_nvls_20261004/README.md says 'DeepSeek-V4.1-Flash H200 TP4 266 tok/s (no speculation), 30K prefix': the source is DeepSeek-V4-Flash (not V4.1), 266 is the 4K end of a 4K-900K sweep (240 at 900K), and speculation was most likely on. The Dynamo V4.1 recipe it also cites carries no performance figure.
