# V4.1 HBM comparator: DSpark priced with its real draft and the measured expert union

Branch `claude/v41-hbm-speculation-20261003`. These are opt-in model rows. Nothing is adopted. `uarch_model --spec` output on the default path is byte-identical to origin/main's, and `HBM_W19` and `V41_DRAFT_FRACTION` are unchanged.

## Files

| File | What |
|---|---|
| `v41_hbm_speculation_methods.json` | The record: method identity, reproduction gate, union, draft, rates at 1M and 200K, ROM note |
| `router_union.json` | Measured expert union U(p), p = 1..8, per layer; drafter union per stage; max multiplicity |
| `tau_by_gamma.json` | Exact greedy replay at gamma 1..5 from the pilot's DSpark drafts (truncation is exact for a block drafter) |
| `drafter_params.json` | DSpark (mtp.0-2) bytes by group, from the safetensors headers |
| `inputs/w19_hbm_token_compose_71b3ffc5.py` | W19's composer, copied byte for byte from `claude/w19-hbm-token` 71b3ffc5 (main carries an older version) |
| `../../../tools/v41_hbm_speculation_methods.py` | union / tau / params / price |
| `../../../tools/v41_dspark_onpolicy/v41router.py` | Router capture (teacher-forced main pass + DSpark drafter gate hooks) |
| `../../../tests/test_v41_hbm_speculation_methods.py` | Reproduction, pins, consistency, defaults untouched |

## Replay

```bash
SNAP=~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277
D=results/speculative/v41_hbm_speculation_methods_20261003
# 1. traces: the pilot's drafts.json (prompt + 160 greedy tokens, 30 agentic prompts), regenerable with
#    results/speculative/v41_mtp_acceptance_pilot_20261003/work/select_pilot.py + v41gen.py + v41draft.py
#    (sha256 d96061a0d815dc7b7403e8cabcd03f685925db6d0202ad0f751cc2c82160963a)
# 2. router capture (GPU, ~15 GB at --gpu-frac 0.3; IO-bound, ~1 h)
(cd tools/v41_dspark_onpolicy && python3 v41router.py --traces drafts.json --out router_full.pt \
     --max-seq-len 9216 --prefill-group-tokens 8500 --gpu-frac 0.3)
python3 tools/v41_hbm_speculation_methods.py union  --router tools/v41_dspark_onpolicy/router_full.pt --out $D/router_union.json
python3 tools/v41_hbm_speculation_methods.py tau    --drafts drafts.json --out $D/tau_by_gamma.json
python3 tools/v41_hbm_speculation_methods.py params --snapshot $SNAP --out $D/drafter_params.json
python3 tools/v41_hbm_speculation_methods.py price          # asserts W19's 442.14 / 715.82 us first
python3 tools/uarch_model.py --v41-hbm-dspark                # the opt-in rows
python3 -m pytest -q tests/test_v41_hbm_speculation_methods.py
```

`router_full.pt` is not committed. It is about 50 MB of int16 indices plus drafts; its sha256 is in `router_union.json`.

## Findings

**1. The repo's V4.1 "MTP" is already DSpark.** The checkpoint's `num_nextn_predict_layers = 3` modules (`mtp.0`-`mtp.2`, 7.93 GB) are the three serial stages of one DSpark block drafter, not V3-style chained MTP. Its structure:
- `dspark_block_size` 5, noise token 128799;
- inputs are the attention inputs of layers 37-39;
- each stage is a full block with a 128-slot window, MoE with 128 experts top-3, and a shared expert;
- the tied head, plus a rank-256 Markov head that chains the 5 argmaxes.

`V41_TAU` 3.649 (gamma 5, 6 verified positions) was measured with the vendor `forward_spec`. The 328b5fff golden and ISA evidence uses `drafter: dspark`. The headline method is therefore right. Two terms were wrong:
- **Draft cost.** It was ASSUMED at 3/40 of AR (33.2 µs on HBM), or taken as the audit's 49.9 µs.
- **Verify union.** It came from the uniform formula (34.6 at P = 6) or from W19's single synthetic window (27.6).

**2. Measured expert union** over 30 agentic traces, 2,614 generated positions, 40 layers:

| P | 2 | 3 | 4 | 5 | 6 | 8 |
|---|---|---|---|---|---|---|
| U (measured) | 10.40 | 14.24 | 17.74 | 20.93 | 23.90 | 29.36 |
| uniform | 11.91 | 17.72 | 23.44 | 29.08 | 34.62 | 45.45 |

- The per-layer union at P = 6 ranges from 20.9 to 30.6.
- The prompt-region union at P = 6 is 24.0.
- The drafter union over 5 slots is 7.3-8.3 experts per stage, against 14.3 under uniform routing.

**3. HBM prices on W19's composer** (fused, reproduces 442.14 / 715.82 µs):
- **Verify pass.**

  | P | 2 | 3 | 4 | 5 | 6 |
  |---|---|---|---|---|---|
  | verify (µs) | 498.3 | 552.7 | 601.9 | 653.6 | 700.9 |

  At P = 6 this compares with 715.8 µs on W19's union and 744.6 µs on the uniform union.
- **Draft.** 51.9 µs = 3 stages 41.2 + head 3.4 + 5 × 1.46 Markov. That is 0.117 of AR, against the assumed 0.075.
- **gamma 5 at τ 3.649 (1M).**

  | Variant | tok/s |
  |---|---:|
  | DSpark priced here | **4,847.7** |
  | current W19 row | 4,765.4 |
  | 3/40 assumption | 4,971.3 |
  | uniform union | 4,570.4 |

  At 200K the priced row is 4,858.3 (AR 2,266.0).
- **gamma 5 is best for every τ set.** Truncation never helps.

  | τ set | 1M (tok/s) | 200K (tok/s) |
  |---|---:|---:|
  | agentic, all 5 workloads (pilot, n30) | 6,051.8 | 6,065.1 |
  | multi-turn agentic | 5,343.5 | 5,355.2 |
  | mixed (current headline) | 4,847.2 | 4,857.7 |

**4. ROM (note only).** Replacing the assumed 26.9 µs draft with the HBM structural ratio gives 42.1 µs, which moves the τ 3.649 product row from 4,588.8 to 4,502.8 (−1.9%). The ROM verify does not depend on the union, because experts are stationary in their macros. What matters there is collisions on one element: the mean maximum multiplicity is 4.19 at P = 6.

**5. Qualified run (`claude/v41-mtp-acceptance-qualified-20261003`, c24d5da1e).** This run already exercises native DSpark: block 5, vendor `forward_spec`, and greedy plus T=1 replay. Nothing in it needs to change for DSpark. For this pricing it would help to:
- emit τ at gamma 1..5, which is exact by truncating the same drafts;
- record router indices in `moe_stream`, a one-line hook, so the union comes out on the qualified traces at no extra cost.
