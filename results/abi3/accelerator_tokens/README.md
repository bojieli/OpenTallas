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
| `deepseek_v4_flash_hbm_p32` | DeepSeek-V4-Flash HBM | TA-DS-CHAT-1-P32 | 32 | `[13806, 345, 7472, 55560]` | **match** | 4,199.0 s |

All four deployments have produced at least one token the model's own reference
implementation produces for the same prompt. Both Qwen deployments decode four
tokens and agree with gold on all four, and with each other exactly. DeepSeek
HBM likewise completes four transactions and agrees with gold on all four.
DeepSeek ROM completes four transactions but diverges on its second generated
token.

## What is NOT established

**DeepSeek ROM multi-token correctness is not established.**

The current ROM capture completes prefill and all three decode transactions
without a trap, but its tokens are `[13806, 334, 305, 13806]` against oracle
prefix `[13806, 345, 7472, 55560]`: the first divergence is index 1. This is
now a numeric-correlation problem, not the old structural-decode failure.

The fresh HBM capture is post-`77f847c`: it completes prefill plus three decode
transactions with `SUCCESS`/`NONE` status and trap, producing
`[13806, 345, 7472, 55560]` exactly. It closes the former phase-extent failure;
it does not make the numerically divergent ROM continuation correct.

That HBM record declares its actual `target.node_count` as 32. Its top-level
`counters` are cluster totals; `node_counters` retains the engine work measured
at each `NODE_ID`. `make abi3-context-gate` checks the sparse-attention model
against every one of those 32 records and independently checks the aggregate.
It never divides a cluster total, because LINK, STATE, control and host work are
cluster-only and do not generally divide into node shares.

Also not established:

- **Sparse attention at a threshold.** The v2 context gate passes the current
  HBM record through context 35, but explicitly reports that neither the first
  window clipping at 129 nor the first index pruning at 2,052 was executed on
  the accelerator. The pass validates short-context counter scope and decode;
  it is not threshold evidence. The `TA-DS-CTX-*` ladder defines that regime.
- **Oracle-identical DeepSeek ROM generation beyond one token.** ROM executes
  the transactions but diverges numerically; HBM now matches all four retained
  oracle positions.
- **RTL.** These are functional-simulator runs. The shipped-deployment RTL
  co-simulation is `results/rtl/abi3_deployment_campaign.json`.
