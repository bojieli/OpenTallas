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
| 38 | `ATTENTION.GQA` | 127 | 131 | complete required metadata admitted, then precise `CAPABILITY` refusal before any write |

Both storage backends carry the same scatter contract digest,
`55f39bccbda65baf6238cfcd93d7bf9959330984af837979870cc019be00e16f`.
The numeric descriptor's first two dtype fields appear in opposite order in
the ROM and HBM deployments; the adapter validates each admitted encoding
rather than assuming one order.

The source words are causally retained RTL results:

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
No synthesizable GQA/softmax datapath is connected yet. Therefore PC 38 is the
first unsupported operation for both Qwen backends.

## Focused evidence

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

## What remains before either release gate passes

Gate 1 is not yet passed. The RTL path must still implement exact GQA dot
products, scaling, stable softmax, and value reduction at PC 38; complete the
output projection, residual, RMSNorm, and MLP across all 36 layers; execute
final norm and the complete vocabulary projection; select the same argmax as
an independent model oracle; append that selected token; repeat ordinary
decode until an official EOS token; and prove no token commits after EOS.
Natural chat and agentic contexts must both pass, including the exact 8,000
natural-token Qwen acceptance context.

Only after that exact execution passes may Gate 2 use its architectural
token-commit ticks. The TPOT report must identify the same deployment, prompt,
generated-token sequence, EOS position, simulator trace, technology view, and
batch size as the correctness result. It must exclude prefill from steady-state
TPOT, report first-token latency separately, preserve per-token distributions
instead of only an average, and never substitute verification cycles, simulator
wall time, a roofline estimate, or a separate cycle-model run for the committed
token intervals of the passing trace.
