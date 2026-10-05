# Qwen3-8B ROM band-slab port-group element: M1-M5 check (Option A), 2026-10-04

## Verdict: FAIL. The element does not close in its slab share, not even with M7 routing.

The element is `rtl/physical/ot_qwen_slab_port_group.sv`. It is one of the eight port groups a band port/scale slab replicates:
- 16 scale ROM banks;
- post-scale FP32 multiply;
- argmax leaves;
- the block-word mesochronous FIFO.

The bench `rtl/test/tb_qwen_slab_port_group.sv` passes: 1,505 requests bit-exact against `ot_hdc_fmul` (MUL_LAT 6).

The element was placed and routed with ORFS ASAP7 in its slab share, 777.576 × 342.9 µm. That is 2.133 mm² / 8, the die abstract's port/scale slab divided by 8.

| case | max routing layer | MUL_LAT | design area / util | result |
|---|---|---:|---|---|
| m5_l6 | M5 | 6 | 141,170 µm² / 54 % | FAIL at CTS: hold repair hit RSZ-0060 "max buffer count" after inserting 31,278 hold buffers; SS WNS −180 ps during repair |
| m5_l7 | M5 | 7 | 140,395 µm² / 54 % | FAIL at GRT: congestion 39,223 (max H 19 / V 32) |
| m7_l6 (control) | M7 | 6 | ≈141,000 µm² / 54 % | FAIL at GRT: congestion 14,114 (max H 18 / V 20) |

**Reading.**
- The share is not enough for this content at any of the routing limits tried.
- Even the M7 control fails global route, so the die abstract's slab area (port_tiles 11.229 + scale_rom 14.359 mm² over 12 slabs) is under-provisioned for the real element. This holds independently of the entry-layer question.
- Option A (slab abstract with OBS M1-M5) is therefore not adopted. The die GRT with that abstract was also worse (b3r15A i5: 16,187 overflow, M8 1.47 / M9 1.60).
- The die closed with Option B (an M6 entry strip). See `results/rtl/qwen_rom_fulldie_20261003/b3r3/README.md`.
- **Open item:** the slab element needs a larger frame, or a re-split of the scale ROM banks, before the die's slab area can be called implemented. Die area is not scarce: the margin is 46 mm².

Remote: `ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-slab-m5/runs/*` (ORFS work dirs, logs).
