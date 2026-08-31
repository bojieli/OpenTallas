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
| `deepseek_v4_flash_rom_p32` | DeepSeek-V4-Flash ROM wafer | TA-DS-CHAT-1-P32 | 32 | `[13806, 334, 305, 13806]` | **diverges at index 1** | 4,872.8 s |
| `deepseek_v4_flash_hbm_p32` | DeepSeek-V4-Flash HBM | TA-DS-CHAT-1-P32 | 32 | `[13806]` | **first token matches** | 3,379.0 s |

All four deployments have produced at least one token the model's own reference
implementation produces for the same prompt. Both Qwen deployments decode four
tokens and agree with gold on all four, and with each other exactly. DeepSeek
ROM completes four transactions but diverges on its second generated token;
the retained DeepSeek HBM capture stops at its first decode transaction.

## What is NOT established

**DeepSeek multi-token correctness is not established on either lane.**

The current ROM capture completes prefill and all three decode transactions
without a trap, but its tokens are `[13806, 334, 305, 13806]` against oracle
prefix `[13806, 345, 7472, 55560]`: the first divergence is index 1. This is
now a numeric-correlation problem, not the old structural-decode failure.

The retained HBM capture is older. It emits the oracle-identical first token,
then fails decode step 1 because `GROUPED_CONCAT` resolves `(257, 512)`
against a declared `(129, 512)`. Commit `77f847c` subsequently split the
prefill and decode extent bindings and added targeted regression coverage, but
no post-fix HBM execution capture has landed. The artifact therefore records
the old failure honestly; it must not be read as a verdict on the fixed source.

Also not established:

- **Sparse attention.** `window_size` is 128 and `index_topk` is 512; at 32
  prompt tokens, and at TA-DS-CHAT-1's full 104, no threshold is reached. The
  `TA-DS-CTX-*` ladder is what tests that regime.
- **Oracle-identical DeepSeek generation beyond one token.** ROM executes the
  transactions but diverges numerically; HBM still needs its post-fix rerun.
- **RTL.** These are functional-simulator runs. The shipped-deployment RTL
  co-simulation is `results/rtl/abi3_deployment_campaign.json`.
