# Safetensors checkpoint-lock fixture

`source.json` declares an immutable fictitious repository revision and the exact
SHA-256 and byte size of every logical file. Tests deterministically generate
two small safetensors shards, their index, and config in temporary directories,
then exercise the exact streaming parser, identity checks, coverage checks,
lock replay, and payload reader used for the official DeepSeek target.

No generated shard is committed, and this fixture is not evidence that a
DeepSeek checkpoint has been downloaded, ingested, classified, or compiled.
