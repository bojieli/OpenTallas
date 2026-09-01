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
| `deepseek_v4_flash_rom_p32` | DeepSeek-V4-Flash ROM wafer | TA-DS-CHAT-1-P32 | 32 | `[13806, 345, 7472, 55560]` | **match** | 649.9 s |
| `deepseek_v4_flash_hbm_p32` | DeepSeek-V4-Flash HBM | TA-DS-CHAT-1-P32 | 32 | `[13806, 345, 7472, 55560]` | **match** | 4,476.3 s |

All four deployments have produced at least one token the model's own reference
implementation produces for the same prompt. Both Qwen deployments decode four
tokens and agree with gold on all four, and with each other exactly. Both
DeepSeek deployments likewise complete four transactions, agree with gold on
all four, and agree with each other position for position.

## Historical numeric localization and closure

The retained bisectors are historical diagnostic early-stop runs from before
the two ROM fixes: they commit no transaction and establish no generated-token
result. Every ROM/HBM lane below records NumPy 2.2.6, scipy-openblas 0.3.29, and
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
  `[6,4096]` per prompt row. That localization led to the routed-span fix: ROM
  now preserves the full `top_k * span_tokens` batch through dispatch, QDQ,
  routed GEMMs, SwiGLU and route weighting. The fixed ROM source-324/reducer
  result matches HBM at the formerly divergent row.

The first post-routed-fix four-token run then isolated a decode-only state
addressing defect. A compressed layer loop used the correct per-iteration state
stride but discarded its deployment-global starting slot, aliasing layer 2 and
both representatives of the period-2 body onto earlier cache slots. The ROM
lowering now retains that static base. A synthetic alternating-stack regression
checks the representative layer against the state-view slot, and the production
deployment admits with layer-state bases 0, 2, 3 and 4 for its three compressed
runs. The governed token capture is the end-to-end closure: all four tokens now
match the oracle and HBM.

`deepseek_v4_reference_boundaries_p32.json` independently links the refreshed
lane artifact by SHA-256 and records the vendor comparison and layer-0 audit.
The vendor lane is useful implementation context, not a replacement numeric
contract.

## What is NOT established

**DeepSeek ROM correctness is established only through the governed four-token
horizon.**

The current ROM capture completes prefill and all three decode transactions
without a trap and produces `[13806, 345, 7472, 55560]`, identical to the
oracle prefix and the retained HBM capture. It compares four positions, reports
`agreement: true`, and has no divergence index or legitimacy problem.

The fresh HBM capture uses deployment digest
`45e2b872b4db5ded09e580774bd413f5daa0a9f3c4608f1aa222f9323a259dcf`.
It completes prefill plus three decode transactions with `SUCCESS`/`NONE`
status and trap, producing `[13806, 345, 7472, 55560]` exactly. It closes the
former phase-extent failure. The corresponding now-matching ROM deployment
digest is
`c8c03f1a7f579e8dfb892626cd2842ef88d624f086a5b55bd0b245f1ca515824`.

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
- **Oracle-identical DeepSeek generation beyond four tokens.** Both accelerator
  targets match all four retained positions, but this capture says nothing
  about token 5 or later.
- **RTL.** These are functional-simulator runs. The shipped-deployment RTL
  co-simulation is `results/rtl/abi3_deployment_campaign.json`.
