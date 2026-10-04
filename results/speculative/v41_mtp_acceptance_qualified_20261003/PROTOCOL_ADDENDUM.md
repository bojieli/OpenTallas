# Protocol addendum: general-purpose class mix and blend (pre-registered 2026-10-03, before any result)

On 2026-10-03, while batch 1 was in prefill, the user redefined the headline as a general-purpose mix of eight usage classes. This addendum is committed before any batch-1 or batch-2 result exists. It does not change `PROTOCOL.md`'s measurement method: the same native DSpark block of 5, 512 new tokens, greedy and T=1 replay, and the same statistics. It adds classes and a pre-registered blend.

## Classes and their τ source

| Class | τ source | Prompts |
|---|---|---|
| (a) simple chat | **LMSYS published**: Arena-Hard 3.78 | none of ours |
| (b) reasoning | **LMSYS published**: GSM8K 5.24 | supplementary only: committed MATH-500, thinking on (24, batch 2) |
| (c) coding | **ours**: committed HumanEval, thinking **off** (class value) | 24 (batch 2); thinking-on HumanEval (24) is supplementary |
| (d) long document / summarisation / RAG | **ours**: LongBench-E, `zai-org/LongBench` @5e628be4 (MIT, from the THUDM/LongBench repo; the HF card states none). 6 each from gov_report_e (summarisation), qmsum (query summarisation), multifieldqa_en_e (single-doc QA) and hotpotqa_e (multi-doc RAG), using LongBench's own prompt templates. These are the longest contexts ≤ 12,000 tokens; selected prompts span 10,933-11,995 tokens. | 24 (batch 2) |
| (e) multilingual | **ours**: `CohereLabs/aya_dataset` @f9ea0458 test split (Apache-2.0), 4 each of Arabic, Yoruba, Turkish, Simplified Chinese, Portuguese and Telugu | 24 (batch 2) |
| (f) long agentic | **ours**: SWE-agent, τ-bench and Mind2Web; batch 1 per `PROTOCOL.md` | 72 |
| (g) assistant function calls / structured output | **ours**: committed BFCL (simple, multiple, parallel, live_multiple; 6 each) and json-mode (batch 1), plus `acon96/Home-Assistant-Requests-V2` @29ac1a80 `home_assistant_test_english.jsonl` (MIT; synthetic home-llm smart-home requests with the Home Assistant tool schema; system device state and user request; 24, batch 2) | 72 |
| (h) creative writing | **LMSYS published**: Poetry 2.91 | none of ours |

- **Batch 2 selection.** `tools/v41_dspark_onpolicy/select_batch2.py`; sha256 `b86639d6862cb459a8e5510994f93a3e1126b365ee4f6ec48f06d074bec3df36`; 144 prompts, 383,934 prompt tokens. Batch 2 runs as an extra batch; batch 1 is not restarted.
- **The LMSYS values.** Source: https://www.lmsys.org/blog/2026-07-06-dspark-sglang/, Figure 4, mixed traffic, block 6. They are labelled **"LMSYS published, V4-Flash (not V4.1), verify window (upper bound on accepted length), block 6"**. They are not converted to accepted length, and they are kept apart from our measurements. LMSYS reports a single value per class, so the same value enters the greedy blend and the T=1 blend.
- **Chat class.** It is not measured by us (user decision). No Arena-Hard or MT-Bench batch was started.

## Class value

For our classes, the class value is the **median of per-prompt τ** over the class prompts. Pooled τ is reported alongside. For class (g), the median is taken over all 72 prompts (BFCL 24, json-mode 24, smart-home 24).

## Blend

Weights are shares of **generated tokens**. Under them, the blended τ is the rate-correct harmonic mix τ_blend = 1 / Σ_c w_c / τ_c, because time per token is step / τ. The arithmetic mix Σ w_c τ_c is reported for reference only.

| Weighting | a chat | b reasoning | c coding | d long-doc | e multilingual | f agentic | g assistant | h creative |
|---|---|---|---|---|---|---|---|---|
| **equal (default)** | 1/8 | 1/8 | 1/8 | 1/8 | 1/8 | 1/8 | 1/8 | 1/8 |
| chat-heavy | 0.5 | 1/14 | 1/14 | 1/14 | 1/14 | 1/14 | 1/14 | 1/14 |
| assistant-heavy | 1/14 | 1/14 | 1/14 | 1/14 | 1/14 | 1/14 | 0.5 | 1/14 |
| agent-heavy | 1/14 | 1/14 | 1/14 | 1/14 | 1/14 | 0.5 | 1/14 | 1/14 |
| reasoning/coding-heavy | 1/12 | 0.25 | 0.25 | 1/12 | 1/12 | 1/12 | 1/12 | 1/12 |
| 3-class equal (earlier definition) | 1/3 | 0 | 0 | 0 | 0 | 1/3 | 1/3 | 0 |
| 3-class chat-heavy | 0.5 | 0 | 0 | 0 | 0 | 0.25 | 0.25 | 0 |
| 3-class agent-heavy | 0.25 | 0 | 0 | 0 | 0 | 0.5 | 0.25 | 0 |
| 3-class assistant-heavy | 0.25 | 0 | 0 | 0 | 0 | 0.25 | 0.5 | 0 |

- **Measured-only blend.** Equal weights over our five classes (c-g), which keeps the upper-bound LMSYS values out of it.
- **Envelope.** The minimum and maximum class τ over the eight classes, each labelled published or ours.
- **Rates.** The rates are reported for the blend, the envelope ends and every class, at γ 1-5 where our classes allow it. The LMSYS classes have only their one value, at block 6.

## Rates: draft cost and expert union

Both come from branch `claude/v41-hbm-speculation-20261003` @d2aff19ef, record `v41_hbm_speculation_methods_20261003`.

- **DS HBM (W19 fused, 1M).** step(γ) = verify(P = γ + 1, measured union) + the composed DSpark draft of 51.88 µs, which gives 550.21 / 604.59 / 653.77 / 705.48 / 752.73 µs at γ 1-5. The rate is τ / step, against AR 442.14 µs (2,261.7 tok/s).
- **DS ROM (product, m = 1).** Two figures:
  - verify(γ) + the ASSUMED 3/40 draft (26.9 µs), from the pilot sensitivity shape (795.2 µs at γ 5), which is the current repo row;
  - the same verify + the HBM-composition draft proxy (42.1 µs, 0.1173 × AR), which is 810.4 µs at γ 5.

  Neither ROM draft is a ROM pricing. **Both are UNVALIDATED.**
- **Expert union.** The 23.9 per layer at P = 6 was measured on the pilot's 30 agentic traces. It is re-measured on the batch-1 greedy traces with `v41router.py`, and reported beside the priced rates. The rates keep d2aff19ef's priced union unless the re-measured union differs materially; any re-pricing is left to that branch's tool.
