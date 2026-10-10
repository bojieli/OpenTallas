# Die-level bench with real ATT / HC / SM (stream hgi-1010/g, 2026-10-10)

Successor of `results/rtl/hgi_e2e_20261009/STATUS.md`: the stubs for HC, ATT and SM are being replaced by the real
unit bodies on the die record buses (`tb_hgi_e2e.sv` REAL_HC / REAL_ATT; SM slice pending).

## HC (unit 10) -- real, DS L0 (1M, rank 0 / 96), vehicle ds_L0_gf (G22 lowering)

| run | result | HC records | RTL service | priced | ratio |
|---|---|---|---|---:|---:|
| `runs/ds_L0_gf_hc_f40k40` | **PASS**: 93/93 dispatches, final VM / HBM exact, token exact | 2 HC_MIX_POST, both exact | 570 + 572 | 540 + 540 | 1.057 |
| `runs/ds_L0_gf_hc_HC_MUT_POST1_f40k40` | **FAIL as required** (pre without + hc_eps: 4 + 4 words wrong) | 2 | | | |

- Unit: `ot_hgi_hc_unit` (W 32; record adapter + post units + r25 Sinkhorn) on the die hc record bus, VM model VLAT 6,
  HBM lane on an in-order KLAT 40 model.
- **HC weight set.** The simulator reads `hc_{attn,ffn}_{fn,scale,base}` from the checkpoint by name and the DS
  compiler reserves only a 1-element BF16 placeholder at B.base, so no weight set exists in the exported HBM.  The
  harness serves the HC lane from `hcw.bin`, written by `tools/hgi_e2e/hc_weights.py` from the released checkpoint in
  the unit's W = 32 weight-set layout (HC_MIX_POST reads only the 4 scale / base sectors).  Compiler item (owner e):
  reserve and fill the 1,966,208 B set at B.base in exactly this layout.
- Needs main's sequencer op table with HC_MIX_ROWS / HC_MIX_POST (a0fb6c743); before it the CP faulted at the first
  HC_MIX_POST (status 3).
