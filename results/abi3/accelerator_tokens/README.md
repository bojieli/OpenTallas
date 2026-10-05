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
| `qwen3_8b_rom_chat1` | Qwen3-8B ROM | TA-QW-CHAT-1 | 93 | `[1654, 525, 2661, 1447]` | **match** | 54.5 s |
| `qwen3_8b_hbm_chat1` | Qwen3-8B HBM | TA-QW-CHAT-1 | 93 | `[1654, 525, 2661, 1447]` | **match** | 50.0 s |
| `deepseek_v4_flash_rom_p32` | DeepSeek-V4-Flash ROM wafer | TA-DS-CHAT-1-P32 | 32 | `[13806, 345, 7472, 55560]` | **match** | 684.4 s |
| `deepseek_v4_flash_hbm_p32` | DeepSeek-V4-Flash HBM | TA-DS-CHAT-1-P32 | 32 | `[13806, 345, 7472, 55560]` | **match** | 4,887.9 s |

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

## Re-take on the current lowering (2026-09-06): the ROM array

`deepseek_v4_flash_rom_array_p32.json` was re-taken because the lowering had
moved three times under it -- AM-E9 v2, the item-22 `DMA.SCATTER` dtype fix and
item 26 (the KV arena in SRAM) -- and nobody had checked whether the tokens
survived. Seven of its 55 bound sources had moved.

The bundle was rebuilt from committed source at `a002283` in a pinned clean
worktree, not taken from `build/abi3` as found. The rebuilt kernel IR and
workload reproduce the retained record's digests exactly
(`b92fadb1…`, `ca3c64c0…`), and the published bundle's `deployment_sha256` is
`5065fab0…` -- the digest `results/abi3/rom_schedule_checks.json` certifies for
`deepseek-v4-flash-rom-array-32`. The retained record bound `a3cc19ba…`, which
is no longer shipped.

What the lowering change actually is, measured by decoding both descriptor
tables: **3,423 -> 3,159 descriptors, all of it SCHEDULE, 347 -> 83.** Every
other descriptor type, all 430 memory objects, the 1,344 instructions, the
4,206,473 proved retired work, the capability digest and the topology digest
are unchanged.

What the run produced: the same ids `[13806, 345, 7472, 55560]`, the same
decoded text and `token_ids_sha256`, `agreement: true` over 4 compared
positions with `first_divergence_index` null, no legitimacy problem -- and
**all 61 architectural counters, the four token-commit ticks and the per-step
retired counts identical to the retained record**, node counters included.

**The two walls in this directory are not comparable.** The re-take took
16,850.9 s against the retained 9,349.6 s, and the difference is thread count,
not work: `numba_threads` is 8 here and 32 there, while `numba_calls` (18,656)
and `numba_scalar_product_adds` (375,272,767,488) are identical. The kernel
parallelises only across independent outputs and keeps every reduction serial
in k, so its thread count cannot change a value -- but it is part of the
recorded implementation identity, so `runtime.evidence.check_comparable`
refuses a ROM-versus-HBM comparison across records taken at different counts.
The HBM twin must therefore be re-taken at 8 threads before the pair can be
compared again.

**The HBM twin is NOT re-taken.** Its run was killed by the host OOM killer at
2026-09-06T20:57:35Z with `anon-rss` 73.9 GiB, after prefill and one decode, on
a box whose physical lane held about 111 GiB of OpenROAD at the time. That is
the same constraint the Makefile states in words: this host has no headroom for
two DeepSeek numerical lanes at once. The retained
`deepseek_v4_flash_hbm_p32.json` therefore still binds `0da49f94…`, while
`results/abi3/hbm_deepseek_deployment_certificate.json` certifies `d8328615…`
-- and a rebuild from `a002283` reproduces `d8328615…` exactly, so only the
execution is missing. The command is `tools/run_accelerator_tokens.py
--backend hbm_sram --capability
configs/hardware/abi3_capability/hbm_sram_cluster_32.json` on the same kernel
IR, workload, reference and `--expert-numeric-path fp8 --max-new-tokens 4`,
under an affinity mask of exactly 8 CPUs so that `OPENBLAS_NUM_THREADS=8` is
honoured rather than clamped.

Consequence for the pair: `tools/build_comparison_report.py` refuses both
retained records today for source-currency, so
`results/abi3/comparison_deepseek_rom_array_vs_hbm.json` is not regenerable
until the HBM leg is re-taken; that was already true before this re-take.

## What is NOT established

**DeepSeek ROM correctness is established only through the governed four-token
horizon.**

The current ROM capture completes prefill and all three decode transactions
without a trap and produces `[13806, 345, 7472, 55560]`, identical to the
oracle prefix and the retained HBM capture. It compares four positions, reports
`agreement: true`, and has no divergence index or legitimacy problem.

The fresh HBM capture uses deployment digest
`2943197b3055d6198899d402efd927810cd307c09287f9d250b1b1afb2695275`.
It completes prefill plus three decode transactions with `SUCCESS`/`NONE`
status and trap, producing `[13806, 345, 7472, 55560]` exactly. It closes the
former phase-extent failure. The corresponding now-matching ROM deployment
digest is
`fa907792d8eb73ec1237525468581e47945a9077e5a247f4f88c43fbb5042394`.

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
