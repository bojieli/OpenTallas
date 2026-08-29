# DeepSeek V4 attention KV-view reference evidence

**Evidence class:** source-pinned deterministic row-space composition

**Qualified graph kind:** `ATTENTION_KV_VIEW`

**Reference profile:** `opentallas.deepseek_v4_attention_kv_view.v1`

**Graph contract at qualification:**
`cab1b68f0411ed5942b40aa31f3aa6ebdee19b8913ba7a3918672f63930c76d9`

## Scope

The qualified reference composes the BF16 KV row space consumed by sparse
attention after the current request has updated its session-bound circular
window and, when enabled, its compressed-KV state. It distinguishes three
source-defined layouts:

- main-attention prefill exposes the complete current KV sequence followed by
  only the completed compressed prefix;
- main-attention decode exposes all 128 physical circular-window slots followed
  by only the completed compressed prefix; and
- DSpark decode exposes all 128 physical main-window slots followed by the five
  current draft KV rows.

The result separately identifies the physical output regions and the rows that
an index tensor may select. Unused or preserved stale window capacity can remain
in the fixed decode buffer, as it does in the released source, but it never
enters the valid selectable-row set.

This gate does not implement KV projection, normalization, RoPE, QDQ, index
construction, sparse-attention arithmetic, an atomic inter-request transaction,
compiler or service execution, RTL, physical memory placement, cycles,
bandwidth, PPA, checkpoint-derived activations, or complete-model output.

## Pinned authority

| Artifact | Pinned identity | Governed behavior |
|---|---|---|
| Repository | `deepseek-ai/DeepSeek-V4-Flash-0731` | Official source owner |
| Revision | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` | Immutable release |
| `inference/model.py` | SHA-256 `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` | Main and DSpark KV composition plus index offsets |

The governing source regions are `get_window_topk_idxs`,
`get_compress_topk_idxs`, `Attention.forward`, `get_dspark_topk_idxs`, and
`DSparkAttention.forward`. In particular, the released DSpark decode performs:

```text
window[start_pos mod 128] = main_kv
attention_kv = concat(window[0:128], draft_kv[0:5])
```

The main-conditioning row updates the window but is not the five-row suffix.
The graph previously supplied `main_kv` to the composition site; qualification
corrects that input to the current draft `kv` block.

## Main-attention layout

For prefill at `start_pos == 0`, current KV has shape `[B,S,512]`. The output is:

```text
current_kv[0:S] || compressed_valid_prefix[0:floor(S / R)]
```

where `R` is 4 or 128 when compression is enabled. Without compression, the
second region is absent. The complete current sequence remains visible even
when `S > 128`; the circular state is independently reconciled against its
final `min(S,128)` writes but is not substituted for the prefill input.

For decode, current KV contains exactly the one row already committed at
`start_pos mod 128`. The output is:

```text
physical_window_capacity[0:128] ||
compressed_valid_prefix[0:floor((start_pos + 1) / R)]
```

The compressed offset is therefore `S` for prefill and 128 for decode. The
reference does not expose unused compressed-cache capacity. It revalidates the
compressed view's exact profile, ratio, session vector, cursor, valid-prefix
length, versions, dimensions, finite BF16 payload, and complete logical
counters before taking a deeply immutable snapshot.

## DSpark layout

DSpark composition is decode-only, uncompressed, and requires exactly five
draft rows. The separately committed main-conditioning row advances the window
cursor to `start_pos + 1`; the reference then emits:

```text
physical_main_window_capacity[0:128] || current_draft_kv[0:5]
```

The five suffix rows are all selectable. Before the window fills, only physical
slots `0..start_pos` are selectable; after it fills, every physical slot is
selectable. Circular chronology and query-specific ordering remain the job of
the separately qualified index constructors. `valid_row_indices` is the legal
row set, not a replacement index schedule.

## Session, cursor, and validity rule

Composition accepts one to four unique lowercase 64-hex-digit session IDs and
the exact complete window-state version vector. Active window lanes must form a
contiguous prefix, match those sessions, and share one cursor. Prefill requires
that cursor to equal `S`; main and DSpark decode require `start_pos + 1`.

Main prefill independently compares every retained circular-window row with the
corresponding current KV row. Main decode compares the newly written physical
slot with the supplied current row. DSpark does not perform that comparison
against its draft suffix because the committed row is deliberately produced by
`main_kv`, a distinct source. A stale version, wrong session or cursor,
unreconciled current row, malformed mode combination, nonfinite code, ragged
shape, or forged compressed-view record poisons the complete call.

The pure immutable reference cannot make a version check and successor commit
atomic between independently scheduled requests. The service controller must
eventually provide that synchronization and authenticate producer artifacts.

## Logical counters and claim boundary

The result reconciles current, window, compressed, output, and valid-row counts;
BF16 values and bytes; state rows checked; circular modulo evaluations; session,
active-lane, cursor, prefix, and version fields; exposed invalid window capacity;
one view evaluation; and zero state commits. These counts describe logical
semantic work only. They do not identify HBM or SRAM transactions, bursts,
banks, caches, NoC traffic, cycles, latency, achieved bandwidth, throughput,
energy, area, routing, or PPA.

All returned payloads, retained sources, session metadata, compressed snapshots,
regions, validity sets, and counters are deeply immutable and reconstructible.
The implementation imports neither compiler/service code nor the sparse-
attention arithmetic oracle.

## Verification

The committed suite covers both compression ratios, prefill beyond the window,
decode before and after window fill, circular wraparound, official 128-by-512
decode shape, the DSpark source distinction, stale authority, current-row
reconciliation, forged compressed views and counters, illegal mode combinations,
nonfinite/malformed values, mutable-input alias resistance, forged result
records, exact logical counter fields, and a bounded randomized physical-slot
oracle.

Reproduce the operator and interacting-state gate with:

```bash
pytest -q \
  tests/runtime/test_deepseek_v4_attention_kv_view.py \
  tests/runtime/test_deepseek_v4_kv_window.py \
  tests/runtime/test_deepseek_v4_compressed_kv.py \
  tests/runtime/test_deepseek_v4_indexing.py \
  tests/runtime/test_deepseek_v4_sparse_attention.py

pytest -q tests/compiler/test_deepseek_v4_graph.py
```

This evidence qualifies one target reference kind and repairs the DSpark graph
edge. It does not close `COMP-01`, M4, M6, M8, target-node feasibility, or any
physical or performance milestone.
