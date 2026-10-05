# Pinned Qwen3-8B compiler target

This directory binds the production Qwen compiler path to
`Qwen/Qwen3-8B` revision
`b968826d9c46dd6066d109eabc6255188de91218`. The source declaration pins
all five BF16 checkpoint shards and every locally required release artifact.
Remote checkpoint code is disabled; the executable semantics are implemented
and verified in `compiler/qwen3`.

The product context limit for this build is exactly 8,000 total tokens even
though the checkpoint declares a larger position allocation. A prefill plus
decode sequence that would exceed 8,000 tokens must fail before any KV state is
mutated.

`config.json` is a semantic mirror of the upstream 728-byte file with one final
repository newline. Its parsed fields are checked exactly. The official byte
hash remains pinned in `checkpoint_source.json`; checkpoint locking consumes
the original snapshot file, not this mirror.

The separate reference-source lock identifies the Transformers 4.51.0 commit
and exact Qwen3 source files used to recover operator ordering. Those files are
source evidence only: the compiled service engine does not execute remote code
or import Transformers.
