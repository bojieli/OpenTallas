# DeepSeek-V4.1-Flash CSA2 shared-cache evidence

**Evidence class:** executed demonstration of cross-layer cache sharing in the
pinned vendor modules, plus a structure derived from the released config at run
time. Not a checkpoint-derived value, not a token, not a placement decision, not
a performance number.
**Qualified boundary:** which layer owns each compressed-KV resource, which
layers read it, and that a reading layer holds no copy of its own. The
accelerator-side placement rule this is evidence *for* is stated but **not**
checked here.
**Graph kind:** `STATE.READ` (a placement and lifetime rule, not a new kind —
plan section 5, last three rows)
**Reference profile id:** `deepseek_v41_flash_target_precision_v1`
**Release:** `deepseek-ai/DeepSeek-V4.1-Flash`
**Revision:** `dba1be0a40aa45a94ad051997016db3960a90277`
**Checkpoint lock:** `3035f90f54bdb46150c7c45a0fa8224c459583d0849c51d2c24fdb055e627a53`

**Graph-contract digest at qualification: NONE EXISTS.** The V4.1 node-by-node
lowering is not emitted — `export_deepseek_v41_kernel_graph` refuses with "the
remainder of gate DS41-I2 is the node-by-node lowering itself, which this front
end does not emit yet" — so there is no graph contract to digest and none is
invented. Bound instead to the planned census digest
`44f53d34427faacb81cbbc148d42932c930e5cc33dcedaa80498c47bd1ee4cbc` (3,131 planned
kernels over 40 layers) and the release's `tensor_structure_sha256`
`834a3fd1840230036c63b3edf4467d9356784f69bcc4a7fb156ffec536b8ef2c`. Revisit when
the graph contract first exists.

## Pinned authority

| Artifact | Pinned identity | Use |
|---|---|---|
| `inference/model.py` | SHA-256 `4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65` | `SharedAttentionRuntime`, `Attention._compress_kv`, `Indexer.owns_k`, `Indexer.uses_candidates` |
| `config.json` | SHA-256 `8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879` | `compress_ratios`, `kv_source_layer_ids` [2, 8, 14, 20], `index_source_layer_ids` [2, 8, 14, 20, 24, 28, 32, 36], `candidate_source_layer_id` 20 |
| Producer | `tools/run_deepseek_v41_reference_oracle.py` SHA-256 `8339288c26c144255938baa54dafdace4fa6c7cf2432e89dffed0112c978c5b7` | The comparator |
| Record | `results/abi3/deepseek_v41_reference_oracle_probe.json`, stages `widths` and `index_scans` | The executed evidence |

## The three shared resources

`SharedAttentionRuntime` carries exactly four slots — `compress_kv`, `index_k`,
`topk_idxs`, `candidates` — with one slot each, and the vendor's own comment
records why that is enough: "Layers run in order and every source writes before
its consumers read, so one slot each is enough and nothing needs resetting
between forwards." **The layer order is therefore load-bearing**, which is what
makes this a lifetime rule rather than a data layout.

| Resource | Written by | Read by |
|---|---|---|
| `compress_kv` | every `kv_source_layer` | every later layer with a non-zero `compress_ratio`, until the next source |
| `index_k` | every `kv_source_layer` that is also an `index_source_layer` (`Indexer.owns_k`) | every later `index_source_layer` that owns none |
| `candidates` | `candidate_source_layer_id` 20 | every later `index_source_layer` (`uses_candidates`) |
| `topk_idxs` | every `index_source_layer` | every later layer that is not one |

## The ownership structure, derived from the released config

Computed from `compress_ratios` and `kv_source_layer_ids` at run time — nothing
below is transcribed in the producer:

| Owner layer | Readers | Layer count | Compression ratio |
|---|---|---|---|
| (none) | 0 – 1 | 2 | 0 — pure sliding window, no compressed cache |
| 2 | 2 – 7 | 6 | 2 |
| 8 | 8 – 13 | 6 | 2 |
| 14 | 14 – 19 | 6 | 2 |
| 20 | 20 – 39 | 20 | 1 |

Index-source layers owning no index keys: 24, 28, 32, 36. Candidate-pool
consumers: 24, 28, 32, 36. This reproduces plan section 6.1's statement — "a
`StateResource` written by layer 2 is read by layers 3 to 7, one written by layer
20 by layers 21 to 39" — from the released config rather than restating it.

**The compression ratio changes at layer 20, from 2 to 1.** No ratio-1 layer
therefore reads a ratio-2 cache: the group boundary and the plan's two-wafer
split (layers 0–19 on wafer 1, 20–39 plus the head on wafer 2) fall at the same
layer. Enumerating every (reader, owner) pair against that split yields **no pair
whose owner is on the other side**. That is the arithmetic behind section 6.1's
claim that the rule "every reader of a shared global cache is placed on the stage
that owns it" holds by construction for this release and this split.

## What was executed

Six `Attention` modules were constructed at the released geometry, one per
distinct (ratio, owns-KV, owns-index) class the released config produces, and
each cache read off the buffer the module itself registered:

| Layer | ratio | `is_kv_source` | `is_index_source` | Buffers it owns |
|---|---|---|---|---|
| 0 | 0 | false | false | window |
| 2 | 2 | true | true | window, main, index |
| 3 | 2 | false | false | window |
| 20 | 1 | true | true | window, main, index |
| 21 | 1 | false | false | window |
| 24 | 1 | false | **true** | window only |

Layer 24 is the load-bearing row: it is an index source, so it runs an `Indexer`,
but it is not a KV source, so `Indexer.owns_k` is false and **it registers no
`k_cache` at all**. When its `Indexer.forward` ran, the buffer the counters read
the index entry width from was recorded as

```
"read_from": "Indexer.k_cache handed to Indexer.forward at layer 24"
"shape": [1, 4096, 128],  "dtype": "torch.bfloat16",  "entry_bytes": 256
```

— a `[1, 4096, 128]` buffer that layer 24 does not own, reached through
`shared_attn.index_k`. That is cross-layer sharing observed at run time, not
inferred from the source.

The same pair demonstrated the candidate pool crossing the same boundary: layer
20 published `shared_attn.candidates` and layer 24's indexer consumed it,
admitting 33,792 of 65,536 scored positions in the 256-query prefill and 16,377
of 20,001 in the decode step at `start_pos` 20,000.

Every cache measured is `torch.bfloat16`, because `inference/generate.py` calls
`torch.set_default_dtype(torch.bfloat16)` before constructing the `Transformer`
and every cache is registered with `torch.zeros` at the default dtype. Measured
entry widths, beside the profile's recipe widths (which are read from
`configs/models/candidates/deepseek-v4.1-flash.json`, never restated):

| Role | Measured, grade `executed` | Recipe, grade `read_from_profile` | Ratio |
|---|---|---|---|
| main | 1,024 B | 288.0 B | 3.5556 |
| index | 256 B | 68.0 B | 3.7647 |
| window | 1,024 B | 528.0 B | 1.9394 |

The measured widths carry grade `executed`; the recipe widths do not, and
neither is corrected into the other.

## Not established

- **The accelerator-side placement rule itself.** `shared_state_locality` in
  `compiler/backends/rom/common/check.py` — "no `STATE.READ` resolves to a
  resource whose writer is on another node or wafer" — is the plan's checker, and
  it was **not** run: there is no V4.1 lowering for it to check. What is
  established is the vendor-side ownership structure the rule is about.
- **The two-wafer placement.** No wafer, node, link or region is measured,
  chosen or validated here. The split at layer 20 is the plan's, and this
  document only records that the released ownership groups do not straddle it.
- **`compress_kv` sharing, observed.** The layer 20 → 24 demonstration is of
  `index_k` and `candidates`. That layers 21–39 read layer 20's `compress_kv` is
  read from the pinned source and derived from the config; no layer above 24 was
  constructed or run.
- **`topk_idxs` reuse across the up-to-five-layer lifetime.** Not exercised: it
  requires a full `Attention.forward`, and `model.sparse_attn` cannot launch on
  the available device — at the released `n_heads` 64 and `head_dim` 512 it fails
  with `InternalError: Failed to set the allowed dynamic shared memory size to
  141312`, against 101,376 B of opt-in shared memory per block on an NVIDIA RTX
  PRO 6000 Blackwell Workstation Edition (compute capability 12.0).
  `Attention.forward`'s wrap therefore recorded **zero** calls, and the record
  lists it under `unexercised_symbols` rather than reporting a zero.
- **Ordering violations.** That a consumer run before its source sees a stale or
  absent resource follows from `SharedAttentionRuntime` having one slot and no
  reset, but no run was made to provoke it.
- **Batch above 1, `world_size` above 1, and the MTP/DSpark layers.** None run.
- **Residency, capacity, bandwidth, transactions, cycles, TPOT, throughput,
  latency, area or energy.** None claimed and none measured.

## Reproduce

```bash
PATH=/usr/local/cuda/bin:$PATH python3 tools/run_deepseek_v41_reference_oracle.py \
  --stage widths --stage index_scans --stage instrumentation \
  --output results/abi3/deepseek_v41_reference_oracle_probe.json
pytest -q tests/test_deepseek_v41_reference_boundaries.py
```
