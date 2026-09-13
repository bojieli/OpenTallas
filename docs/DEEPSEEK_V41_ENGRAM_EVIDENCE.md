# DeepSeek-V4.1-Flash Engram evidence

**Evidence class:** executed run of the pinned vendor module at released
geometry with a reduced table and sampled weights, plus an executed refutation
of a repository numeric contract. Not a checkpoint-derived value, not a token,
not a performance number.
**Qualified boundary:** the Engram row geometry (24 hashed rows of 264 B per
token) and the expression DAG of `Engram.forward`'s gate. **Not** the gate's
numeric contract: see the finding below.
**Numeric contracts in play:** `engram_gate_fp32_v1` (pre-existing, and shown
here to be a different function from the pinned one), `ngram_hash_u32_v1`
**Reference profile id:** `deepseek_v41_flash_target_precision_v1`
**Release:** `deepseek-ai/DeepSeek-V4.1-Flash`
**Revision:** `dba1be0a40aa45a94ad051997016db3960a90277`
**Checkpoint lock:** `3035f90f54bdb46150c7c45a0fa8224c459583d0849c51d2c24fdb055e627a53`

**Graph-contract digest at qualification: NONE EXISTS.** The V4.1 node-by-node
lowering is not emitted, so there is no graph contract to digest and none is
invented. Bound instead to the planned census digest
`44f53d34427faacb81cbbc148d42932c930e5cc33dcedaa80498c47bd1ee4cbc` and the
release's `tensor_structure_sha256`
`834a3fd1840230036c63b3edf4467d9356784f69bcc4a7fb156ffec536b8ef2c`. Revisit when
the graph contract first exists.

## Pinned authority

| Artifact | Pinned identity | Use |
|---|---|---|
| `inference/model.py` | SHA-256 `4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65` | `Engram.forward`, `ParallelEngramEmbedding` |
| `inference/engram.py` | SHA-256 `11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884f94d476d3897` | `EngramLayout`, `NgramHashState`, `compute_hash_multipliers` |
| `config.json` | SHA-256 `8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879` | `engram_layer_ids` [1, 14], `engram_num_embeddings` [384,006,168; 384,016,682], `engram_n_heads` 8, `engram_head_dim` 256, `engram_max_ngram_size` 4, `engram_compressed_vocab_size` 99,092, `rms_norm_eps` 1e-20 |
| Reference | `runtime/reference/engram.py` SHA-256 `248f40843af5ea9d6f60fe34ba8ea66f9310f794d091474a5850c5e732d9aae0` | `engram_gate`, `ngram_row_ids`, and the new `engram_gate_pinned_form` |
| Producer | `tools/run_deepseek_v41_reference_oracle.py` SHA-256 `8339288c26c144255938baa54dafdace4fa6c7cf2432e89dffed0112c978c5b7` | The comparator |
| Record | `results/abi3/deepseek_v41_reference_oracle_probe.json`, stage `engram_gate` | The executed evidence |

## Measured row geometry

The pinned `Engram` was constructed at the released `engram_n_heads` 8,
`engram_head_dim` 256, `engram_max_ngram_size` 4, `hc_mult` 4 and
`hidden_size` 5,120, and its own buffers read:

- `n_hash_cols` = `(max_ngram_size - 1) * n_heads` = **24** rows per token;
- one row is `ParallelEngramEmbedding.weight` at `torch.float8_e4m3fn`,
  256 elements = 256 B, plus `ParallelEngramEmbedding.scale` at
  `torch.float8_e8m0fnu`, `256 // 32` = 8 elements = 8 B, so
  **264 B per row**, measured from the buffers rather than transcribed;
- 24 × 264 = **6,336 B gathered per token per Engram layer**, and there are two
  Engram layers.

The released tables are 384,006,168 and 384,016,682 rows; at 264 B that is
202.76 GB, which is `data/inventory`'s figure and is **not** re-derived here as
evidence.

## The finding: the pinned gate is not `engram_gate_fp32_v1`

`runtime/reference/engram.py::engram_gate` was written before the pinned sources
were present in this checkout; its own docstring says so and records that
"confirming the operand-role mapping and the reduction convention against the
vendor source is WP-H work and remains open". The sources are now present. The
pinned `Engram.forward` is

```python
kv          = wkv(embed(hash_ids).flatten(-2))
key, value  = kv.split([hc_mult * dim, dim], dim=-1)
key         = key.float().unflatten(-1, (hc_mult, dim))
weight      = q_weight.float() * k_weight.float()
h, eps      = x.float(), self.eps
rstd        = rsqrt(h.square().mean(-1) + eps) * rsqrt(key.square().mean(-1) + eps)
dot         = (h * weight * key).sum(-1) * rstd * dim ** -0.5
gate        = sigmoid(copysign(dot.abs().clamp_min(self.clamp_value).sqrt(), dot))
return        (h + gate.unsqueeze(-1) * value.float().unsqueeze(-2)).to(x.dtype)
```

and it diverges from `engram_gate_fp32_v1` in four ways, none of them a rounding
detail:

| id | pinned | `engram_gate_fp32_v1` | changes a value |
|---|---|---|---|
| D1 clamp target | `clamp_min(1e-6)` on **\|dot\|**, the normalised dot, before the square root | 1e-6 on the **norm product**, i.e. the denominator | yes |
| D2 mean not sum | `rsqrt(mean(h²) + norm_eps) · rsqrt(mean(key²) + norm_eps)`, then `· dim**-0.5`, with `norm_eps` = **1e-20** | `dot / max(sqrt(Σq²)·sqrt(Σk²), 1e-6)`; no eps term at all | yes |
| D3 operand roles | the dot is `h · (q_weight·k_weight·key)`; `h` is both the gate's query and the residual | the dot is `q · k`; `hidden_codes` take no part in the gate | yes |
| D4 gated term | `h + gate · value`, `value` shared across the `hc_mult` copies | `h + gate · (key·value)`, elementwise | yes |

D1 and D2 were **confirmed by construction, not by reading alone**: the
released-geometry module reports `clamp_value = 1e-06` and `eps = 1e-20` — two
different values, where `engram_gate_fp32_v1` has one epsilon used once.

The divergence is exhibited by execution, not argued.
`runtime.reference.engram.prove_pinned_form_differs()` runs both contracts on
one finite 8-element input, feeding `engram_gate_fp32_v1` the pinned operands in
the roles it names (the most favourable reading available to it):

```
pinned_gate_code = 1061731455   pinned_gate_value = 0.7841262221336365
v1_gate_code     = 1060032557   v1_gate_value     = 0.6828640103340149
gate_codes_differ = True        outputs_differ = True
```

`engram_gate_pinned_form` is the pinned DAG stated in exact arithmetic, named
`engram_gate_pinned_dsv41_form` — **deliberately not** `engram_gate_fp32_v1`,
because giving a different function the same contract name is exactly how a
deployment comes to hand one to an engine expecting the other. Nothing in this
work edited `engram_gate` or the vectors built from it: which of the two the
machine must implement is a contract decision, not a documentation fix.

## What was executed on the device

The pinned `Engram.forward` ran on an NVIDIA RTX PRO 6000 Blackwell Workstation
Edition (compute capability 12.0) through its real FP8 path — the `wkv`
projection is `Linear` at `torch.float8_e4m3fn` and dispatches the pinned
`fp8_gemm` — in 0.081 s, and the `Engram.forward` wrap fired exactly once. An
independent recomputation of the expression DAG above agreed to
`max_abs_difference = 0.0`. That shows **which expression the module evaluated**;
it is *not* agreement with an independent numeric reference, because both sides
of that particular comparison are torch, and the record says so in
`transcription_check.what_this_shows`.

Declared adaptation, `engram_table_rows_reduced`: the released table for layer 1
is 384,006,168 rows of 264 B, about 101 GB, and
`ParallelEngramEmbedding.forward` calls `F.embedding` over the whole table, so it
cannot be materialised on a 101.97 GB device alongside anything else. The table
was allocated with 4,096 rows. The row **width** is measured from the buffer and
is unchanged; the gate arithmetic depends on row **values**, not row count. This
stage is therefore evidence about the gate expression and the wrap, and about no
released row.

## Not established

- **That either gate contract is the one the machine must implement.** This
  document records that they differ and which one the pinned source states. It
  does not change a contract.
- **Bit equality between `engram_gate_pinned_form` and the vendor.** torch
  evaluates `(h * weight * key).sum(-1)` in an unspecified order, so a
  per-element comparison against the exact-arithmetic form is a measurement to
  report, not a bit claim, and it was not taken.
- **Any released table row, and therefore any released gate value.** The table
  was reduced and the weights are a seeded sample.
- **`NgramHashState.forward` and the compressed token map.** Not run here.
  `NgramHashState.__init__` asserts the compressed vocabulary is exactly 99,092
  and builds it from a tokenizer by decoding every one of 129,280 token ids; that
  was not executed in this record. `tools/check_a3_v41_ngram_hash_vendor_oracle.py`
  and `results/rtl/a3_v41_ngram_hash_vendor_oracle.json` are a separate prior
  record, are not evidence in this document, and were not re-run.
- **The `1e-6` `hc_eps`**, which is a different constant from both
  `clamp_value` and `norm_eps` and was not exercised.
- **Table residency.** Where the 202.76 GB of Engram tables live is plan section
  3.4's decision; nothing here measures a lookup cost, a transaction count, or a
  fraction of a decode step.
- **The `world_size > 1` sharded `all_reduce` path.** Not run.
- **Any RTL correlation.** `results/rtl/a3_v41_engram_gate_campaign.json` exists,
  is built against `engram_gate_fp32_v1`, is not evidence in this document, and
  was not re-run. Given D1–D4, whether it is bound to the right contract is open.
  `results/rtl/a3_v41_ngram_hash_campaign.json` is additionally now source-stale:
  it pins `runtime/reference/engram.py` whole, and the `engram_gate_pinned_form`
  section appended for this work moves that file's digest to
  `248f40843af5ea9d6f60fe34ba8ea66f9310f794d091474a5850c5e732d9aae0`. The addition
  is purely additive — `engram_gate` and `ngram_row_ids` are untouched and every
  bit-exactness test still passes — but
  `test_campaign_record_sources_have_not_moved` fails until the campaign is
  re-run and rebound with
  `python3 tools/run_a3_v41_ngram_hash_rtl_campaign.py --output results/rtl/a3_v41_ngram_hash_campaign.json`.
  That artifact belongs to WP-K and was deliberately not overwritten here.
- **Any token, TPOT, throughput, bandwidth, latency, area or energy.**

## Reproduce

```bash
PATH=/usr/local/cuda/bin:$PATH python3 tools/run_deepseek_v41_reference_oracle.py \
  --stage engram_gate \
  --output results/abi3/deepseek_v41_reference_oracle_probe.json
pytest -q tests/test_deepseek_v41_reference_boundaries.py
```
