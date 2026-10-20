# HBM-QINT8B (10-20): wide INT8 SM front -- 128 INT8 codes/edge, measured

## Lever
The narrow INT8 path (`ot_smh_static_int8`, HBM-QINT8) widens one packed 128-code line into two BF16 lines on two edges, so
Qwen INT8 was SM-front bound: 136 edges per 64-line block (64 codes/edge), not HBM-bound.

The wide front (`rtl/hbm_accel/sm/attn/ot_hbm_sm_i8w_front.sv`) is opt-in: `ot_hbm_accel_smh_attn #(.INT8W(1))` passes it
through `ot_hbm_sm_attn_front_static #(.INT8W)`. Both default to 0, which gives the previous netlist and behaviour; the 0
default is shown below to reproduce the narrow-path cycles exactly. It uses no new arithmetic and changes no tile, XS,
tcl, tct or BE master. The SM row bundles already go to the two column sides separately (rl -> columns 3..0, rr -> 4..7), and
a single-vector matvec uses one x column per side. Command mode 3 was a free encoding (a schedule fault before this
change). It marks one packed line as two rows of one chunk:
- the low 64 codes are row A, sent to the left side with x in column 0;
- the high 64 codes are row B, sent to the right side with x in column 4.

Both halves are widened by the real `ot_hbm_accel_int8_line` arithmetic: 128 lanes, two registered stages (classify, encode).
They launch as ordinary fmt-0 BF16 row bundles at command+2. Exactness is therefore the fmt-0 path's: codes are exact in BF16,
products are exact in FP32, and each row keeps its own golden chunk8 csum. While the result mode is set, rdata column 1 carries
column 4 (row B), so the VM writer stores B as slot 1.

## Compiler contract
The production compiler must follow this contract. It is implemented in the bench compilers `qwen_sm_mv_unit.compile_int8w`
and `toksim_smhbm` `TOKSIM_QWEN_MODE=int8w`.
- **Row pairing.** An op's R rows pair as A = r and B = r + Rh, with Rh = ceil(R/2). The slot order is the narrow compiler's
  wave order over the A items. One packed line goes out per edge, and each word reads its own line.
- **No mark or offset.** There is no svg bit 118 mark and no converter offset: the svg S1 copy sees the raw packet, exactly as
  in non-INT8 mode.
- **Descriptors.** Descriptors carry mode 3 (xc mrel substitutes it on every magic word) and fl 0 (no format launch).
- **Block.** A block is one wave: 8 A-items x 8 t = 64 packed lines, a 64-word programme.
- **x columns.** x goes into columns 0 and 4. On the die that means x-load p = 5 parts with stride 0 (nb 8 beats vs 2);
  double-buffer it under the previous op (the VMEARLY rule).
- **VM writer.** Use VM writer descriptor P = 2 and pair B = A + 8 x stride_row (SM-local), so slot 1 is B's natural VM
  address. This needs Rh % 8 == 0, which holds for every Qwen TP-8 shape except the LM head tail (pad it).
- **rmode.** rmode is cleared by the next non-dual valid word or attention word. Start the next op only after the previous
  op's results are out (OP_GAP).
- **Svg bit 118.** Bit 118 is only needed for the NARROW path (`ENABLE_INT8` mark). The production compiler sets it on narrow
  packed reads (toksim `qwen_block_programme` does); the wide path needs none.

## Evidence (Verilator 5.050, unpinned ot-run, ot-epyc5)
### SM unit (`qwen_sm_mv_unit.py run --i8w`, real Qwen3-8B L0 rank-0 weights, SM-0 block)
Bench: `unit/L0_i8w_pos.json`. All four shapes PASS bit-exact (columns 0 and 1 against the golden). The narrow regression
(`unit/L0_narrow_reg.json`) uses this tree's INT8W = 0 front_static and reproduces the SMB-INT8 baseline exactly.

| shape | wide (cycles) | narrow regression (cycles) |
|---|---:|---:|
| qkv | 1661 | 3206 |
| o | 1128 | 2161 |
| gu | 6269 | 12422 |
| down | 3197 | 6278 |

### Die composition (`tb_toksim_smhbm -DTOKSIM_I8W`, MC3 successor PC, rotated, TP-8 rows)
Runs are in `runs/`. All are PASS bit-exact at pace 80/64+8.

| shape | wide span (cycles) | narrow span (cycles) |
|---|---:|---:|
| qkv48 | 2213 | 3390 |
| o128 | 1495 | 2288 |
| gu192 | 8549 | 13182 |
| down128 | 4325 | 6654 |

The wide front is HBM-bound at 88 edges per 64-line block. At p72 and p64 the svg cdc faults (the controller cannot supply
faster), and those runs are kept as evidence.

### Witnesses (`witness/`)
Every witness FAILs, with its run log alongside:
- compiler: wbit (golden), halfswap (golden), nopkt (schedule_fault 856), late (schedule_fault), tag (schedule_fault 857);
- RTL: sign `OT_I8W_MUT_SIGN` (golden), noswap `OT_I8W_MUT_NOSWAP` (column 1 wrong), half `OT_I8W_MUT_HALF` (golden);
- die: `wm8_halfswap` (48/48 bad).

## Rate (census `--measured --bw 98 --bridge 1`, info_banklat_all, HBM-PRETREE3 basis m_pt3_tp8 + SM.MATVEC swapped)
`census/smhbm_int8w.json` holds the wide units. The LM head comes from the affine law (101 fixed + 88/block). Rates follow the
HBM-SUFIX delta rule.

| Qwen SM.MATVEC | Qwen (tok/s) | DS (tok/s) |
|---|---:|---:|
| wide INT8 front (measured) | 1,001.5 | 1,148.8 (unchanged) |
| narrow INT8 (measured, `smhbm_int8`) | 775.0 | 1,148.8 (unchanged) |

The wide front is worth +29% on Qwen. The PRETREE3 Qwen row of 1,000.7 used the BF16w law for SM.MATVEC; the wide front
now backs that row with a measurement.

## SAFE-DESIGN checklist (`ot_hbm_sm_i8w_front`, part of the SM parent soft logic; no tile kit changes)
1. **Pins: PASS.** Every output launches from a register: 8 row_launch instances, and rdata comes from the front's existing
   result registers plus one 2:1 mux on column 1. Inputs are the SM's existing command and packet ports. No new ports.
2. **Reach: PASS.** The logic is local to the SM front, next to the existing attention row launch.
3. **Fanout: PASS by construction; census owed.** The 6,544-bit pin mux select uses 206 kept copies, fed by 8 kept stage-1
   copies (<= 26 loads each). rmode has 2 kept copies (16 loads each). Packet bits feed 1 classify each. The mapped native32
   census is owed at the SM parent's next synthesis and gate (owner HBM-SMATT5 / HBM-DIE6).
4. **Depth: PASS.** classify (8-bit negate + 8:3 priority) and encode (3-bit shift + zero test) sit in separate stages, as in
   `ot_hbm_accel_int8_line` PIPE 1.
5. **Storage: PASS.** Pipeline registers only: 1,536 classify + 6,544 launch flops. No arrays and no delay lines.
6. **Floorplan.** The front strip grows by about 9k flops and 128 lane converters; the SM parent outline review is owed.
7. **Clock: PASS.** The SM stream clock, the same domain as the front.
8. **Schedule: PASS.** Static. Faults are sticky and never stall: a missing or mistagged packet, a format launch on a dual
   word, or a dual row meeting a normal or attention row at the mux. The wide path is +0 cycles to the BF16 law; the compiler
   issues one line per edge.
