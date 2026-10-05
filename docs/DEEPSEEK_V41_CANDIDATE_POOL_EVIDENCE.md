# DeepSeek-V4.1-Flash candidate-pool evidence

**Evidence class:** executed differential comparison of an independent
repository reference against the pinned vendor function, on sampled score rows.
Not a checkpoint-derived value, not a token, not a performance number.
**Qualified boundary:** `select_candidate_blocks` — level one of the
Hierarchical Sparse Indexer's two-level top-k — from index scores to a
per-position admission mask, for one query row at a time.
**Numeric contract:** `candidate_mask_v1`
**Reference profile id:** `deepseek_v41_flash_target_precision_v1`
**Release:** `deepseek-ai/DeepSeek-V4.1-Flash`
**Revision:** `dba1be0a40aa45a94ad051997016db3960a90277`
**Checkpoint lock:** `3035f90f54bdb46150c7c45a0fa8224c459583d0849c51d2c24fdb055e627a53`

**Graph-contract digest at qualification: NONE EXISTS.** The V4.1 node-by-node
lowering is not emitted — `export_deepseek_v41_kernel_graph` refuses with
"the remainder of gate DS41-I2 is the node-by-node lowering itself, which this
front end does not emit yet" — so there is no graph contract to digest and none
is invented. Bound instead to the planned census digest
`44f53d34427faacb81cbbc148d42932c930e5cc33dcedaa80498c47bd1ee4cbc` and the
release's `tensor_structure_sha256`
`834a3fd1840230036c63b3edf4467d9356784f69bcc4a7fb156ffec536b8ef2c`. Revisit when
the graph contract first exists.

## Pinned authority

| Artifact | Pinned identity | Use |
|---|---|---|
| `inference/model.py` | SHA-256 `4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65` | `select_candidate_blocks`, and `Indexer.forward`'s two branches around it |
| `config.json` | SHA-256 `8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879` | `candidate_source_layer_id` 20, `candidate_topk_blocks` 2,048, `candidate_block_size` 8, `index_source_layer_ids` [2, 8, 14, 20, 24, 28, 32, 36] |
| Reference | `runtime/reference/candidate_pool.py` SHA-256 `3a4681bf78f61f2f425925599c861cf0d6ee0b665cddfcf60f3f07367ce4690a` | `select_candidate_blocks` (new) and `select_candidate_mask` (pre-existing) |
| Producer | `tools/run_deepseek_v41_reference_oracle.py` SHA-256 `8339288c26c144255938baa54dafdace4fa6c7cf2432e89dffed0112c978c5b7` | The comparator |
| Record | `results/abi3/deepseek_v41_reference_oracle_probe.json`, stages `candidate_pool` and `index_scans` | The executed evidence |

## The three decisions, and why a new reference was needed

`select_candidate_mask` already existed and takes block ids a top-k has already
chosen — which is the operand the RTL takes. It is not the whole of the pinned
function. Three decisions live between the scores and the ids:

1. **the −inf pad of the partial final block**, which makes an unreachable
   block's score −inf instead of letting it wrap into a neighbour;
2. **the pin**, which the pinned source computes as
   `(compress_lens - 1) // block_size` — the block holding *this query's* newest
   reachable position, **not** the last block of the position axis;
3. **the `top.values > -inf` drop**, which stops a query with fewer reachable
   blocks than `topk_blocks` from admitting padding.

`select_candidate_mask`'s `pin_last_block` pins `block_count - 1`. During decode
the two coincide, because the axis is exactly as long as the one query can
reach. **During prefill they do not**: `compress_lens` is per-query and every
query pins a different block. A reference that pinned the axis's last block would
admit positions a prefill query cannot reach. That gap is what
`runtime.reference.candidate_pool.select_candidate_blocks` closes, and
`test_decode_case_agrees_with_select_candidate_mask` pins that the two references
still coincide on the configuration they share.

## What was executed

64 sampled rows, each with a width deliberately chosen so that most are **not**
a multiple of the block size — so the −inf pad of the partial final block is
exercised — and each with a reachable extent `compress_lens` drawn inside the
width, positions beyond it set to −inf as the pinned contract requires. The
pinned `model.select_candidate_blocks` was run at the released
`candidate_topk_blocks` 2,048 and `candidate_block_size` 8, and its boolean mask
compared position by position against the reference's.

```
candidate pool: 64/64 untied rows identical, 0 rows tied at the threshold
and not counted, 0 disagreements
```

The reference is independent: it orders exact values with `fractions.Fraction`
and a sentinel for −inf, and never calls torch. Rows whose admitted set is not
determined by the scores alone are reported separately as `tie_at_threshold` and
excluded from the agreement count, because the pinned implementation calls
`torch.topk`, whose tie order is unspecified, and a comparison on a tied row is
not evidence either way. No such row arose in this run.

## The pool bound, measured where it binds

The plan's `candidate_pool_bound` checker states that every `INDEX_TOPK` after
the candidate source carries a mask whose population is at most 16,384
(= 2,048 × 8, both read from the released config at run time). The `index_scans`
stage ran the pinned `Indexer.forward` at layer 20 (the candidate source) and
layer 24 (the first index source that consumes the pool), in both phases:

| Layer | Phase | Role | Positions scored | Positions admitted | Pool bound | Selected/query |
|---|---|---|---|---|---|---|
| 20 | prefill (256 queries) | candidate_source | 65,536 | — | 16,384 | 256 |
| 24 | prefill (256 queries) | pool_consumer | 65,536 | 33,792 | 16,384 | 256 |
| 20 | decode at `start_pos` 20,000 | candidate_source | 20,001 | — | 16,384 | 512 |
| 24 | decode at `start_pos` 20,000 | pool_consumer | 20,001 | **16,377** | 16,384 | 512 |

The decode rung is the one that tests the bound: a query reaching 20,001
compressed positions is the only configuration in which the admitted population
can be smaller than the scan. 16,377 rather than 16,384 is the tail: the pinned
pin is block `(20001 - 1) // 8 = 2500`, whose 8-position span is truncated by
`[..., :width]` to the 1 real position at 20,000, giving `2047 * 8 + 1`.
`test_the_probe_reached_a_rung_where_the_pool_bound_binds` refuses an artifact
that never reached such a rung.

## The finding: the scan is not the pool

The pinned `Indexer.forward` slices
`shared_attn.index_k[:bsz, : end_pos // ratio]` and scores **all** of it with its
own `einsum`, and only then masks to the candidate pool:

```python
index_score = torch.einsum("bshd,btd->bsht", q, index_k)
index_score = (index_score.relu_() * weights.unsqueeze(-1)).sum(dim=2)
...
elif self.uses_candidates:
    index_score = index_score.masked_fill(~shared_attn.candidates, -torch.inf)
```

So a Reindex layer's SCAN is the full reachable width — 20,001 positions at the
decode rung above — while its ADMITTED population is bounded by 16,384.

`AttentionGroup.index_scan_entries_cap` in `src/opentallas/schema.py` carries the
other reading:

> DeepSeek-V4.1's Hierarchical Sparse Indexer lets a decoder Reindex layer score
> only the candidate pool the decoder's Full layer built — 2,048 blocks of 8
> positions, 16,384 entries — **so its scan stops growing with context**. The Full
> layer itself still scans everything.

and `configs/models/candidates/deepseek-v4.1-flash.json` charges
`index_scan_entries_cap: 16384` on the `csa2-1-reindex` group accordingly. **The
measured scan does not stop growing with context.** At the executed rung it is
20,001 positions against the cap's 16,384, a factor of 1.2213, and the scan
tracks `end_pos` while the cap does not.

This is the same shape of error the schema's own `index_scan_min_compressed_entries`
docstring retracts three paragraphs earlier — a bound read off the architecture's
intent rather than measured from the code, and there recorded as "the grade error
this repository has now made three times". Both numbers are reported here and
neither is corrected into the other. Two things follow, and only the first is
established by this document:

1. the pinned reference implementation scores the full reachable width on a
   Reindex layer, at the one rung executed;
2. **whether an accelerator may exploit the pool to avoid scoring the rest is an
   architecture question this document does not answer.** If it may, the cap is a
   design intent and should be graded as one; if it may not, the profile
   under-charges the index term at long context. Nothing here decides which.

## Not established

- **Which blocks win.** The indexer's parameters in the `index_scans` stage are a
  seeded sample, not released weights, because reading released rows needs the
  layer-streaming engine that does not exist. A scan WIDTH is set by the released
  shapes and the released selection rules; WHICH positions score highest is
  weight-dependent and is not claimed.
- **The tie rule.** `torch.topk`'s order is unspecified and no tied row arose, so
  nothing was learned about ties. `runtime/reference/selection.py` owns that
  question and was not exercised here.
- **Batch above 1, and the world-size > 1 `all_reduce` path.** Neither was run.
- **Any scan at or beyond the mandatory 200,000-token rung.** The largest
  position reached is `start_pos` 20,000. The 1.2213 ratio above is a measurement
  **at that rung only** and must not be read as a ratio at any other context; the
  ratio grows with context and nothing here measures how.
- **The prefill scan above 256 queries.** `Indexer.index_score` is
  `[b, s, 32, s / ratio]`, quadratic in the prompt, so a long prefill needs the
  query-axis tiling the V4 program wrote and V4.1 has not.
- **Any RTL correlation.** `results/rtl/a3_v41_candidate_mask_campaign.json` and
  `a3_v41_block_max_campaign.json` exist, are not evidence in this document, and
  were not re-run. **Both records are now source-stale with respect to
  `runtime/reference/candidate_pool.py`**: they pin that file whole, at SHA-256
  `311d7fbd9bdb212f8361ba8c6838edf52d31e7999f01b943b313a83ac77d470b`, and the
  8,456-byte `select_candidate_blocks` section appended for this work moves it to
  `3a4681bf78f61f2f425925599c861cf0d6ee0b665cddfcf60f3f07367ce4690a`. The addition
  is purely additive — `select_candidate_mask` and `block_max_rows` are untouched,
  and all 37 non-currency tests in `tests/test_a3_v41_route_block_max.py` and
  `tests/test_a3_v41_ngram_hash.py` still pass — but
  `test_campaign_sources_have_not_moved_underneath_the_record` fails until the
  campaigns are re-run and rebound:

  ```bash
  python3 tools/run_a3_v41_block_max_rtl_campaign.py \
    --output results/rtl/a3_v41_block_max_campaign.json
  python3 tools/run_a3_v41_candidate_mask_rtl_campaign.py \
    --output results/rtl/a3_v41_candidate_mask_campaign.json
  ```

  Those artifacts belong to WP-K and were deliberately not overwritten here. The
  `route_block_max` record is independently stale on
  `compiler/ir/v3/lowering.py`, which this work did not touch.
- **Any token, TPOT, throughput, bandwidth, latency, area or energy.**
- **The greedy token ladder.** Not run; `model.sparse_attn` cannot launch on this
  device (see the FP4 KV evidence document for the verbatim failure).

## Reproduce

```bash
PATH=/usr/local/cuda/bin:$PATH python3 tools/run_deepseek_v41_reference_oracle.py \
  --stage candidate_pool --stage index_scans \
  --output results/abi3/deepseek_v41_reference_oracle_probe.json
pytest -q tests/test_deepseek_v41_reference_boundaries.py
```
