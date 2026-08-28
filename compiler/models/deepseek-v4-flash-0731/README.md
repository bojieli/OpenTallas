# Official DeepSeek V4 Flash compiler target

`checkpoint_source.json` binds the public
`deepseek-ai/DeepSeek-V4-Flash-0731` release at immutable Git revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. It records the SHA-256 and exact
byte size of all 48 safetensors shards and all 26 non-shard files, including the
checkpoint index. The values were reconciled against the pinned Hugging Face
Git/LFS objects and the already governed inventory in
`data/inventory/deepseek-v4-flash-0731.json`.

The compiler never executes release Python as remote code. Those files are
content-bound semantic references for an independently implemented front end.
Once a complete local snapshot exists, `lock-checkpoint` streams and validates
every byte, every header, all 72,317 tensor assignments, and the declared
166,878,536,440 payload bytes before emitting a lock.

This source contract establishes checkpoint identity and loadability. It does
not claim operator-complete inference, numeric equivalence, compiled scheduling,
RTL execution, or performance closure; those remain separate end-to-end gates.
