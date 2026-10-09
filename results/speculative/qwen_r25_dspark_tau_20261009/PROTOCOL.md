# Qwen3-8B DSpark acceptance (tau) on the owner's 6-class blend, for MTP on r25: pre-registered protocol

This protocol was written on 2026-10-09 (stream qwen-hbm-unify), before any result of this run existed. Anything that contradicts it is reported as it comes out. Background: the owner decided on 10-09 at 00:30 that Qwen on r25 uses DSpark at 4 positions, after its tau is measured on the 6-class blend.

## Models
- **Target.** Qwen/Qwen3-8B @ b968826d, the released BF16 weights, computed in FP32 on CPU (an exact upcast of the weights).
  - Deviation: the r25 deployment target is the O4 INT8 contract. That contract agrees with BF16 on top-1 95.7 % of the time (results/quality/qwen3_8b_weight_format_search.json).
  - The local GPU is unavailable (Xid 175/154, reset required), which is why the run is on CPU.
- **Drafter.** deepseek-ai/dspark_qwen3_8b_block7 @ 03326e50, the released BF16 weights, unchanged (memory draft-must-stay-exact). It runs through DeepSpec @ 005e03b8, as in tools/qwen_rom_dspark_tau.py.

## Configuration
- **Primary:** S = 7 (the block as trained), truncated to B - 1 = 3 drafts, with B = 4 (3 drafts + bonus; the r25 verify is p = 4). The key is `tau_bf16_S7_B4`.
- **Secondary:** S = 3, the block shortened. This changes the drafter's computation, so it is reported only, never adopted. The key is `tau_bf16_S3_B4`.
- B = 2..8 at S = 7 is recorded too.
- Decoding is greedy (tau is exact under a lossless greedy replay).
- `max_new_tokens` = min(the prompt's own value, 512). The 512 cap matches the DS qualified protocol.

## Classes (the owner's 6-class mix; every class measured, none taken from a publication)

| Class | Prompts (results/speculative/raw/prompts.jsonl.gz unless stated) |
|---|---|
| chat | chat_mt_bench (12, first turn) |
| reasoning | reasoning_math500 (24, thinking on) |
| coding | reasoning_humaneval (24) |
| agentic | agentic_swe_agent + agentic_tau_bench + agentic_mind2web (72) |
| assistant_fc | agentic_bfcl + agentic_json_mode (48) |
| creative | the 3 creative prompts built into tools/qwen_rom_dspark_tau.py (low n, flagged) |

## Statistic
- Per class: the median of per-prompt tau, plus the pooled tau.
- **Blend:** the equal-weight harmonic mean of the six class medians, greedy. This is the DS blend_owner6 definition.
- The envelope (lowest and highest class) is reported beside the blend.
