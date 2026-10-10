# DS-V4.1 ROM MTP seed projection, production slice (dsrom_mtp_seed_projection_full15360), mtp-lead 2026-10-09

Element: `mtp.0.main_proj` (5120 x 15360 FP8 + UE8M0 block scales), input the HC mean of layers 37/38/39
(3 x 5120 BF16), output 5120 FP32 roots rounded once to BF16 (before main_norm).

## What was built

- `rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_ctl.sv` (the routed block): 240-beat 64-lane BF16 intake, two
  `ot_hdc_actquant` FP8 quantisers, a 4-SRAM activation buffer (480 blocks, banked so the two writes and the two
  stream reads of a cycle never share a macro), the K segmentation the 13-bit native descriptor needs (four aligned
  phases K = 4096/4096/4096/3072), the element's fences at its registered pins, the ordered reduction
  (r0 + r1) + (r2 + r3) on one LAT8 `ot_v41_fadd` per row (join of row pair rp hidden behind the phases of rp + 1),
  BF16 RNE once. Sticky fault word (element, join, protocol, quantiser).
- `rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_desc.sv`: generated (`tools/dsrom_mtp_seed_proj.py desc`) 4 x 25 config
  words + 480 stream words. Row pair rp uses the same words with rp x 480 added to word 0 [41:29] (segment base)
  and word 16 [19:6] (PP first word index); the generator asserts this for every row pair (checked RP 8: 3,840 of
  4,096 ROM words), so one descriptor serves every row pair of an element.
- `rtl/dsrom_sys/mtp/ot_dsrom_mtp_seed_proj.sv`: ctl + the native q-element `ot_v41_rom_elem_q_qxpq_w10` at the
  selected QS5f parameters (separately hardened). 5120 rows = 5120 / (2 RP) slices.

## Exact gate (Verilator 5.050, ot-epyc1tb, released fixture of the Codex QS5f gate, provenance in this folder)

| Run | Result | Cycles |
|---|---|---|
| pos (RP 8 = rows 0..15, two tokens back to back) | **PASS**: 32/32 FP32 roots and BF16 outputs bit-exact vs the chunk8 golden, no fault | 11,780 per token, first x beat to done |
| pos_rp1 (RP 1, rows 0..1, two tokens) | **PASS** | 1,749 per token |
| mut (MUT_JOIN = 1: sequential ((r0 + r1) + r2) + r3) | **FAIL as required**: rows 2, 9, 11, 13, 14 FP32 roots differ by 1-8 ulp | — |

Note on the mutant: the five changed FP32 roots still round to the same BF16 values; the gate compares the FP32
root, so the ordered reduction is the contract.

Cycle model from the two measured points: T(RP) = 316 + 1,433 x RP cycles per token (240 intake + quantiser tail +
last join in the constant; per row pair: four serial aligned phases on the native element, its fences and quiet
time). The 44 source files' sha256 are in each record.json and match the commit.

## Open

- Routes: mtp-seedproj-{a 440x340 HM 0, b 400x320 HM 10 ps}-7c1939686-tc (ctl only; the native element's own
  closure is the S81 q-element stream's).
- The activation quantiser `ot_hdc_actquant` routed alone at 0.9 ns; its 773 ps TT headroom route was -92 ps.
  If it limits this block, the next variant splits its critical stage.
- Phase overlap (configure phase n + 1 during phase n through the PQ shadow) is not used: serial phases, as the
  Codex pin-level gate. That is the lever if the per-row-pair 1,433 cycles matter.
- Not in this slice: HC mean producer, main_norm, the rank gather of the 5120 rows, six-position sharing.
