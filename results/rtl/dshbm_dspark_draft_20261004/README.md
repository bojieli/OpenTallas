# DS-V4.1 HBM accelerator: DSpark draft MEASURED (successor to the 51.88 us model draft)

> **TAU SUPERSEDED (owner rule 2026-10-04).** `model.json`/the record is now composed at the third-party published tau (3.8879, `tools/third_party_tau.py`, `results/speculative/third_party_acceptance_20261004/`). Hand-written figures below that quote tau 4.159 are the superseded self-measured composition: scale MTP tok/s by 3.8879/4.159 = 0.9348 (and MTP J/token by its inverse); AR figures and ROM:HBM ratios are unchanged.

Owner request (2026-10-04, fairness). Until now the HBM draft was a model estimate: 51.88 us at 1M, from
d2aff19ef (`v41_hbm_speculation_methods`), as used in the authoritative record c246e929d. The ROM draft was
MEASURED (main dae91947c). This record measures the HBM draft the same way, so that both sides of ROM:HBM MTP
rest on measured drafts.

Tool: `tools/dshbm_dspark_draft_chain.py` (golden / chain / fullshape / compose). Successor rows:
`python3 tools/uarch_model.py --hbm-mtp-drafts-measured` (`hbm_mtp_both_drafts_measured()`).
`hbm_switch_latency_authoritative()` and its record are unchanged; the AR rows and verify passes do not move.

## What was measured (minimum component: one SM / die share + composition)

Definition, the same as the ROM record:
- **draft** = embed (y's row) + 3 DSpark stages over 5 slots + LM head + a SERIAL 5-step chain. Each step is
  d_{i+1} = argmax(logits_i + markov(d_i)), and needs the previous step's token.
- **seed_commit** (main_proj, main_x gather, main_norm, the 3 stages' window rows, ctl commit) is priced separately,
  as the ROM's `seed_commit` term is.
- **step** = verify(P=6) + draft + seed_commit.

| Part | Vehicle | Result |
|---|---|---|
| `chain.json` | Reduced-v2 checkpoint, closed loop on the HBM RTL elements. LM head on `ot_gpu_sm_v`: one 5-column pass (the ctl's DHEAD), and also 5 one-column passes. Per step: Markov head matvec of the embedding row of the token the RTL argmax produced, on `ot_gpu_sm_v`. Bias add + full-vocab argmax on `ot_dshbm_argmax` (ot_gpu_fadd RNE). Python moves bytes only. | **PASS.** Head logits 0 mismatches (5-col; every 1-col pass equals its column). Markov bias rows 0 mismatches. 5/5 argmax = golden. Drafts [2111, 343, 2983, 109, 3060] = `Model.draft`. Forced drafter (golden AR continuation, d_4 corrupted, host-forced Markov inputs): 5/5 exact. |
| `fullshape.json` | Released weights, busiest SM of a TP-96 die (Icarus 12, ot-epyc1tb) | **PASS**, all exact. LM head **1 column 3,671 cycles = 5 columns 3,671** (3,440 lines either way). DSpark stage matvecs on mtp.0 at 5 columns equal the 1-column record (wq_a/wkv 241, wq_b 430, wo_a 437, wo_b 308, gate 323, expert w1 232 / w2 226). Seed wkv at 6 columns 241. Argmax: SM epilogue 43 biased 18 cycles, 32-SM die merge 16, 96-die select 24. |
| `composition.json` | W19's composer rules plus measured elements | Every draft collective is COUNTED and priced with the authoritative transports. |

Collectives in the draft: **23**, against 26.3 assumed:
- 3 stages x 6 (x_proj gather, o-group all-reduce, attn_out gather, router gather, expert-intermediate gather,
  ffn_out gather) at 5 positions;
- 5 chain argmax merges, 768 B, one Tomahawk crossing + tail each = 0.629 us.

The seed adds 1: the main_x gather at 6 positions.

Head placement follows the design. DS HBM keeps every weight in HBM: L2 is 4 x 2 MB and weights bypass it; SMEM
staging is 128 KB per SM. The 13.79 MB head share per die therefore streams every pass:
- the die streams at 4 x 0.958 TB/s measured = 3.83 TB/s, which is 3.60 us bare;
- the idle window before each pass refills 3.50 MB of staging;
- so the pass is SM-bound at 3,528 cycles (lines + drain) = 2.94 us, for 1 and 5 columns alike.

Chain step (as built, Tomahawk): **1.212 us**. The merge transport is 52% of it.

| Term | Value |
|---|---|
| Markov-row fetch | 0.133 us |
| Markov matvec | 404 cycles |
| Boundary | 78 cycles |
| Bias + argmax epilogue | 18 cycles |
| Die merge | 16 cycles |
| 96-die gather | 0.629 us |
| Select | 24 cycles |

## Result (tau 4.159, gamma 5; authoritative default scenario per design)

HBM draft at 1M (200K is identical; the draft does not depend on context):

| Design | Model draft (us) | Measured as built (us) | Measured per-step head (us) | Seed + commit (us) |
|---|---:|---:|---:|---:|
| Accelerator (firm ladder, TU protocol) | 47.23 | **44.50** | 56.46 | 3.46 |
| Accelerator, measured composition | 48.04 | 45.28 | 57.36 | 3.57 |
| GPU-organised ablation (NVLS measured) | 74.99 | 69.93 | 82.01 | 4.46 |
| GPU-faithful R0 (fenced) | 282.04 | 253.45 | 270.69 | 15.22 |

The model draft includes main_proj, which belongs to the seed. The ROM draft is 144.44 us as built and 105.55 us
with the fused head, plus a 3.2 us seed_commit.

HBM MTP tok/s with both drafts measured. Values are 1M / 200K; the parenthesis is the old row with the model draft.

| Design | HBM as built | HBM per-step head |
|---|---:|---:|
| Accelerator firm (6,351.9 / 6,364.9) | **6,344.7 / 6,356.8** | 6,231.1 / 6,242.7 |
| Accelerator measured comp. (6,032.4 / 6,044.8) | 6,025.4 / 6,036.9 | 5,921.7 / 5,932.8 |
| Ablation W19 (4,123.9 / 4,129.8) | 4,126.4 / 4,131.8 | 4,077.5 / 4,082.8 |
| GPU-faithful R0 (1,249.9 / 1,250.7) | 1,255.0 / 1,255.7 | 1,248.5 / 1,249.2 |

ROM:HBM MTP at 1M, accelerator firm (200K in parentheses). ROM: 6,733.7 as built, 7,186.2 L1, 7,858.1 L1+L2
EXPECTED.

| ROM | vs HBM as built | vs HBM per-step head |
|---|---:|---:|
| as built | **1.061** (1.090) | 1.081 (1.110) |
| L1 fused head | 1.133 (1.165) | 1.153 (1.187) |
| L1+L2 (expected) | 1.239 (1.278) | 1.261 (1.301) |

Against the accelerator's measured composition, as built, the ROM:HBM ratios are 1.118 / 1.193 / 1.304. The ROM:HBM
AR ratio is unchanged at 0.94.

**Like-for-like pairs:**
- ROM as built (one head pass a step) against HBM per-step head: **1.081**.
- ROM L1+L2 against HBM as built: **1.239** (the ROM side is EXPECTED). The HBM as built already has both: its bias
  and argmax are fused in the SM epilogue (L1), and its DHEAD is one 5-column pass (L2).

## L1 / L2 on HBM (reported, not built)

- **L1, fused bias + argmax.** Already in the as-built HBM: `ot_dshbm_argmax` is the SM epilogue. Gain 0.
- **L2, batched head.** Already in the as-built HBM: the ctl issues DHEAD once with 5 columns. Columns are free on
  the SM (3,440 lines for 1 or 5 columns). Undoing it (the per-step-head row) costs +12.0 us of draft, -1.8% MTP.
- **What remains.** The HBM chain is now dominated by the cross-die argmax merge, one switch crossing per step. No
  further L1/L2-class lever applies.

## Verdict

The HBM draft is MEASURED: 44.50 us as built at 1M on the accelerator, plus a 3.46 us seed, against the 47.23 us
model term. The HBM MTP rows move by -0.1% (6,351.9 -> 6,344.7 tok/s), well inside the owner's 1% band. The
earlier "asymmetry that favours HBM" therefore did not bias the comparison materially.

With both drafts measured, ROM:HBM MTP (1M, accelerator) is:
- **1.06**, as built against as built;
- **1.08**, like-for-like per-step head;
- 1.13, ROM L1;
- 1.24, ROM L1+L2 expected.

Successor to the authoritative MTP columns.

## Claim boundary

Exactness is shown on the reduced vehicle. Its seeded Markov bias (|b| <= 0.01) never flips an argmax there, so the
chain's token feedback is checked through bit-exact bias rows for 9 distinct input tokens and exact argmaxes. The
bias-flip behaviour of `ot_dshbm_argmax` is covered by its own record: 6/6 Markov-biased rows in
`results/rtl/dshbm_dspark_rtl_20261003`.

The stages' dedicated-unit (local) and expert-fetch terms are W19's element prices; no new RTL was run for them.
Full-shape cycles use synthetic BF16 activations on released weights. No P&R and no SS/FF figure is claimed.

## Replay

```
SP=/tmp/dd; D=results/rtl/dshbm_dspark_draft_20261004
HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_draft_chain.py golden --out $SP/golden.pkl   # needs tokenizers (local)
# ot-epyc1tb (jobs/run.sh in /srv/opentallas-scratch/claude/dshbm-draft; DSHBM_SM_EXE per process):
HDC_V41_ARITH=chunk8 python3 tools/dshbm_dspark_draft_chain.py chain --golden $SP/golden.pkl --out $D/chain.json
HDC_V41_ARITH=chunk8 OT_V41_FLASH_SNAPSHOT=<snap> python3 tools/dshbm_dspark_draft_chain.py fullshape --out $D/fullshape.json
python3 tools/dshbm_dspark_draft_chain.py compose --chain $D/chain.json --fullshape $D/fullshape.json --out $D/composition.json
python3 tools/uarch_model.py --hbm-mtp-drafts-measured --out $D/successor_rows.json
python3 -m pytest -q tests/test_dshbm_dspark_draft.py
```

The golden operands' sha256 is `7d3b4a88...bc36` (`chain.json` `golden_operands_sha256`). The runs used source
commit 5c449cd1e.
