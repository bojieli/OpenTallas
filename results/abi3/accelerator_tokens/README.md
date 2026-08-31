# Accelerator-side token captures

Produced by `tools/run_accelerator_tokens.py` (`make abi3-tokens`). One
deployment, one workload, one external reference oracle per run: the tool
lowers, admits, executes on the functional device with the real engines, and
compares against the oracle's gold for the *same* workload.

The oracle result is selected by workload id **and** its `workload_digest` must
equal the workload's own. That guard exists because an earlier ad-hoc driver
scored a 32-token run against `TA-DS-CHAT-1`'s 104-token gold and reported a
mismatch that meant nothing — the two prompts ask different questions.

## Results

| capture | deployment | workload | prompt | generated | gold prefix | wall |
|---|---|---|---:|---|---|---:|
| `qwen3_8b_rom_chat1` | Qwen3-8B ROM | TA-QW-CHAT-1 | 93 | `[1654, 525, 2661, 1447]` | **match** | 124.7 s |
| `qwen3_8b_hbm_chat1` | Qwen3-8B HBM | TA-QW-CHAT-1 | 93 | `[1654, 525, 2661, 1447]` | **match** | 129.6 s |
| `deepseek_v4_flash_rom_p32` | DeepSeek-V4-Flash ROM wafer | TA-DS-CHAT-1-P32 | 32 | `[13806]` | **first token matches** | 2,458.3 s |
| `deepseek_v4_flash_hbm_p32` | DeepSeek-V4-Flash HBM | TA-DS-CHAT-1-P32 | 32 | `[13806]` | **first token matches** | 3,379.0 s |

All four deployments have now produced a token the model's own reference
implementation produces for the same prompt. Both Qwen deployments decode four
tokens and agree with gold on all four, and with each other exactly.

## What is NOT established

**DeepSeek multi-token decode fails on both lanes**, at decode step 1, and the
two lanes fail *differently*:

```
ROM: GROUPED_CONCAT output view 1417 dims (129, 512) differ from the
     axis-0 concatenation (137, 512)
HBM: GROUPED_CONCAT output view 1268 dims (129, 512) differ from the
     axis-0 concatenation (257, 512)
```

The join is `current span + committed 128-row window + valid compressed
prefix`. At decode the span is 1, so the declared output extent
`attention_rows_ratio4` binds to `1 + 128 + 0 = 129` — it took the *span's*
group count where it needed the *accumulated context's*. The compressed KV
state holds 8 groups from the 32 prefilled tokens (32/4), which is ROM's 137.
HBM instead resolves that operand to 128, the sliding-window size, giving 257.

So the extent is wrong on both lanes, wrong in two different ways, and the two
backends disagree with each other about the size of the same resource. The
frontend has two symbol families with identical bounds and different meanings —
`span_groups_ratioN` and `context_groups_ratioN` — and the binding does not
keep them apart.

Prefill is unaffected (span equals the context, so the two coincide), which is
why every single-token result above passes and why this went unseen until a
second decode step was attempted.

Also not established:

- **Sparse attention.** `window_size` is 128 and `index_topk` is 512; at 32
  prompt tokens, and at TA-DS-CHAT-1's full 104, no threshold is reached. The
  `TA-DS-CTX-*` ladder is what tests that regime.
- **DeepSeek beyond one token**, per the defect above.
- **RTL.** These are functional-simulator runs. The shipped-deployment RTL
  co-simulation is `results/rtl/abi3_deployment_campaign.json`.
