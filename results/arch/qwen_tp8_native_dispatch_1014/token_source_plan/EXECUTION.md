# Native token source checkpoint

The actual checkpoint metadata and small program/constant preflight passed
`oth-ubuntu-612655-1791967047` on AGI with a 4 GB/one-thread reservation,
exit 0. It checks 399 BF16 tensors, derives 38 stages (embedding, 36 decoder
layers, head), eight distinct head rank descriptors and both post-collective
scale operations. The first attempt `611784-1791967013` exited 1 because the
frozen stage lacked its `qwen_o4_fulltoken_binding_w12.py` import; the missing
source was copied before the successful retry.

The native decoder profile has 29 source instructions, 25 explicitly lowered
instructions, two 256-word collectives and 541313 CROM words. Each native head
rank owns 18992 vocabulary rows and an eight-instruction program, including
four real ROM chunks of 6144/6144/6144/560 rows. Its compact code bank is 1600
words. The physical padded scale bank emitted by the existing emitter is
1200 words; `head_geometry.scale_words=1187` describes useful row groups rather
than the allocated final-round padding. Actual head manifests remain the
authority for bank depths.

The payload preparation is separately live on AGI:
`oth-ubuntu-613509-1791967148`, parent session91102, 16 GB/eight threads.
It revalidated all 16 existing layer0/1 rank images, rejected a missing-rank
mutant and an actual transported descriptor high-row-bit mutant, and is
emitting missing layers2–35 and all eight head banks sequentially. No final
all-image result is asserted while this job runs. Read actual progress from
`/srv/opentallas-scratch/codex/qwen-native-layer-1014/token_payload_progress.json`.
The frozen source runner SHA256 is
`23bd8c71086369a1678ab84fe09fd9f76fae343537ecbe2845ef743eefa45c61`;
the preflight source SHA256 is
`7e82fe75f27f86e10263dace039b2914ff1d5ce072e1dc67c5107b4fb783739b`.

This work does not implement the full token engine. In particular, the live
generic fullcore build uses NW16 and has no token embedding bank. A genuine
token successor requires NW18 and INT8_EMBED1, actual source-token addressed
embedding codes/scales, all 36 accepted layer programs, real prior-KV
provenance, no-reset actual VM/X carry, and real head argmax partials with
the production gather/reduction. None of the previous-layer reference
arrays may preload the executed path. HOST token completion must follow those
actual operations and their commit barriers. Fixture/model token responses
cannot release it.

The pending fullcore v6_600 build remains the immediate executed-layer
dependency: EPYC1 PID1392551, intended archive under
`qwen-fullshape-provider-1014/v6_600/full_g3072_su64/obj`. At 75 minutes it was
still computing at 99.9% CPU and about 457.6 GiB RSS, with no usable library.
Do not duplicate or cancel it. Use the composed harness NEXT.md recipe when
its real header/archive exists. Full-token timing and accepted-cost evidence
also require production cached ROM/X-band, physical constant/VM/TT station
composition and a unified clock/cycle measurement with HOST. Generic ideal
ROM simulation, separate collector invocation, component cycles and cold
prefill ratios cannot establish the owner's 5%/15% cost gates.
