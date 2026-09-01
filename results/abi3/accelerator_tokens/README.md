# Accelerator-side token captures

Produced by `tools/run_accelerator_tokens.py` (`make abi3-tokens`). One
deployment, one workload, one external reference oracle per run: the tool
lowers, admits, executes on the functional device with the real engines, and
compares against the oracle's gold for the *same* workload.

The oracle result is selected by workload id **and** its `workload_digest` must
equal the workload's own. That guard exists because an earlier ad-hoc driver
scored a 32-token run against `TA-DS-CHAT-1`'s 104-token gold and reported a
mismatch that meant nothing — the two prompts ask different questions.

The runner establishes the governed blocked-GEMM default before NumPy loads:
`OMP_NUM_THREADS=8`, `OPENBLAS_NUM_THREADS=8`, and `MKL_NUM_THREADS=8`. An
explicit caller override remains authoritative, but it produces a different
recorded implementation identity and therefore a different evidence run.

## Results

| capture | deployment | workload | prompt | generated | gold prefix | wall |
|---|---|---|---:|---|---|---:|
| `qwen3_8b_rom_chat1` | Qwen3-8B ROM | TA-QW-CHAT-1 | 93 | `[1654, 525, 2661, 1447]` | **match** | 124.7 s |
| `qwen3_8b_hbm_chat1` | Qwen3-8B HBM | TA-QW-CHAT-1 | 93 | `[1654, 525, 2661, 1447]` | **match** | 129.6 s |
| `deepseek_v4_flash_rom_p32` | DeepSeek-V4-Flash ROM wafer | TA-DS-CHAT-1-P32 | 32 | `[13806, 334, 305, 13806]` | **diverges at index 1** | 1,347.3 s |
| `deepseek_v4_flash_hbm_p32` | DeepSeek-V4-Flash HBM | TA-DS-CHAT-1-P32 | 32 | `[13806, 345, 7472, 55560]` | **match** | 4,476.3 s |

All four deployments have produced at least one token the model's own reference
implementation produces for the same prompt. Both Qwen deployments decode four
tokens and agree with gold on all four, and with each other exactly. DeepSeek
HBM likewise completes four transactions and agrees with gold on all four.
DeepSeek ROM completes four transactions but diverges on its second generated
token.

## Current numeric localization

The retained bisectors are diagnostic early-stop runs: they commit no
transaction and establish no generated-token result.  Every ROM/HBM lane below
records NumPy 2.2.6, scipy-openblas 0.3.29, and
`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=8`, matching the governed
token captures' blocked-GEMM identity.

- `deepseek_v4_layer00_norm_input_bisect.json` compares 192 terminal operator
  outputs and two traced RMSNorm inputs.  Both accelerator lanes agree exactly
  on the input, checkpoint weight, frozen-contract output, and next boundary.
  The separate vendor audit differs at 3 of 131,072 BF16 output elements in one
  row, with maximum absolute difference 0.000244140625; the released source
  does not freeze its backend reduction tree or reciprocal-square-root
  implementation.
- `deepseek_v4_layer02_operator_bisect.json` compares 253 terminal outputs and
  three traced state/QDQ inputs with no payload difference.  This closes the
  older boundary-3 mismatch under the governed implementation identity.
- `deepseek_v4_lane_activation_bisect.json` compares 44 logical boundaries.
  ROM and HBM are byte-identical through boundaries 0--31 and first differ at
  boundary 32, the input to layer 4 produced by layer 3.
- `deepseek_v4_boundary32_operator_bisect.json` compares 193 terminal layer-3
  outputs and localizes the first difference to `EXPERT_REDUCE` source kernel
  331, invocation 2.  All 32 shared-expert inputs match.  Of the routed inputs,
  only invocation 2 differs, and only selected-expert slice 2 of its six input
  slices differs.  The reducer is therefore propagating one upstream routed
  expert result rather than creating the mismatch locally.
- `deepseek_v4_routed_chain_input_bisect.json` traces sources 317--324.  A
  shape-normalized inspection aligns ROM's row loop with HBM's batch and finds
  all 2,368 comparable leading input slices equal: routing IDs, normalized
  inputs, dispatch/QDQ data, gate/up results, SwiGLU and route weights, weighted
  activations, and the FP8 activation plus expert IDs entering the routed down
  projection.  The first semantic difference is its output at global selected
  row 14 (prompt row 2, selected-expert slice 2).  HBM lowers that source to a
  `[192,128]` local projection plus collection operators while ROM emits
  `[6,4096]` per prompt row.  The trace localizes the remaining fault boundary
  to that down-projection/collection path; its physically sharded weight views
  do not directly distinguish weight mapping, shape-dependent GEMM association,
  and collection ordering.

`deepseek_v4_reference_boundaries_p32.json` independently links the refreshed
lane artifact by SHA-256 and records the vendor comparison and layer-0 audit.
The vendor lane is useful implementation context, not a replacement numeric
contract.

## What is NOT established

**DeepSeek ROM multi-token correctness is not established.**

The current ROM capture completes prefill and all three decode transactions
without a trap, but its tokens are `[13806, 334, 305, 13806]` against oracle
prefix `[13806, 345, 7472, 55560]`: the first divergence is index 1. This is
now a numeric-correlation problem, not the old structural-decode failure.

The fresh HBM capture uses deployment digest
`45e2b872b4db5ded09e580774bd413f5daa0a9f3c4608f1aa222f9323a259dcf`.
It completes prefill plus three decode transactions with `SUCCESS`/`NONE`
status and trap, producing `[13806, 345, 7472, 55560]` exactly. It closes the
former phase-extent failure; it does not make the numerically divergent ROM
continuation correct. The corresponding ROM deployment digest is
`c438881661300ba53d0432fa5d87a0b9f631671fef165a828123ac0b53815650`.

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
