# DeepSeek-V4.1-Flash DSpark (MTP) acceptance, qualified agentic run: pre-registered protocol

Pre-registered on 2026-10-03, before the main run started. The commit that adds this file precedes every result file in this directory. Results that contradict the protocol are reported as they come out; nothing below is changed after the run.

## Drafter

The drafter is the one the DeepSeek-V4.1 ROM and HBM designs price: the DSpark module that ships inside the V4.1-Flash checkpoint (`mtp.0`-`mtp.2`, revision dba1be0a). DFlash is not used, since it is the Qwen comparator's drafter.

- The run uses the vendor's own `inference/model.py` modules: `DSparkBlock`, `DSparkAttention` (a 128-position window ring), `DSparkMarkovHead` and `forward_spec`.
- The draft structure is native:
  - one parallel pass over a block of `dspark_block_size = 5` slots, which are the last committed token followed by four noise tokens (id 128799);
  - then a semi-autoregressive Markov-head bias, where draft k depends on draft k-1.
- gamma 5 is this native block size. It is not a chained one-token MTP. A verify pass checks 6 positions (`V41_POSITIONS`).
- Draft inputs are the target's layer-37/38/39 attention inputs, averaged over the hc copies (`dspark_target_layer_ids`), at every committed position.

The harness evaluates a draft row at every generated position. The walk uses only the rows at cycle starts. In serving, the verify pass also produces the target hidden states of every accepted position, so the window ring sees the same inputs.

**Differences from vendor serving, stated rather than changed:**

- Kernels are torch replacements of `kernel.py`, as in the committed record.
- The vendor ships no speculative verify loop: `generate.py` decodes autoregressively. The accept rule below is therefore the standard one, not a vendor one.

## Workload

- **Prompts.** Every agentic prompt in the committed `results/speculative/raw/prompts.jsonl.gz`, 24 per workload, selected by `tools/v41_dspark_onpolicy/select_qualified.py`. There is no length cap: each prompt runs at the full context it provides. The selection sha256 is `c5ed3003819d626c72fe34d33f5d26cb2cd683e3c3519539e7122145d72e6266`.
- **Headline set (multi-turn agent loops).** `agentic_swe_agent`, `agentic_tau_bench` and `agentic_mind2web`: 72 prompts, weighted equally by construction (24 each).
- **Reported separately, never mixed into the headline.** `agentic_bfcl` and `agentic_json_mode`: single-shot function-call and JSON tasks, 48 prompts.
- **Context.** Prompt lengths are 1,520-8,428 tokens. The headline set holds 72 prompts and 295,570 tokens; the mean is 4,105 and the median 3,820. These contexts are 24-690x shorter than the 200K (secondary) and 1M (ROM) design contexts. See "Long context" below.
- **Output length.** Up to 512 new tokens per prompt (EOS stops it earlier). Thinking mode follows each prompt's `enable_thinking` flag; all 120 prompts are chat mode.

## Decoding and replay

The two modes share each prompt's prefill. The T=1 trace is a twin of the greedy trace with cloned caches, seeded by `20261003 ^ crc32(prompt_id)`.

1. **Greedy.** The target decodes greedily. The draft is the vendor `forward_spec` at temperature 0, which is argmax with the Markov head fed its own argmax. tau comes from an exact speculative replay (`analyze.walk`): starting at p = L, each cycle commits a+1, where a is the number of leading draft matches out of 5. Only full-depth cycles count.
2. **T=1 (temperature 1.0, top_p 1.0).** The target samples with the vendor `sample()` Gumbel trick, and the harness records p(x) for every sampled token. The draft is sampled at T=1 too, since `DSparkBlock.temperature = args.temperature`.
   - The accept rule is standard speculative sampling (Leviathan et al. / Chen et al.): accept d_k with probability min(1, p(d_k)/q(d_k)), and on rejection resample from norm(max(0, p − q)).
   - The replay realises this rule exactly in distribution on the sampled target trajectory x, through the maximal coupling: draft d_k equals x_k with probability min(1, q_k(x_k)/p_k(x_k)). Under that coupling, d_k has marginal q_k, the acceptance probability is Σ min(p, q), and the token emitted on rejection is distributed as the residual. The committed text therefore always follows x.
   - q_k(x_k) is the DSpark distribution at depth k, with the Markov head teacher-forced on x_{k-1}. Depth k matters only when d_{k-1} = x_{k-1}.
   - Per prompt, the replay is Monte Carlo over 2,000 replays with seeded uniform draws. Per-prompt tau = Σ committed / Σ cycles over the replays.
   - top_p 0.95, which the vendor also recommends, is not run. It would sharpen p and raise acceptance somewhat, so T=1 at top_p 1 is the conservative sampled case.

## Statistics (each reported for greedy and for T=1, for the headline set and per workload)

- Per-prompt tau.
- **Median of per-prompt tau.** 95% CI from a workload-stratified prompt bootstrap: 20,000 resamples, seed 7.
- **Pooled tau** (Σ committed / Σ cycles), with the same bootstrap CI.
- Conditional acceptance by depth, the histogram of a, and the alpha equivalent (tau = Σ_{i=0..5} alpha^i).
- **Primary serving figure.** The T=1 multi-turn median of per-prompt tau, because DeepSeek evaluates every agentic benchmark at T=1. The greedy multi-turn median is reported beside it and is comparable to the committed greedy `V41_TAU = 3.649`.

## Rates (the repo's formula; MTP at gamma 5 is linear in tau)

- ROM product: rate = 4,588.9 × tau / 3.649. This is `consolidation.json` `per_user_mtp` at tau 3.649 against AR 2,786.8, with the m = 1 time-multiplexed verify.
- HBM W19 fused: rate = tau × 1e6 / (715.82 + 49.9) µs. The AR is 442.14 µs, or 2,261.7 tok/s (`HBM_W19`).

`m = 1` is the lane multiplier, meaning positions per weight word per cycle. It is not the draft length. The ROM's m = 1 verify still checks 6 positions, so the accept formula and tau are the same as for any m. Only `T_verify` changes, and the model already prices it.

The draft cost is `V41_DRAFT_FRACTION = 3/40` of an AR token (ROM) and 49.9 µs modelled (HBM). It is **UNVALIDATED**, and so are the verify-pass times: they are model figures, with no RTL token-level verify and no KV rollback built.

## Long context

Acceptance is measured at 1.5K-8.4K tokens of context only. At 200K-1M tokens, DSpark still sees only a 128-position window plus the target's hidden states, but those hidden states come from a target attending over the long context. Whether acceptance changes at the design contexts is **not measured**. These numbers must not be presented as 1M or 200K acceptance.
