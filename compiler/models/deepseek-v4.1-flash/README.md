# Official DeepSeek V4.1 Flash compiler target

This directory binds the public `deepseek-ai/DeepSeek-V4.1-Flash` release at
immutable Git revision `dba1be0a40aa45a94ad051997016db3960a90277`, released
2026-09-10 under MIT. The registry lists 88 files totalling 510,313,353,565
bytes at that revision, 48 of them safetensors shards; the listing itself is
committed as `data/inventory/deepseek-v4.1-flash-registry-listing.json` rather
than fetched, so every check below reruns without network access.

The compiler never executes release Python as remote code. The release files are
content-bound semantic references for an independently implemented front end.

## Configuration identity

`config.json` is a byte-identical committed copy of the official root config, not
a hand-transcribed approximation: 3,311 bytes, SHA-256
`8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879`, which is also
the `config_sha256` of the already governed inventory in
`data/inventory/deepseek-v4.1-flash.json` and the digest `docs/SOURCES.md`
registers as `SRC-DSV41-FLASH-CONFIG`.

Unlike both V4 releases this config is **nested**. The language model's scalars
live under `text_config` and its `rope_scaling` with them, the weight
quantization stays at the root, and a vision tower is configured under
`vision_config`. The release record's `config_layout` records where each pinned
structure sits, so `compiler/frontend/deepseek_v41.py` resolves them rather than
assuming a flat object — and a flattened config fails the gate instead of
partially satisfying it.

`inference_config.json` is likewise a byte-identical committed copy of the
official local-inference config: 1,982 bytes, SHA-256
`2e84f45cf1dac8c7fcbb200e96667d4b913275690668ed496f24c7747207a809`. It is
retained separately because it is the flat form of the same architecture, and
because it is what `inference/model.py` actually reads.

## The checkpoint contract

`checkpoint_source.json` is the expectation half of the checkpoint identity — the
SHA-256 and exact byte size of each of those 88 files — and
`tools/build_checkpoint_source.py` produces it by hashing the local snapshot and
confronting every digest with the registry's own per-file record. Build it with:

    make checkpoint-source-deepseek-v41

It fails closed unless the whole snapshot is present, and it reads every byte, so
it is deliberately not a prerequisite of any aggregate target.

Every one of the 88 files is witnessed on content, in one of two ways, and the
difference is worth stating because the tool reports the second class as "size
alone": 52 files carry an LFS `sha256` — all 48 shards, the technical report, two
assets and one example image — and the other 36 are plain Git objects, for which
the registry publishes a `blobId`. That is a SHA-1 over the blob rather than a
SHA-256, but it is still a content witness, and
`tests/compiler/test_deepseek_v41_release.py` recomputes it locally for the two
files whose content the contract turns on: `config.json`
(`09917a9139b22d5bf8be52132787f435147b1020`) and `model.safetensors.index.json`
(`54c85064dd92c8550471302e9ae59bedbbf96ca4`). So the index's
`metadata.total_size` is content-bound at the pinned revision even though no LFS
digest covers it.

The graph adapter checks the committed config bytes, expands the 40 main layers
and three checkpoint-backed DSpark stages together with the ViT tower, and
derives all 96,085 tensor names, dtypes, shapes, scale pairs and semantic roles,
totalling 510,286,023,000 payload bytes. Both figures equal the inventory's
`tensor_count` and `checkpoint_bytes`, and the 96,085 derived names are exactly
the `weight_map` keys of the released `model.safetensors.index.json` — the
7,470,294-byte file the registry listing records at SHA-256
`74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8`, whose
`metadata.total_size` is the same 510,286,023,000 bytes.

The tensor-structure digest of that derivation is
`834a3fd1840230036c63b3edf4467d9356784f69bcc4a7fb156ffec536b8ef2c`. Unlike the
Pro digest it has been confronted with shard headers: all 48 headers of the
pinned revision are cached under `.cache/hf/headers/`, and every tensor name,
storage dtype and extent agrees, as does the per-dtype split of counts and bytes
against the inventory's `dtype_tensor_counts` and `dtype_bytes`. The release
record says so in `tensor_structure_evidence`.

## What makes this release structurally new

Six differences change *which* tensors exist rather than how large they are, and
each is derived from a released config field rather than written into a
predicate:

* **A 40-layer Causal Encoder-Decoder.** Attention no longer owns its KV per
  layer. Only the four `kv_source_layer_ids` `[2, 8, 14, 20]` carry compressor
  weights; every later layer reads the latent those publish. This is the single
  largest departure from V4, where all 43 layers but two carried a compressor.
* **A split indexer.** The eight `index_source_layer_ids`
  `[2, 8, 14, 20, 24, 28, 32, 36]` each own the query side (`wq_b`,
  `weights_proj`); only the four that also compress own the key side (`wk`,
  `k_norm`), because the index key is derived from that layer's own latent. The
  four query-only layers `[24, 28, 32, 36]` are the difference.
* **Ratio-1 compressors have no pooling gate.** `compress_ratios` names 2 and 1,
  not V4's 4 and 128: two window-only layers, then three groups of six encoder
  layers at ratio 2, then five groups of four decoder layers at ratio 1 — the
  20 + 20 split the model card states. `Compressor.__init__` builds `wgate` only
  above ratio 1, so layer 20, which is a KV source *and* ratio 1, has `wkv` and
  no `wgate`. That is one layer of forty, and it is the case a "KV source implies
  a gate" rule would get wrong.
* **Engram.** The two `engram_layer_ids` `[1, 14]` carry FP8 n-gram tables with
  per-layer row counts — 384,006,168 and 384,016,682, which differ, so one count
  cannot serve both — plus the projection that turns
  `(engram_max_ngram_size - 1) * engram_n_heads` = 24 looked-up rows into one key
  per hyper-connection copy and one shared value. The two tables are 202,758,032,400
  packed bytes, which equals the inventory's `engram_table_packed`.
* **A vision tower.** 32 ViT blocks, an aligner, three image-span delimiter
  embeddings, and a second router bias `bias_vl` that `Gate` substitutes for
  `bias` at image positions. All of it is sized from `vision_config`.
* **A halved FP8 scale block.** `quantization_config.weight_block_size` is
  `[32, 32]` where both V4 releases publish `[128, 128]`. The shared tensor
  builder in `compiler/frontend/deepseek_v4.py` now takes that block from the
  released config instead of assuming 128, so one generator produces both
  releases' scale geometry; both V4 structure digests were re-derived unchanged
  after that change. The MXFP4 expert scales stay on the format's own 32-element
  micro-scaling block, which is why they are unaffected.

What V4.1 *drops* matters as much, and the tests assert each absence: there is no
global or per-stage `hc_head_*`, no compressor `ape` position table, and no
hash-routed `gate.tid2eid` table.

`num_nextn_predict_layers: 3` agrees with the three `mtp.*` namespaces, the three
trailing compression-ratio entries, and the inference config's `n_mtp_layers: 3`.
That conflict, which both V4 releases carry and record as an explicit source
adaptation, does not exist here.

## Shared and unshared release files

The released inference implementation is **not** shared with V4: `inference/model.py`
(`4e9ae236…`), `inference/engram.py` (`11f35ecb…`) and `inference/vision.py`
(`5d49edc1…`) are new to this release, and the first two are what
`docs/SOURCES.md` registers as `SRC-DSV41-FLASH-MODEL`. `tokenizer.json` is also
new (6,367,257 bytes, `c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b`),
so the V4 tokenizer loader refuses it by construction and
`compiler/frontend/deepseek_v41_tokenizer.py` is its own boundary.
`tokenizer_config.json` is the only file shared byte for byte with both V4
releases (801 bytes, `6ac8c8dc…`); the registry records the same Git blob id
`f3dad388a2bbfd6a8605bd02754acd86d9ca5112` for it here as it does for Pro. The model card `README.md` (13,110 bytes,
`347c9db4e5506acb531cbc3b724407ab88e9af8781679152f0823d7bac16d251`) is registered
as `SRC-DSV41-FLASH-CARD`; it is not committed here, and this file is not it.

## Scope

This directory establishes configuration identity, the checkpoint source
expectation, and the derived tensor contract. It does not claim operator-complete
inference, numeric equivalence, compiled scheduling, RTL execution, or
performance closure.

The checkpoint lock **is** established. It is host state rather than a release
artifact — it names a snapshot directory on one machine — so it lives under
`~/.cache/opentallas/deepseek-v4.1-flash/checkpoint.lock.json` and is built with

    make checkpoint-lock-deepseek-v41

which reads and hashes all 510,286,023,000 payload bytes, parses all 48 shard
headers, and records a per-tensor digest. Its identity is pinned on the release
record: `checkpoint_lock_id`
`3035f90f54bdb46150c7c45a0fa8224c459583d0849c51d2c24fdb055e627a53` and
`tensor_content_sha256`
`312df8e2f3f7abf5868da7403cfb0e9c54c3f58736c35fb3d4ade344efcd53e6`.
`compiler.frontend.checkpoint.verify_checkpoint_lock` rebuilt the whole lock from
the same bytes and required canonical equality, which held in 568 s, so that
`lock_id` is reproducible on this snapshot rather than the output of a single
pass.

The lock is worth one more comparison than its own reproducibility. It knows the
checkpoint from its contents; `build_official_tensor_specs` knows it only from
`config.json`. All 96,085 tensor names, storage dtypes and extents agree between
the two, as does the payload total — an agreement between a byte-level read and a
header-free derivation that nothing in either path forces.

Because the lock exists, a Tensor Kernel IR document for this release — which
binds every weight to a byte range in a shard — can now be built. That is WP-D's
work, not this directory's.
