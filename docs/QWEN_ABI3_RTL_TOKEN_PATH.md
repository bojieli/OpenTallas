# Qwen ABI 3.0 RTL token path

**Release-gate order:** exact output tokens through EOS first; TPOT from that
same passing execution second.

This document records only work that is causally on the synthesizable Qwen
ABI 3.0 path. A bounded arithmetic or memory operation is useful dependency
evidence, but it is not a decoded token and its simulator wall time or testbench
cycle count is not TPOT.

## Current exact boundary

The shared shipped-prefix witness executes Qwen decode through PC 29 and
produces the exact layer-zero key RoPE result. The focused continuation in
`rtl/abi3/ot_a3_qwen_kv_scatter_adapter.sv` now consumes the real Qwen ROM and
HBM instruction and descriptor records at:

| PC | operation | ROM operator | HBM operator | result |
|---:|---|---:|---:|---|
| 32 | `DMA.SCATTER` key append | 111 | 114 | exact 1,024-code row appended at logical row 16 |
| 35 | `DMA.SCATTER` value append | 118 | 120 | exact 1,024-code row appended at logical row 16 |
| 38 | `ATTENTION.GQA` | 127 | 131 | exact fixed-context-17 arithmetic; 4,096 BF16 words match the independent oracle on ROM and HBM |
| 41 | `TENSOR.MATMUL` | 134 | 137 | next shipped operation; output-projection RTL is not connected |

Both storage backends carry the same scatter contract digest,
`55f39bccbda65baf6238cfcd93d7bf9959330984af837979870cc019be00e16f`.
The numeric descriptor's first two dtype fields appear in opposite order in
the ROM and HBM deployments; the adapter validates each admitted encoding
rather than assuming one order.

The source words are causally retained RTL results:

- query: PC 26 `VECTOR.ROPE`, BF16 payload SHA-256
  `f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150`;
- key: PC 29 `VECTOR.ROPE`, BF16 payload SHA-256
  `b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406`;
- value: PC 17 `TENSOR.MATMUL`, BF16 payload SHA-256
  `b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5`.

For each of four successful backend/plane cases, the campaign compares all
17,408 active logical-plane words: 16,384 prior words remain unchanged and the
1,024 words at row 16 are replaced. Prior rows intentionally contain nonzero
deterministic data so preservation cannot pass through an all-zero accident.
The compact logical plane is a verification mapping of the ABI view's
2,048-element interleaved physical row and its key/value offsets of 0/1,024.

The exact PC 38 GQA metadata has query shape `[1,32,128]`, key/value cache
shape `[8256,8,128]`, active context length 17, scale bits `0x3db50000`, and
contract digest
`623af598461a17f0b15fb564380a7b8de0bf3f8c89a0833947ad9ed8872ce181`.
The new synthesizable datapath implements only that exact context-17 decode
geometry. It performs ordered QxK products, BF16 score and probability
boundaries, stable softmax through the shared correctly rounded exponential and
divider, the specified eight-lane denominator reduction, ordered probabilityxV
reduction, and complete-result buffering before publication. The next shipped
operation without a connected datapath is PC 41 output projection for both
backends.

Only the current query, key, and value row is authentic. No authentic retained
KV rows for positions 0 through 15 were available, so the focused arithmetic
campaign uses deterministic rotations and reversals of the authentic current
row for that history. This is honest operator-level arithmetic evidence, not an
authentic context-17 model history and not token evidence.

## Focused evidence

### KV-scatter evidence

`results/rtl/a3_qwen_kv_scatter_campaign.json` is the machine-readable
authority. Its focused campaign contains:

- four complete scatters, 4,096 moved BF16 codes and 73,728 observed writes;
- 69,632 destination words compared, including 65,536 preservation checks and
  4,096 replacement checks;
- exact PC 38 metadata admission for ROM and HBM followed by zero-write
  capability refusals;
- instruction-CRC, late descriptor-CRC, valid-CRC wrong object, wrong shape,
  wrong numeric contract, and out-of-active-context index negatives, all with
  zero writes;
- 209,076 checks in Icarus and the same 209,076 checks in pinned Verilator
  5.050, with normalized observations identical;
- generic Yosys 0.68 elaboration of the adapter, descriptor validator, and DMA
  mover. The instruction-decoder interface is stubbed only for this Yosys
  frontend check because that pinned frontend cannot parse the qualified
  decoder's package import; both simulators execute the real instruction
  decoder and its CRC logic.

Reproduce only this focused lane with:

```sh
python tools/build_a3_qwen_kv_scatter_vectors.py
python tools/run_a3_qwen_kv_scatter_rtl_campaign.py
python -m pytest -q tests/compiler/test_a3_qwen_kv_scatter_rtl.py
```

### Context-17 GQA evidence

`results/rtl/a3_qwen_gqa_campaign.json` is the machine-readable authority for
PC 38. The source-current campaign records:

- one exact ROM case and one backpressured HBM case, each comparing all 4,096
  computed BF16 output words with an independent scalar reference; the shared
  expected payload SHA-256 is
  `8992e9d1a0b5303b81b2503df2e23170f838f772e79eb8d7c65c1fce4fac93c2`;
- 8,192 computed-word comparisons and 12,288 atomic sentinel checks in total;
- per successful case, 143,360 memory reads, 69,632 score multiplications, 544
  exponential evaluations, 69,632 value multiplications, and 4,096 writes;
- a late-final-value nonfinite fault after all preceding arithmetic with zero
  writes, a valid-CRC wrong numeric contract with zero reads and writes, and an
  instruction-CRC corruption with zero descriptor records, reads, or writes;
- 20,565 checks in Icarus and the same 20,565 checks in pinned Verilator 5.050,
  with all normalized case records identical; and
- generic Yosys 0.68 elaboration with zero reported structural problems. This
  is synthesizable-frontend evidence only, not library mapping, timing, area,
  power, or a characterized process result.

Reproduce only this focused lane with:

```sh
python tools/build_a3_qwen_gqa_vectors.py
python tools/run_a3_qwen_gqa_rtl_campaign.py
python -m pytest -q tests/compiler/test_a3_qwen_gqa_rtl.py
```

The campaign's 471,054- to 718,949-cycle case counts and its host wall times
measure verification cost. They are neither architectural token-commit ticks
nor TPOT.

## What remains before either release gate passes

Gate 1 is not yet passed. The fixed context-17 PC 38 result must be generalized
to every required position through the exact 8,000-token context without
changing the numeric contract. The RTL path must continue at PC 41; complete
the output projection, residual, RMSNorm, and MLP across all 36 layers; execute
final norm and the complete vocabulary projection; select the same argmax as
an independent model oracle; append that selected token; repeat ordinary
decode until an official EOS token; and prove no model transaction or token
commit occurs after EOS. Natural chat and agentic contexts must both pass,
including the exact 8,000-natural-token Qwen acceptance context.

Only after that exact execution passes may Gate 2 use its architectural
token-commit ticks. The TPOT report must identify the same deployment, prompt,
generated-token sequence, EOS position, simulator trace, technology view, and
batch size as the correctness result. It must exclude prefill from steady-state
TPOT, report first-token latency separately, preserve per-token distributions
instead of only an average, and never substitute verification cycles, simulator
wall time, a roofline estimate, or a separate cycle-model run for the committed
token intervals of the passing trace.
