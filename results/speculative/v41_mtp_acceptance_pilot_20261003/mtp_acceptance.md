# DeepSeek-V4.1 MTP acceptance: inventory, pilot, headline sensitivity

Base: origin/main 7b4d51a08. Machine-readable version: `mtp_acceptance.json`. Work files: `work/`. These include `drafts.json`; `gen_out.pt` is 2.9 GB and can be deleted after review.

## 1. Inventory: which acceptance values the repo uses

| τ / α | Source | Grade | Consumed by |
|---|---|---|---|
| **3.649** (γ 5) | OWN: `results/speculative/v41_flash_dspark_onpolicy_greedy.json`. 36 prompts across 9 workloads, mixed reasoning, agentic and chat. | measured, mixed workload | `uarch_model.V41_TAU` feeds every V4.1 MTP row: ROM 4,588.9, HBM W19 4,765.4, and the HBM group-slot row's 5,673 in MICROARCH_MODEL.md. `arch_budget_v41.TAU_HEADLINE`=3.65 feeds the utilization, ladder and rack tools: v41_lanes 15,890, HEADLINE_BUNDLE, ARCH_V41_RACK, ARCH_SPEC_V41. |
| **3.78** | LMSYS DSpark blog, V4-Flash, arena-hard | third-party; **a verify window, not an accepted length**, according to `acceptance_tau.json` | `TAU_SWEEP` labels it "HEADLINE", and consolidation has `per_user_mtp_headline_tau_3p78`. **ARCHITECTURE_ATLAS.html says "adopted headline acceptance is now τ = 3.78". That contradicts arch_budget_v41 (3.65) and the record's own caveat.** |
| 2.91 / 4.5 / 5.24 | LMSYS windows, plus 4.5 interpolated | third-party upper bounds | `tau_sweep_1m` in MICROARCH_MODEL.md |
| 3.5–4.1 band | InferenceX V4.1-Flash at T=1 (3.51 / 4.07); vLLM #57432 GSM8K (3.82–3.89) | third-party | `TAU_BAND` |
| 3.27 / 3.80 | V4-Pro survival, derived from vLLM | derived | ARCH_SPEC_V41 |
| 3.43 | vLLM #56797 community "agentic" comment | uncontrolled | rederived rack rates only |
| α 0.85–0.90 | DeepSeek-V3 paper, γ 1 | third-party | citation only |
| draft = 3/40 of AR | `V41_DRAFT_FRACTION` | **ASSUMED** | every V4.1 MTP row |
| Qwen DFlash τ 2.86–3.66 | OWN, `dflash_block_acceptance.json` | measured | Qwen HBM comparator only. Qwen ROM is AR-only. |

No agentic median is bound to any headline. The committed record does contain a per-class agentic figure (τ 4.654, 20 prompts), but nothing reads it.

## 2. Feasibility

The full released V4.1-Flash weights are on disk (476 GB at revision dba1be0a, including the DSpark heads mtp.0–2). The committed on-policy harness in `tools/v41_dspark_onpolicy/` matches its recorded hashes.

Hardware:
- GPU: one RTX PRO 6000, 96 GB, idle when I started.
- Host: 188 GB RAM.
- The run is limited by disk I/O on expert reads (about 2 GB/s).

The DSpark golden at 328b5fff is not needed here. I used no reduced vehicle.

## 3. Workload

The committed prompt set `results/speculative/raw/prompts.jsonl.gz` has 24 prompts each from five agentic sources:
- BFCL v3;
- τ-bench gpt-4o retail/airline trajectories;
- nebius SWE-agent trajectories;
- Mind2Web;
- json-mode-eval.

The datasets are cached locally, so nothing was fetched.

## 4. Pilot (run now: GPU was idle, capped at 30%)

**Configuration:**
- 30 new agentic prompts: the next 6 per workload that the committed run did not use.
- Length cap raised from 4,500 to 9,000 tokens, so the 13 long τ-bench/SWE contexts the committed run skipped are now included.
- Greedy decoding, γ 5, 160 new tokens.
- Wall time: phase A 100 min, phase B 6 min.
- The first attempt ran out of GPU memory at a 15% cap; its log is in `work/`.

τ is measured by exact greedy replay. Confidence intervals come from a workload-stratified prompt bootstrap (20,000 resamples).

| Set | Prompts | Cycles | τ pooled [95% CI] | **Median of per-prompt τ** [95% CI] | α equivalent |
|---|---:|---:|---|---|---:|
| Committed agentic | 20 | 260 | 4.654 [4.46, 4.88] | 4.684 [3.88, 5.12] | 0.897 |
| **Pilot (new)** | 30 | 551 | 4.555 [4.29, 4.87] | 4.692 [4.34, 5.31] | 0.888 |
| **Combined** | 50 | 811 | 4.587 [4.38, 4.82] | **4.692 [4.37, 5.12]** | 0.891 |
| Multi-turn agents only (SWE, τ-bench, Mind2Web) | 30 | 508 | 4.012 [3.77, 4.31] | **3.917 [3.72, 4.37]** | 0.825 |

Per-workload pooled τ (combined): json_mode 5.78, bfcl 5.33, τ-bench 4.11, swe 3.95, mind2web 3.91.

The pilot reproduces the committed agentic figure. It is still **not a qualified bound value**, for these reasons:
- Contexts are at most 8K tokens, against the 1M/200K headlines.
- Continuations are only 160 tokens.
- Greedy only; T=1 serving would be lower.
- The workload weights are arbitrary. Single-shot JSON and function-call tasks inflate the all-agentic median by about 0.8 τ relative to multi-turn agent loops.
- The kernels are torch replacements of the vendor kernels.

## 5. Headline sensitivity (repo formula: rate = τ / (T_verify(6) + 3/40·T_AR); linear in τ at γ 5)

The α column below maps α to τ assuming each draft position is accepted independently: τ = Σα^i for i = 0…5. In the measured chain the conditional acceptance is roughly flat, between 0.85 and 0.91.

| α | τ | ROM product (AR 2,786.8) | HBM W19 (AR 2,261.7) | HBM group-slot TT (AR 2,801.8) |
|---:|---:|---:|---:|---:|
| 0.50 | 1.97 | **2,476 (< AR)** | 2,571 | 3,061 |
| 0.60 | 2.38 | 2,997 | 3,113 | 3,705 |
| 0.70 | 2.94 | 3,699 | 3,841 | 4,573 |
| 0.80 | 3.69 | 4,640 | 4,818 | 5,736 |
| 0.85 | 4.15 | 5,222 | 5,423 | 6,456 |
| 0.90 | 4.69 | 5,893 | 6,119 | 7,285 |
| 0.95 | 5.30 | 6,663 | 6,919 | 8,237 |
| *at τ 3.649 (current)* | | 4,588.9 | 4,765.4 | 5,673 |
| *agentic median 4.692* | | 5,901 | 6,128 | 7,295 |
| *multi-turn median 3.917* | | 4,926 | 5,115 | 6,090 |
| *chat (mt_bench) 2.458* | | 3,091 | 3,210 | 3,821 |

Break-even τ, where MTP at γ 5 equals AR, is 2.22 for ROM, 1.73 for HBM W19 and 1.80 for HBM group-slot. That corresponds to α ≈ 0.56 for ROM.

Below α ≈ 0.8 a shorter draft wins. I derived this by truncating the block and using the model's verify shape for P = 1…6. For example, at α 0.5 ROM with γ 1 gives 3,354. The per-row optimum is in the JSON.

**Unvalidated inputs:**
- The draft cost (3/40 for ROM; 49.9 µs modelled for HBM).
- The verify-pass times. They are model or composition figures only; there is no token-level greedy check in RTL, and the KV rollback and in-block causal attention are not built.
- The independence assumption behind the α→τ mapping.
- The γ<5 rows, which are derived by truncation.
- Every τ is a short-context measurement.

## 6. Plan for a qualified agentic median (for the parent)

1. **Select prompts.** Use ≥24 prompts per multi-turn agentic workload (SWE-agent, τ-bench, Mind2Web, plus BFCL multi-turn) from the committed set, with the length cap at 16K or more. Pre-register the workload weights and state "median of per-request τ" as the statistic.
2. **Generate.** Run `v41gen.py --max-new 512 --max-seq-len 17408 --gpu-frac 0.30 --prefill-group-tokens 8500` in a pinned worktree, then `v41draft.py` and `work/acc_stats.py`.
3. **Add a T=1 replay**, which needs probabilistic accept in `analyze.py`.
4. **Expected cost.** Roughly 8–10 h on one GPU at a 30% cap, limited by I/O (about 60 min of prefill per 30 long prompts, about 20 s per decode step). It needs about 25 GB of GPU memory and about 20 GB of host RAM.
5. **Long context.** Measuring acceptance at 200K–1M needs full-length agent trajectories and a chunked-prefill harness. It is out of reach of this harness on one GPU.
