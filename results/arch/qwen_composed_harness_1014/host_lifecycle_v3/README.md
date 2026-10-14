# HOST token lifecycle gate v3 (component, numerical engines absent)

ot-run unit oth-ubuntu-2999460-1791985924 on ot-epyc4, exit 0. Source branch claude/qwen-wholetoken-1014
(tools/qwen_native_host/host_lifecycle.hpp, host_lifecycle_gate.cpp, run_lifecycle_gate.sh); archives are the
existing full8bb9a6c00-compiledO1 HOST, boardd4a77a6c7, allocator and cohort models (hashes in inputs.sha256).

- positive PASS: dispatch 21388, latched PRE_TERMINAL accepted-traffic certificate 22944 (accessor bbc4, tag-bound,
  after last board stimulus), one credited head37 result pulse 23388, allocator+cohort terminal accepted 23389,
  8 endpoint result credits, HOST0 CQ published by the original two DMA writes at ring 0x800
  (word0 0xc7320000cafe0025 = token 0xc732 = 50994, tag 0xcafe), IRQ observed, POST_TERMINAL certificate 27902
  (host_last_descriptor_retired on HOST0 + all-8 transport/board drains), typed retirement 27903, warm_ready again.
- strict (negative control: HOST must show native active==0 before the terminal) never completes: blocked on
  HOST0 u_native.active -- the deadlock the lifecycle avoids.
- stale (negative control: POST certificate with wrong generation) FAILS: "stale POST_TERMINAL retirement certificate".

Fixtures: result token/value and KV/VM/collective drains (no numerical engines), board/BOOT stimulus.
Not a whole-token result. v1/v2 diagnosed that CQ publication is the DMA ring write, not the class5 completion word.
