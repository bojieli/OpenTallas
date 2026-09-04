# Qwen3-8B exact-8K heterogeneous Gate-1 campaign handoff

**Campaign:** `qwen3-heterogeneous-exact-8k-v1`

**ABI:** 3.0, unchanged

**Workload-set ID:**
`4f3e2e3c3dd06683e4aa9374d317dbbbb9227ce90815cf6dc9fc93f195295bea`

**Current status:** tokenizer-authenticated preparation; eight production
external oracles are pending. No model or accelerator was run by this build,
no batch request is runnable, Gate 1 is not passed, and there is no TPOT claim.

## Frozen workload set

The authoritative manifest is
`configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1/manifest.json`.
Every lane contains exactly 8,000 legal prompt-token IDs, uses
`max_new_tokens = 256`, decodes and re-encodes byte-for-byte through the pinned
Qwen tokenizer, and has a unique sequence ID, workload ID, workload digest,
prompt-token digest, and file identity. The profiles are exact nested prefixes:

| Lane | Class | Authenticated existing source | Workload ID | First profile |
|---:|---|---|---|---:|
| 0 | natural chat | ROM `arithmetic` question | `TA-QW-8K-1` | B=1 |
| 1 | reasoning | ROM `reasoning`, thinking enabled | `TA-QW-8K-REASON-1` | B=2 |
| 2 | agentic/tool | TerminalBench `hello-world`, official bash tool | `TA-QW-8K-AGENT-HELLO-1` | B=4 |
| 3 | stress | established repeated `<|im_start|>` IDs | `TA-QW-8K-STRESS-256-1` | B=4 |
| 4 | natural chat | ROM `geography` question | `TA-QW-8K-GEOGRAPHY-1` | B=8 |
| 5 | natural chat | ROM `science` question | `TA-QW-8K-SCIENCE-1` | B=8 |
| 6 | agentic/tool | TerminalBench `fix-permissions`, official bash tool | `TA-QW-8K-AGENT-PERMISSIONS-1` | B=8 |
| 7 | natural chat | ROM `practical_advice` question | `TA-QW-8K-PRACTICAL-1` | B=8 |

Natural, reasoning, and agent prompts prepend the maximum deterministic
character prefix of the authenticated public-domain *Moby-Dick* corpus to the
canonical final user request, then render the complete conversation through
the authenticated official Qwen template. Agent lanes retain the exact shared
`SYSTEM_PROMPT`, `BASH_TOOL`, TerminalBench commit, suite ID, Docker/test/task
hashes, and runtime-file hashes. The stress lane retains the established 8,000
copies of legal token ID 151644; its workload ID changed because the historical
stress case had a 32-token cap.

A physical heterogeneous batch containing an agent lane validates the opening
tool-capable model turn only. It does not by itself prove the later sandbox
actions or a complete closed-loop TerminalBench episode. Closed-loop episode
acceptance remains a separate requirement.

## Contracts and refusal boundary

- `schemas/abi3/qwen3_heterogeneous_workload_set_v1.schema.json` defines the
  content-addressed preparation set, per-lane pending/frozen oracle binding,
  and exact B=1/2/4/8 views.
- `schemas/abi3/qwen3_heterogeneous_reference_set_v1.schema.json` admits a
  production-ready reference set only after all eight singleton oracle files
  validate. A partial or pending set has no production-ready representation.
- `compiler/workloads/qwen3_heterogeneous_8k.py` reconstructs the workloads and
  validates sources, content hashes, legal IDs, tokenizer round trips,
  uniqueness, profile nesting, singleton reference selection, complete
  checkpoint preflight, exact workload bindings, decoded text, and the terminal
  rule.
- `tools/build_qwen3_heterogeneous_campaign.py` is a tokenizer-only,
  create-once builder.
- `tools/check_qwen3_heterogeneous_campaign.py` validates preparation and can
  create-once freeze the eight-oracle reference set. Missing one oracle fails
  closed.

An admissible oracle file must contain exactly one result and its producer must
record exactly one `selected_workload_ids` entry matching that lane. The v3
production profile must have been explicitly requested with the integrated
manifest, one `--only`, and the lane's create-once output path. It binds the
checkpoint lock, reconstructed campaign and manifest file, workload-set ID,
lane index/sequence/category/source, campaign workload index, exact workload
bytes/digest, prompt-token digest and length, tokenizer, numeric/prefill
association, and explicit production launch. Its output must contain legal
non-padding IDs and either:

1. end at the first official EOS, retaining that EOS and no earlier EOS; or
2. contain exactly 256 tokens with no official EOS.

The raw and special-token-stripped decoded strings must exactly reproduce the
retained output IDs. The reference artifacts are external comparators; even a
complete reference set is not accelerator execution and does not pass Gate 1.
The singular homogeneous `comparison_contract_v1` is explicitly forbidden for
this campaign. The existing heterogeneous ABI 3.0 request and execution schemas
remain the downstream boundary.

## Operator commands

Reproduce the committed preparation set in a new create-once directory:

```bash
python3 tools/build_qwen3_heterogeneous_campaign.py \
  --output build/workloads/qwen3-heterogeneous-exact-8k-v1
```

Validate the committed preparation set:

```bash
python3 tools/check_qwen3_heterogeneous_campaign.py
```

Generate one production oracle at a time with this exact form (shown for lane
0):

```bash
python3 tools/run_qwen3_reference_oracle.py \
  --heterogeneous-gate-1-production \
  configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1/manifest.json \
  --only TA-QW-8K-1 \
  --output \
  configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1/references/TA-QW-8K-1.json
```

Repeat that singleton command for the following seven exact `--only` / output
basename pairs, preserving the manifest path and changing no production
options:

| `--only` | output basename |
|---|---|
| `TA-QW-8K-REASON-1` | `TA-QW-8K-REASON-1.json` |
| `TA-QW-8K-AGENT-HELLO-1` | `TA-QW-8K-AGENT-HELLO-1.json` |
| `TA-QW-8K-STRESS-256-1` | `TA-QW-8K-STRESS-256-1.json` |
| `TA-QW-8K-GEOGRAPHY-1` | `TA-QW-8K-GEOGRAPHY-1.json` |
| `TA-QW-8K-SCIENCE-1` | `TA-QW-8K-SCIENCE-1.json` |
| `TA-QW-8K-AGENT-PERMISSIONS-1` | `TA-QW-8K-AGENT-PERMISSIONS-1.json` |
| `TA-QW-8K-PRACTICAL-1` | `TA-QW-8K-PRACTICAL-1.json` |

Every output lives under the same
`configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1/references/`
directory. The launcher refuses a missing, duplicate, multiple, or undeclared
selection; a different manifest/workload root/output; agent-episode or force
mode; CPU-only or eager attention; and nonqualified chunking or CPU placement.
It authenticates all campaign inputs and hashes the full 16.38 GB checkpoint
before importing Torch or Transformers. Run these jobs serially, and only when
the DeepSeek or any other memory-heavy host process has completed.

Require a production-ready result, which currently must refuse because the
oracles are absent:

```bash
python3 tools/check_qwen3_heterogeneous_campaign.py \
  --require-production-ready
```

After eight independently generated files have been placed at the exact
`references/<workload-id>.json` paths declared by the manifest, freeze them:

```bash
python3 tools/check_qwen3_heterogeneous_campaign.py \
  --freeze-reference-set \
  configs/abi3/workloads/qwen3_heterogeneous_exact_8k_v1/reference-set.json
```

The freeze is intentionally create-once and refuses an existing destination.
Validate a completed set with `--reference-set <path>`.

## Immediate dependency and next execution order

The generalized launcher preflight is implemented without changing the
historical `--gate-1-production` profile or ABI 3.0. The next state-changing
step is to run the eight singleton oracle jobs serially when the memory-heavy
host is free, then freeze and validate the reference set. Only after that may
the B=1/2/4/8 HBM and ROM heterogeneous requests be constructed.

The two acceptance gates are deliberately separate and ordered:

1. **Correct output tokens:** every sequence in the exact physical batch must
   match its independent oracle token-for-token and decoded-string-for-string,
   use only legal IDs, and obey first-EOS-or-exact-256 with no post-EOS work.
2. **Desired TPOT:** only a Gate-1-passing execution may contribute TTFT,
   decode-step latency, steady-state TPOT, or aggregate-throughput evidence,
   and each B=1/2/4/8 point must be compared with its pre-frozen numerical SLO.

Reference-oracle wall time is neither accelerator TPOT nor performance
evidence. Projected roofline throughput is also not a TPOT pass. This work does
not modify the TPOT checker or comparison schemas.

Focused qualification is:

```bash
pytest -q tests/test_qwen3_heterogeneous_campaign.py
```

It covers the positive preparation and complete-reference structures plus
schema validity, byte tampering, source-hash drift, non-8K prompts, non-256
caps, cloned prompts, malformed nesting, attempted homogeneous-contract use,
missing oracles, multi-result/misselected/misbound oracles, illegal padding
IDs, premature EOS, short non-EOS results, and decoded-text drift.
