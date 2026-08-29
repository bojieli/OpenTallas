# DeepSeek V4 shared vocabulary-head reference evidence

- **Evidence date:** 2026-08-29
- **Qualified boundary:** target-precision `LM_HEAD` reference semantics
- **Official model:** `deepseek-ai/DeepSeek-V4-Flash-0731`
- **Official revision:** `7872f01b1d1fe23eabc4c98b48bffcef5a386062`
- **Reference profile:** `opentallas.deepseek_v4_lm_head_binary32.v1`
- **Independent service profile:** `opentallas.deepseek_v4_lm_head_service_binary32.v1`
- **Graph contract at qualification:** `5c7f52fefc72c306d27f0fd86d4bc0c18ad003a31983213d06a0bae173c54322`

## Qualified boundary

The released model has one untied vocabulary matrix shared by the main model
and DSpark. The checkpoint tensor `head.weight` is BF16 `[129280,4096]`, while
`ParallelHead` deliberately creates its runtime parameter as binary32. Loading
therefore widens each BF16 checkpoint value exactly. The finite BF16 hidden
input is likewise widened exactly before one bias-free projection.

This head is not covered by the released routed-weight MXFP4 or dense/shared
FP8 matrix formats. Its official checkpoint storage is BF16 and its runtime
arithmetic/output is binary32. The deterministic target forms each exact BF16
product in increasing hidden-column order and performs one binary32 RNE fused
product-add per column. It returns the completed binary32 accumulator with no
BF16 output conversion.

The two graph sites differ only in position selection:

| Site | Source behavior | Qualified output shape |
|---|---|---|
| `main.lm_head` | `full_logits=False`; select only source position `S-1` | `[B,129280]` binary32 |
| `dspark.lm_head` | `full_logits=True`; project all five DSpark positions | `[B,5,129280]` binary32 |

The complete reference accepts rank-ordered contiguous vocabulary shards for
world sizes 1, 2, 4, and 8. Rank `r` owns one equal contiguous interval along
the vocabulary axis. The released all-gather followed by increasing-rank
concatenation reconstructs global token order; it is not a numerical reduction
across ranks. The selected-row API retains the same declared topology while
evaluating only explicit global rows for bounded evidence.

Final HC reduction and RMS normalization are upstream operations. Sampling,
DSpark Markov-bias addition, and the autoregressive loop are downstream and are
not part of this qualification.

## Source and checkpoint authority

The tests re-read the pinned files before checking the exact constructor,
position-selection, binary32 projection, all-gather, concatenation, and DSpark
call expressions:

| Official artifact | SHA-256 |
|---|---|
| `inference/model.py` | `c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f` |
| `inference/convert.py` | `6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe` |
| `inference/generate.py` | `775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812` |
| `inference/config.json` | `c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71` |
| `model.safetensors.index.json` | `98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b` |

The governed checkpoint lock is
`30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760`.
The complete tensor occupies 1,059,061,760 bytes and has identity:

```text
029e3c5293b29cc426e21d87795e15efa4d363f27b2bc4a9e3aef7d79f047919
```

The release converter partitions the vocabulary axis into equal contiguous
rank shards. A complete MP=4 reconstruction produces four `[32320,4096]`
BF16 payloads of 264,765,440 bytes each:

| Rank | Global vocabulary rows | SHA-256 |
|---:|---:|---|
| 0 | `0..32319` | `517371776bf297a7c1fba6317c04649c8080841cf0107d3395b23559b8540ee1` |
| 1 | `32320..64639` | `a0e8f1115ad0ce49a7ec27af80017abe5beff4ac0fde26cfaf1ff6fbb7d217ba` |
| 2 | `64640..96959` | `ea93b80dcc8940969e20c481de389f85709ea9b015a02a28540719e77c7cd494` |
| 3 | `96960..129279` | `abbeab307dd4d6cf87f0d38106032743af343954a9671deec6960a0384e089c4` |

The official-payload test streams every one of the 1,059,061,760 source bytes,
reconstructs all four partition hashes independently, and rejects any BF16 NaN
or infinity. This is complete storage/provenance evidence. It is not a complete
vocabulary projection.

## Complete bounded operator evidence

Small complete operators exercise behavior that a selected-row audit cannot:

- main mode uses two batches, two source positions, hidden width three, eight
  vocabulary rows, and four rank shards; changing an excluded nonfinal source
  position cannot enter the result;
- DSpark mode uses the full five-position block, hidden width two, and four
  complete vocabulary rows; every position is projected through the same head;
- an increasing-K cancellation sentinel distinguishes one binary32 rounding per
  product-add from a one-round exact dot product;
- complete-shard tests reject missing, empty, or unequal vocabulary partitions;
  and
- randomized complete/selected cases compare against a separately assembled
  exact-rational binary32 composition.

These tests qualify complete operator shape, ordering, rounding, topology,
atomic poison, and immutable-result behavior at bounded dimensions. Reduced
dimensions do not establish execution of the complete official head.

## Full-width official selected-row evidence

Eight global rows cross both sides of every MP=4 partition boundary:

```text
0, 32319, 32320, 64639, 64640, 96959, 96960, 129279
```

Every row is read at its full hidden width of 4,096 BF16 values and independently
checked against its frozen row hash:

| Global row | MP=4 rank/local row | SHA-256 |
|---:|---:|---|
| 0 | `0/0` | `162f09c5797bcba1555a099a5de9da5761b0fc34d04022dbeef8eb50f406757e` |
| 32,319 | `0/32319` | `e1a8c0455e9fce11d63f5df882b85df0f5fe4bc157676f4f238d0dc03e4bdc96` |
| 32,320 | `1/0` | `aefdc3bbc727717d741b9c57e9b6b3483e409c7ceef0c28599ea982e91ebf7a3` |
| 64,639 | `1/32319` | `679fcaf5960da3188e7d1aa49ee01387636b195b9c8eee0b32892bf55dcb3295` |
| 64,640 | `2/0` | `d6ecd4976ad1af6c2a8ebefd3f8b48f1055372be10b048582524c3f7256c7672` |
| 96,959 | `2/32319` | `c1e117f1bc5c3c224c108c1f5945c1420744521a08a35669f05994048111f28c` |
| 96,960 | `3/0` | `24c00c267308a4c26f6262fabe82e6b2449e17343b7a3dbb53275e5387dedc41` |
| 129,279 | `3/32319` | `e91cbbddc23effa754f3c3a4635defe39e803ed3b550cb0ff3a45df135a9ac0a` |

A deterministic full-width synthetic BF16 hidden row then produces the
following increasing-K binary32 logits in global vocabulary order:

```text
0xC095C958
0xC1D054DE
0x418C15E0
0xC076B7DE
0x41D56672
0x414F357C
0x403C3AB0
0x412A990C
```

The retained input/resource/output identities are:

| Evidence stream | SHA-256 |
|---|---|
| selected synthetic hidden row | `0b188d698a9e5f29a5ce4795ef0359b6256989aff373d53b8d3932d9ab19f734` |
| eight selected official weight rows | `b6ccb6bb100c580f786df921c978bd43b813addb9d6bd3d837921c048dae13fa` |
| eight binary32 logits | `39eee776802412be8ad32c2d9ac21b76c8eac8385d7112cb6caa4acc64536514` |

This evidence combines real official weights with a synthetic hidden input. It
must not be described as a checkpoint-derived model activation or end-to-end
logit result.

## Independent selected-row differential

`runtime/service_engine/lm_head_numeric.py` independently implements finite
BF16 validation, exact widening, increasing-K binary32 arithmetic, vocabulary
ownership, and logical accounting. It imports neither compiler nor runtime
reference code. For all eight full-width official rows it matches every
binary32 code and every rank owner exactly. Randomized reduced cases separately
compare the reference to an exact-rational composition.

The service lane intentionally accepts at most 20 evidence rows. It does not
authenticate the checkpoint, read generated deployment artifacts, execute the
complete vocabulary, issue a physical collective, or change the graph's
service-engine status. It is functional selected-row numeric evidence only.

Public reference results retain source hashes, output codes, topology, and
logical counters rather than the potentially 1.06-GB weight payload. Their
structural validation detects result mutation, but public construction alone
cannot prove checkpoint provenance or recompute all dot products.

## Logical accounting boundary

For batch `B`, input sequence length `S`, projected positions `P`, evaluated
vocabulary rows `V`, and hidden width `K`, a successful transaction reports:

```text
source_hidden_bf16_values_validated = B * S * K
selected_hidden_bf16_values_read    = B * P * K
selected_weight_bf16_values_read    = V * K
exact_product_accumulates           = B * P * V * K
binary32_accumulation_roundings     = B * P * V * K
binary32_logits_written             = B * P * V
logical_gathered_binary32_values    = B * P * V
transaction_commits                 = 1
```

`P=1` for the main head and `P=S=5` for the graph-qualified DSpark head. Input
and weight widening counts reflect logical unique values in this semantic
operator, while product counts reflect every output dot product.

These are not physical traffic or performance counters. They do not select ROM,
SRAM, HBM, cache, NoC, or link placement and do not describe actual reads,
writes, bursts, reuse, flits, instructions, cycles, latency, bandwidth,
inference bytes/s, throughput, power, energy, area, routing, or PPA.

## Reproduction

```bash
pytest -q \
  tests/runtime/test_deepseek_v4_lm_head.py \
  tests/compiler/test_deepseek_v4_graph.py

ruff check \
  runtime/reference/lm_head.py \
  runtime/service_engine/lm_head_numeric.py \
  tests/runtime/test_deepseek_v4_lm_head.py \
  compiler/frontend/deepseek_v4_graph.py \
  tests/compiler/test_deepseek_v4_graph.py
```

The complete payload and selected official-row cases require the pinned local
checkpoint. Without it, those cases skip; complete small operators, randomized
arithmetic, poison, immutability, topology, and physical-nonclaim tests remain
runnable.

## Explicit nonclaims

This qualification does not establish a checkpoint-derived hidden activation,
complete official 129,280-logit numeric execution, final HC/RMS execution,
sampling, Markov bias or autoregressive-loop semantics, a complete generation
step, artifact-driven service execution, physical all-gather, compiler image or
placement, schedule, RTL, physical ROM/SRAM/HBM traffic, cycles, latency,
bandwidth, inference bytes/s, throughput, power, energy, area, PPA,
manufacturability, task quality, or GPU advantage.
