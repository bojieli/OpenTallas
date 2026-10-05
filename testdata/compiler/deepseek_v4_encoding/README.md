# Pinned DeepSeek V4 Flash encoding fixtures

These are the eight byte-exact input and output files published in
`deepseek-ai/DeepSeek-V4-Flash-0731` at revision
`7872f01b1d1fe23eabc4c98b48bffcef5a386062`. They are base64-wrapped so Git
can preserve the upstream files' differing end-of-file newline conventions.
Tests decode with strict base64 validation, then check the exact size and
SHA-256 from `checkpoint_source.json` before using any fixture.

`tokenizer_golden.json` records the exact token count and SHA-256 of the
little-endian uint32 token-ID stream obtained by applying the verified official
tokenizer to each output prompt. The tokenizer payload itself remains in the
external checkpoint snapshot rather than being duplicated in Git.

These small fixtures validate only the official host message wire format. They
do not validate checkpoint payloads, model operators, logits, DSpark acceptance,
or accelerator execution.
