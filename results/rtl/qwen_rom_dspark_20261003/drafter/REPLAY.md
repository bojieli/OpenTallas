# Qwen3-8B ROM: the DSpark drafter (step 3 of the DSpark adoption gate)

Branch `claude/qwen-rom-dspark-drafter-20261003`. Model and measurement records; no RTL and no P&R.

## The drafter

- **Checkpoint:** `deepseek-ai/dspark_qwen3_8b_block7` @ `03326e5043815da1f81b109078b2889737c26017` (arXiv 2607.05147). `drafter_facts.json`.
- **License:** not stated. The repo has no README or model card and no license tag. The reference code, `github.com/deepseek-ai/DeepSpec` @ `005e03b8`, is MIT.
- **Shape:** five Qwen3-8B-shaped layers; `fc` 20,480 -> 4,096 over the target's hidden states after layers 1, 9, 17, 25 and 33; a vanilla Markov head (`markov_w1` and `markov_w2`, each 151,936 x 256); a confidence head 4,352 -> 1; block size 7.
- **Shared with the target:** `embed_tokens` and `lm_head` are byte-identical to Qwen3-8B (row 1,000 checked).
- **Drafter-unique parameters:** 1,126,422,017.

## ROM placement and area (`drafter_rom_schedule.json`, `tools/qwen_rom_dspark_drafter_rom.py`)

- **Words a die at TP4:** the drafter needs 2,873 tile code words a die: 5 layers 2,560, `fc` 214, `w2` 99.
- **Tile slack:** the tile holds 5 x 4,096 = 20,480 words. The target uses 36 x 512 + 1,584 = 20,016, so 464 are free. The drafter needs 2,409 more.
- **The only legal placement:** +1 bank (two `ot_rom_4096x266_m8`) a tile, 58.8% full = **+30.84 mm2/die**.
  - The drafter must sit in the tiles that consume it: one 512-bit word a tile a cycle.
  - The free shoreline (20.29 mm2) and IO spare (9.11 mm2) therefore cannot host it.
  - **r2 becomes 822.8 mm2, 7.8 mm2 over the 815 budget.** It is still inside the 26 x 33 mm reticle: the width goes from 24.15 to 25.09 mm.
  - The pricing's "fits r2 slack ~52 mm2" treated shoreline and IO area as interchangeable with tile ROM.
- **Rejected:** a re-bank on `ot_rom_8192x266_m8`. Its SS fmax is 1,017.5 MHz, below 1.2 GHz.
- **Markov correction:** the pricing's 1.13 mm2 counted one of the two matrices.
  - `w2` lives in the new tile bank.
  - `w1` is a 256-byte row lookup: 2.98 mm2 replicated at the IO edge, or 0.74 mm2 split by rank plus a 256-element all-gather a slot.

## Draft step on the tiles (model, `draft_step_cycles`)

The draft step is time-multiplexed on the target's own engine. It has four parts:
- ingest of the newly committed tokens' context features: `fc`, an all-gather, and the context K/V of each layer;
- 5 layers at S slots;
- the lm_head for S slots;
- the sequential Markov chain: `w2`, then an add and argmax on the stream unit, then the cross-die argmax gather, about 1,509 cycles a slot.

| S | Existing RTL | Widened AR | Widened AR + attn2 + overlap |
|---|---|---|---|
| 3 (verify block 4) | 69,955 (58.3 us) | 62,595 (52.2 us) | 43,865 (36.6 us) |
| 7 | 158,163 | 136,083 | 79,893 |

- The block term uses the pricing's per-position increment.
- That increment is a MODEL until the step-1 verify-layer gate measures it.

## Acceptance sample (`tau_sample.json`, `tau_summary.json`, `tools/qwen_rom_dspark_tau.py`)

**Setup:**
- Local GPU, BF16 target.
- 8 classes, 3 hand-written prompts each, 128 greedy tokens, non-thinking template.
- Offline replay of lossless greedy speculative decoding, with the confidence head off.

**Checks:**
- The precomputed-context fast path equals DeepSpec's `_forward_backbone` at every prompt.
- The BF16 target's greedy path equals FP32 for 84 tokens and diverges at generated token 85 of the check prompt. That is recorded, not hidden.

**tau, verify block 4** (drafter S = 7 truncated to 3 drafts), compared with the pricing's DERIVED DSpark tau:

| Class | Measured | Pricing |
|---|---|---|
| chat | 2.98 | 2.97 |
| reasoning | 3.66 | 3.11 |
| coding | 3.40 | 2.90 |
| long agentic | 2.96 | 2.74 |
| assistant structured | 3.49 | 3.95 |
| long doc / RAG | 3.54 | not priced |
| multilingual | **1.96** | not priced |
| creative | **2.13** | not priced |

**Equal-weight means:**
- 8 classes: 3.02 at B4, 4.48 at B8.
- The 5 priced classes: 3.30 measured against 3.13 priced at B4, and 5.13 against 4.31 at B8.

**Other results:**
- The W8 drafter equals BF16 within the sample noise: 3.01 at B4.
- Drafting only 3 slots instead of 7 loses about 0.07 at B4.

## Golden (`golden.json`, `tools/qwen_rom_dspark_drafter_golden.py`)

The golden is one draft step in `hdc_golden` arithmetic under the W8 contract, single-core order:
- K/V in FP32, checked against DeepSpec's PyTorch model on the same dequantised weights;
- K/V in FP8, the target's KV contract.

It reports the draft tokens and the max logit difference.

**Result: PASS on every case.** The golden's draft tokens equal DeepSpec's on one prompt (anchor at position `start` in `golden.json`):

| Slots | K/V | Draft tokens equal | Max logit diff | Max logit |
|---|---|---|---|---|
| 3 | FP32 | yes | 0.062 | 33.2 |
| 3 | FP8 | yes | 0.554 | 33.2 |
| 7 | FP32 | yes | 0.056 | 35.1 |
| 7 | FP8 | yes | 1.121 | 35.1 |

- The FP32 rows isolate the golden's BF16 activation and the R-ARITH rounding against the FP32 reference.
- The FP8 rows add the target's KV contract, which the reference does not model.
- The argmax logit bits per slot are recorded, so they serve as the ISA/RTL oracle for this step.

## Replay

```
python3 tools/qwen_rom_dspark_drafter_rom.py
# local GPU (venv: system torch 2.10+cu128, transformers 5.18.0; DeepSpec @ 005e03b8)
python tools/qwen_rom_dspark_tau.py --deepspec DeepSpec --draft DRAFT_SNAP --target QWEN3_8B_SNAP --device cuda --dtype bfloat16 --check-fp32 --max-new 128 --out tau.json
python tools/qwen_rom_dspark_drafter_golden.py --deepspec DeepSpec --draft DRAFT_SNAP --target QWEN3_8B_SNAP --device cuda --out golden.json
```

The run directory is `/home/ubuntu/dspark-drafter-run`, which has its own STATUS.md, MANIFEST.txt and logs. The EPYC attempt was stopped under the user directive that no model inference runs on the EPYC.

## Open items

- The TP4 lowering order of the golden: column-split K sums and rank-order fold of row-split partials.
- The drafter program on the ISA and RTL.
- An 815 mm2 fit, which needs 7.8 mm2 removed elsewhere or a budget decision.
- A larger tau sample from benchmark prompts.
- The target-feature export path from the verify pass: 5 x 4,096 FP32 a position, already replicated on every die.
- The drafter weights carry no license.
