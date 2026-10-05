# Qwen3-8B executable compiler

This package is an isolated, production-oriented implementation of the
OpenTallas executable path for the exact `Qwen/Qwen3-8B` release at revision
`b968826d9c46dd6066d109eabc6255188de91218`. It does not import or modify the
DeepSeek adapter.

The enforced product boundary is batch-one causal prefill and autoregressive
decode with at most 8,000 input/KV positions. The graph includes the input
embedding, all 36 decoder layers, GQA attention and mutable KV state, both MLP
branches, final normalization, and the untied 151,936-row output head.

```text
pinned five-shard checkpoint
  -> 399-tensor shape/role contract
  -> 616-node semantic graph
  -> 617 fixed-width CRC-protected instructions
  -> 36 aligned BF16 physical images
  -> independent byte-for-byte inverse reconstruction
  -> independently certified 617-slot execution schedule
  -> artifact-only stage-streaming service engine
  -> independent Transformers 4.51.0 differential
```

The engine interprets generated microcode and memory-maps only generated ROM
images. It never opens the source checkpoint, imports Transformers, or reads a
known-answer file. The independent reference runner does the converse: it reads
the original official safetensors and executes the pinned official source one
layer at a time without reading generated images or compiler instructions.

## Reproduction

Set paths to the complete content-pinned Hugging Face snapshot and a build
volume with at least 17 GB free:

```bash
QWEN_SNAPSHOT=/path/to/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218
QWEN_BUILD=/path/to/qwen3-8b-build

python3 -m compiler.qwen3 lock-checkpoint \
  --snapshot "$QWEN_SNAPSHOT" \
  --output "$QWEN_BUILD/checkpoint.lock.json"

python3 -m compiler.qwen3 compile \
  --snapshot "$QWEN_SNAPSHOT" \
  --lock "$QWEN_BUILD/checkpoint.lock.json" \
  --output "$QWEN_BUILD/deployment"

python3 -m compiler.qwen3 verify-deployment \
  --deployment "$QWEN_BUILD/deployment" \
  --output "$QWEN_BUILD/inverse-replay.json"
```

Tokenize and run full greedy decoding from the compiled deployment:

```bash
python3 -m compiler.qwen3 run \
  --deployment "$QWEN_BUILD/deployment" \
  --text 'Hello' \
  --max-new-tokens 16 \
  --device cuda \
  --output "$QWEN_BUILD/generation.json"
```

The ordinary compiler environment uses the repository-pinned
`tokenizers==0.22.2`. The independent source differential must run under the
separately pinned Transformers 4.51.0 environment:

```bash
python3 -m venv --system-site-packages "$QWEN_BUILD/reference-venv"
"$QWEN_BUILD/reference-venv/bin/python" -m pip install \
  'transformers==4.51.0' 'tokenizers==0.21.4'

"$QWEN_BUILD/reference-venv/bin/python" tools/run_qwen3_release_gate.py \
  --deployment "$QWEN_BUILD/deployment" \
  --snapshot "$QWEN_SNAPSHOT" \
  --generated-tokens 32 \
  --long-context-tokens 8000 \
  --output "$QWEN_BUILD/release_gate.json"
```

The release runner refuses a different installed Qwen source hash. It requires
zero absolute error over the full vocabulary and exact post-layer BF16 hashes
for prefill, at least 32 cached greedy-decode spans, and the 8,000-token
boundary. It rejects a different long-context length and refuses to overwrite
an existing evidence path.

## Evidence boundary

This path establishes complete checkpoint ingestion, deterministic physical
images, inverse reconstruction, functional microcode execution, KV state
transitions, complete logits, local tokenizer/chat formatting, and an exact
official-source differential on the declared PyTorch/CUDA backend. It does not
claim target-node timing, power, mask-ROM manufacturability, or complete
operator RTL. Those remain separate physical and RTL gates in the system
recovery plan.
