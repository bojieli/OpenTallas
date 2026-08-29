# Qwen3-8B executable request

`chat_request.json` is a small redistributable host-boundary request for the
full official deployment. It contains no checkpoint values. The pinned local
tokenizer renders it into the Qwen chat protocol; the compiled service then
executes the complete checkpoint and greedy decode loop.

`workload_manifest.json` freezes the exact short differential, chat request,
32-token greedy policy, 8,000-token long-context generator, known answers,
evidence identities, and remaining system gates. Its content-bound workload ID
is `340ec91558350b2e52259bcf9dedd919bd6022473a7ad24318afd99f1e55183e`.

Run it with:

```bash
python3 -m compiler.qwen3 run \
  --deployment /path/to/qwen3-8b/deployment \
  --messages testdata/compiler/qwen3_8b/chat_request.json \
  --max-new-tokens 32 \
  --output /tmp/qwen3-generation.json
```

The request is not a reduced model fixture. It is accepted only by a complete
compiled deployment with all 399 official tensor payloads.
