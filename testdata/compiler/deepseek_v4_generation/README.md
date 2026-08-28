# DeepSeek V4 target-only generation control fixture

`greedy_replay.json` is a synthetic executor transcript for the exact control
loop imported from the pinned `inference/generate.py`. It exercises a prefill
call, a decode call, committed mutable-state identities, greedy selection, and
model-generated EOS. Its logits and state hashes name test-double evidence; they
are not real DeepSeek activations or model-execution evidence.
