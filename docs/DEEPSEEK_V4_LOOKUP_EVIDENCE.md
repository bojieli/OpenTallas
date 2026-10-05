# DeepSeek V4 Flash lookup-slice evidence

**Evidence date:** 2026-08-28

**Implementation commit:** `6e65b0c`

**Evidence class:** real official payload, three-operator functional slice

**Status:** exact selected-row checkpoint differential; not full-model execution

This record closes the first official-checkpoint compiler-to-service-engine
vertical slice. It does not claim that OpenTallas can yet execute a transformer
block, prefill, decode, attention, MoE arithmetic, KV/compressor state, logits,
or the complete DeepSeek V4 Flash graph.

## Immutable source and compiler identities

| Item | Governed value |
|---|---|
| Official repository | `deepseek-ai/DeepSeek-V4-Flash-0731` |
| Official revision | `7872f01b1d1fe23eabc4c98b48bffcef5a386062` |
| Checkpoint lock | `30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760` |
| Tensor-content digest | `7ca2e951786c4cd46b64b437d975da3565a1692bdceeb804c09d5fe9e1503b3f` |
| Checkpoint inventory | 72,317 tensors; 48 shards; 166,878,536,440 payload bytes |
| Config SHA-256 | `6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023` |
| Index SHA-256 | `98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b` |
| Tensor-structure SHA-256 | `18285fe60ca3655be488bbabb88b59489b8ee03cff7fc4f4729424051ca83e0e` |
| Complete MP=4 plan | `7b87ee6168e13cf9be7c5e812a13490b6f264bda78a96ceb2e7c02580c49b3a7` |
| Selected application | `2fa9f16abe2f584cc6a72a91512f2adc7faa27935cd8049d21d1b9b183d0e692` |
| Lookup deployment | `7ad4788c978add9011452b263a18fdbab0bd6c66310ae80174e77d30bb31c3b4` |
| Differential report | `830f0d8a0730d012e6be41eb1507f10ef1b70f1829efbbad7b3e50cd2b3e2a95` |

The checkpoint was read twice: once to construct the complete content lock and
again through `verify-checkpoint` to rebuild and compare that lock. The official
adapter then accepted all 72,317 tensors and all 166,878,536,440 payload bytes.

## Selected canonical application

The executable slice consumes only these two locked source tensors:

| Tensor | Dtype and shape | Payload bytes | Locked payload SHA-256 |
|---|---:|---:|---|
| `embed.weight` | BF16 `[129280, 4096]` | 1,059,061,760 | `c05019ecf9435fa47cdcbb35df74c8ade6c4ceedd6ebe75db9ea7a607f6ad2ef` |
| `layers.0.ffn.gate.tid2eid` | I64 `[129280, 6]` | 6,205,440 | `b310d7aa41cf4967e3db21bb0b00b12357f4423b4347e71760a29d340031b897` |

The canonical applicator emitted eight assignments: four disjoint vocabulary
slices for the embedding and four byte-identical replicas for the hash-route
table. It consumed 1,065,267,200 source bytes and emitted 1,083,883,520 bytes.
Independent replay passed before deployment publication.

The application deliberately retains the status
`partial_official_transform_application_not_release_evidence`. The complete
77,116-assignment, 175,539,889,120-byte MP=4 plan is a separate M2 payload
application and is not implied by this selected slice.

## Executed semantics

The dedicated fixed-width `OTV4` ABI contains exactly:

1. `TOKEN_EMBED`: rank-aware gather of raw BF16 encodings;
2. `HC_EXPAND`: bit-preserving four-way structural copy;
3. `HASH_ROUTE`: gather of the checkpoint's six signed-I64 expert IDs;
4. terminal `COMPLETE`.

The service engine consumes only the deployment manifest, semantic descriptor,
tensor manifest, microcode, expectations, and copied ROM payloads. It
stream-verifies the artifact table and memory-maps the four embedding ranks. It
does not read compiler source tensors or a known-answer file during execution.

## Official boundary differential

The request used these token IDs, covering both sides of every MP=4 vocabulary
boundary:

```text
0, 32319, 32320, 64639, 64640, 96959, 96960, 129279
```

After execution, a separate checker streamed `embed.weight` and
`layers.0.ffn.gate.tid2eid` from the original locked checkpoint. It did not
import the lookup service engine. Every persisted output was parsed with exact
shape and integer bounds and compared bit-for-bit:

| Output | Shape | Elements | Expected and observed SHA-256 |
|---|---:|---:|---|
| `embedding_bf16_codes` | `[1, 8, 4096]` | 32,768 | `06f7f7ca047ae1d5d64c44d2c0a0e641184a03d20890d7991e9be1fab4837e22` |
| `hc_hidden_bf16_codes` | `[1, 8, 4, 4096]` | 131,072 | `dbdef7616b41a268f42305c15b8f0c7d97c3f6a90ac7cf63f2f66a01395f269e` |
| `expert_ids` | `[1, 8, 6]` | 48 | `53f915c3357a903cf63adb24469987436ea5f4102f0c8bfd8fa62165b5229c83` |

All three comparisons returned `exact`. The request SHA-256 is
`326b3c534995ec01e0302f4a132aac6ccd96ea622f207cb4dff9b625b66ca7ec`.

The independently recomputed functional counters were:

| Counter | Exact value |
|---|---:|
| BF16 codes copied | 131,072 |
| ROM lookup rows | 16 |
| Logical input bytes read | 128 |
| Logical ROM bytes read | 65,920 |
| Logical activation bytes read | 65,536 |
| Logical activation bytes written | 328,064 |
| Semantic operations executed | 3 |
| Micro-ops executed | 4 |
| Completion events | 1 |

These are semantic accounting counters. They are not cycles, stalls, HBM
transactions, energy, area, PPA, or throughput measurements.

## Reproduction commands

The large checkpoint and generated ROM files remain outside Git. With the exact
snapshot locally available, the evidence chain is reproduced by:

```bash
python3 -m compiler.cli lock-checkpoint --source compiler/models/deepseek-v4-flash-0731/checkpoint_source.json --snapshot "$SNAPSHOT" --output "$EVIDENCE/checkpoint.lock.json"
python3 -m compiler.cli verify-checkpoint --snapshot "$SNAPSHOT" --lock "$EVIDENCE/checkpoint.lock.json"
python3 -m compiler.cli validate-deepseek-v4 --lock "$EVIDENCE/checkpoint.lock.json" --output "$EVIDENCE/checkpoint-validation.json"
python3 -m compiler.cli describe-deepseek-v4-canonical-plan --model-parallel 4 --output "$EVIDENCE/canonical-plan.json"
python3 -m compiler.cli apply-deepseek-v4-canonical-plan --snapshot "$SNAPSHOT" --lock "$EVIDENCE/checkpoint.lock.json" --plan "$EVIDENCE/canonical-plan.json" --output "$EVIDENCE/lookup-canonical" --tensor embed.weight --tensor layers.0.ffn.gate.tid2eid
python3 -m compiler.cli compile-deepseek-v4-lookup-slice --snapshot "$SNAPSHOT" --lock "$EVIDENCE/checkpoint.lock.json" --application "$EVIDENCE/lookup-canonical" --output "$EVIDENCE/lookup-deployment"
python3 -m runtime.service_engine --deployment "$EVIDENCE/lookup-deployment" --inputs "$EVIDENCE/lookup-request.json" --output "$EVIDENCE/lookup-result.json"
python3 -m compiler.cli verify-deepseek-v4-lookup-execution --snapshot "$SNAPSHOT" --lock "$EVIDENCE/checkpoint.lock.json" --deployment "$EVIDENCE/lookup-deployment" --request "$EVIDENCE/lookup-request.json" --result "$EVIDENCE/lookup-result.json" --output "$EVIDENCE/lookup-differential.json"
```

`$SNAPSHOT` must resolve to revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. `$EVIDENCE` must be an
untracked build/cache directory with enough capacity for the selected payloads.

## Explicit non-claims and next gate

This evidence does not establish:

- loading or executing all DeepSeek V4 Flash operators;
- a transformer-layer or end-to-end prefill/decode differential;
- transactional KV, compressed-attention, MoE, or DSpark state correctness;
- generated RTL equivalence;
- hardware timing, HBM behavior, area, power, density, manufacturability, or an
  NVIDIA performance comparison.

The next meaningful executable gate is one checkpoint-derived transformer block
with exact matrix operators, normalization, routing/MoE arithmetic, and
transactional state. Control RTL should be regenerated only after that software
compiler/service-engine path has an independent differential.
