# Official DeepSeek V4 Pro compiler target

This directory binds the public `deepseek-ai/DeepSeek-V4-Pro-0813` release at
immutable Git revision `72e1d3230f6c080a530b0a1d46f8eb4602340597`. The registry
lists 92 files totalling 892,762,497,859 bytes at that revision, 66 of them
safetensors shards; the listing itself is committed as
`data/inventory/deepseek-v4-pro-0813-registry-listing.json` rather than fetched,
so every check below reruns without network access.

`checkpoint_source.json` is **not** here yet. It is the expectation half of the
checkpoint identity — the digest and exact byte size of each of those 92 files —
and `tools/build_checkpoint_source.py` produces it by hashing the local snapshot
and confronting every digest with the registry's own per-file record. That needs
the complete snapshot, which is still downloading. Until it exists, the compiler
authenticates the two committed files below against the digests pinned on the
release record in `compiler/frontend/deepseek_v4_releases.py`, and every entry
point that needs the source contract or the checkpoint lock fails closed and
names the tool that produces it. Build it with:

    make checkpoint-source-deepseek-pro

The compiler never executes release Python as remote code. The release files are
content-bound semantic references for an independently implemented front end.

`config.json` is a byte-identical committed copy of the official root config,
not a hand-transcribed approximation: 1,967 bytes, SHA-256
`9dd2a89255469e120b333668ef5a169b7ae46c00f6bbab786bf0be457546aec0`, which is
also the `config_sha256` of the already governed inventory in
`data/inventory/deepseek-v4-pro-0813.json`. The graph adapter checks those bytes,
expands the exact 61 main layers and three checkpoint-backed DSpark stages, and
derives all 149,782 tensor names, dtypes, shapes, scale pairs and semantic roles,
totalling 892,727,580,904 payload bytes. Both figures equal the inventory's
`tensor_count` and `checkpoint_bytes`, and the 149,782 derived names are exactly
the `weight_map` keys of the released `model.safetensors.index.json` — the
11,651,606-byte file the registry listing records at SHA-256
`2de2ac1e43134f8b03bf6156067715b7c3c73b1a507329e606023c601a56d30a`, whose
`metadata.total_size` is the same 892,727,580,904 bytes. That comparison was run
against a copy carrying that digest; the file itself arrives with the rest of the
snapshot. The tensor-structure
digest of that derivation is
`b776f80c8422880de39e49a0679d4d5b81d218bdd4074b66c691760b65cc0eeb`. It is
adapter-derived from names, dtypes and shapes; unlike the Flash digest it has not
yet been confronted with shard headers, and the release record says so in
`tensor_structure_evidence`.

Twelve architecture-affecting root-config keys differ from DeepSeek-V4-Flash-0731
and every other key is equal: `hidden_size` 7168, `num_attention_heads` 128,
`q_lora_rank` 1536, `o_groups` 16, `index_topk` 1024, `n_routed_experts` 384,
`moe_intermediate_size` 3072, `routed_scaling_factor` 2.5, `dspark_markov_rank`
512, `dspark_target_layer_ids` `[58, 59, 60]`, `num_hidden_layers` 61, and the
64-entry `compress_ratios` list. The structural consequence of the last one is
that this release has no window-only layer at all: its first two layers are
ratio 128 where Flash's are ratio 0, so every layer carries compressor weights.

The root config's `num_nextn_predict_layers: 1` conflicts with the three `mtp.*`
namespaces, the three trailing compression-ratio entries, and the official
inference config's `n_mtp_layers: 3`, exactly as it does for Flash. The adapter
preserves the root value and records the three-stage resolution as an explicit
source adaptation; it does not silently equate these fields.

`inference_config.json` is likewise a byte-identical committed copy of the
official local-inference config: 1,240 bytes, SHA-256
`801bc719d08cd5be57cddc185cac621417522810e29d0314849c939bf0176ee7`. It is
retained separately because it supplies the explicit `n_mtp_layers: 3` used by
`model.py`.

The released inference implementation is shared with DeepSeek-V4-Flash-0731 byte
for byte. `inference/model.py`, `inference/kernel.py`, `inference/convert.py`,
`inference/generate.py` and `encoding/encoding_dsv4.py` hash to the same SHA-256
values on both snapshots, measured on each. Every source anchor in the operator
ledger and every numeric contract derived from that code therefore carries over
unchanged, which is what makes this release a re-parameterisation of the existing
front end rather than a re-derivation of its semantics. `tokenizer.json` and
`tokenizer_config.json` are shared too: the registry listing's Git blob ids for
both files equal `git hash-object` over the local Flash copies, so their SHA-256
pins carry over without waiting for the download. The model card `README.md`
(7,522 bytes, `61755d88e95789fcd7a36f50892f97bba977a30fc99d0f2907ab787ed10b0e66`)
and the two configs are the only released files that differ.

This directory establishes configuration identity and the derived tensor and node
contracts. It does not claim a verified checkpoint, operator-complete inference,
numeric equivalence, compiled scheduling, RTL execution, or performance closure.
No byte of this checkpoint's payload has been read: there is no checkpoint lock,
so `checkpoint_lock_id` and `tensor_content_sha256` are unset on the release
record and no Tensor Kernel IR document — which binds every weight to a byte
range in a shard — can be built yet.
