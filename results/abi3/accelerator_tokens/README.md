# Accelerator-side token captures

## What is in here

Raw captures of accelerator runs that produced tokens, preserved out of a
session scratchpad so the evidence for a headline claim does not live in a
temporary directory.

**These are raw captures, not graded evidence.** They were produced by an
ad-hoc driver script, not by a committed, reproducible repository tool. Do not
cite them with an `executed` grade in `tools/check_evidence_grades.py` until a
committed tool reproduces them. The claim they support is real; the
*reproducibility discipline* around them is not yet met, and recording that
honestly is the point of this file.

## deepseek_v4_flash_rom_p32

DeepSeek-V4-Flash-0731 on the ROM backend, first validated token.

| | |
|---|---|
| backend | `rom` |
| graph | `fa785d3fd7e3af81c98ce6f6e9b2ce58004058614675ca6fcc3c9c90402dfcff` |
| prompt | 32 tokens = `TA-DS-CHAT-1.token_ids[:32]` |
| generated | `[13806]` |
| failure | `None` |
| instructions retired | 47,877 (21,937 issued, 262 predicated off) |
| wall | 4,353.4 s |

**Validation.** The oracle gold for the identical prompt is
`results/abi3/deepseek_v4_reference_oracle_prefix.json` → `TA-DS-CHAT-1-P32`,
whose first generated token is **13806**. The two prompts were compared
element-by-element and are byte-identical (`prompt_token_ids ==
token_ids[:32]`, both length 32). The oracle is an external comparator running
the vendor's own inference code on the pinned checkpoint through the official
fp8 expert path; it never supplies an activation to the accelerator (ADR-003
§18). It was reproduced token-identically in a second independent run
(`deepseek_v4_prefix_gold_reproduction.json`).

## What this establishes, and what it does not

Establishes: the DeepSeek-V4-Flash ROM deployment executes the real model
end-to-end on the real checkpoint and emits the token a faithful
implementation emits, for this prompt.

Does **not** establish:

- **Multi-token decode.** One token exercises the forward pass; it says
  nothing about the KV transaction across decode steps. **There is no decode
  step to say anything about:** the first DeepSeek decode step ever run trapped
  (`results/abi3/deepseek_v4_rom_ta-ds-chat-1-p8_decode_execution.json`),
  because both backends size the attention KV row space's compressed segment
  from the request span, which is one at decode. See
  `docs/DEEPSEEK_SPARSE_ATTENTION_GATE.md`.
- **Sparse attention.** `window_size` is 128 and `index_topk` is 512, and the
  20 `compress_ratio=128` layers hold zero compressed positions below 128
  tokens. At 32 prompt tokens none of the three thresholds is reached — and
  neither is it at TA-DS-CHAT-1's full 104 tokens. Sparse selection under
  pressure is the `TA-DS-CTX-*` ladder's job and neither gate substitutes for
  it. **That ladder now has rungs a backend run can reach** —
  `TA-DS-CTX-129-1`, `-160-1`, `-256-1` and `-2052-1`, built by
  `tools/build_deepseek_v4_context_threshold_workloads.py`, with oracle gold in
  `results/abi3/deepseek_v4_reference_oracle_threshold.json` — and
  `docs/DEEPSEEK_SPARSE_ATTENTION_GATE.md` records what running against them
  established and what it did not.
- **The HBM lane.** Only the ROM backend has produced a validated DeepSeek
  token. A ROM-vs-HBM comparison requires both sides to run the model.
- **RTL.** This is the golden-model/simulator path. The DeepSeek deployment
  does *not* currently correlate in RTL; see
  `results/rtl/abi3_deployment_campaign.json`.
