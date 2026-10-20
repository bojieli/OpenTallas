# qfd_sys_face (MU 1, MU_HEAD 1) -- ROOT4-SYSFACE re-close 10-19

Compute-die system face for the Qwen ROM 4-user release die. This re-close hardens main's current
`d2d_cal_image_mu.svh`. The closed rs3 view carries a stale image: the yosys equivalence in
results/arch/root4_qwpost_equiv_1019 FAILS with 26/13570 cells unproven, all in the d2d calendar config path.
The parameters are the die's own: MU 1 and MU_HEAD 1, from tools/qwen_split/die_params.py (MU-DQ-BOOTCTX).
The RTL structure, outline, ROM placement, pins and faces are those of rs3/mu1.

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: PASS. Pin registers are on (OT_PIN_REGS / OT_KEEP_PIN_REGS), and rst_n lands in 2 registered stages (reset_landing.json).
2. Reach: PASS. The outline is 259.2 x 129.6 um, so no single-cycle wire can exceed 405 um.
3. Fanout: PASS (rs1 regional reset: 14 relay flops of <= 256 loads each; data cones as rs3). The native census comes from the gate.
4. Depth: PASS. The previous mu1 gate measured TT reg->reg +80.4 ps at 833 ps. There is no combinational in->out path (flop-first pins, recipe 4).
5. Storage: PASS. The config image sits in the ot_rom_4096x72_m8 macro. WAIVED-with-reason: the three d2d calendars
   (ot_qwen_d2d_cal NE 64/32/16 x 32 b = 2.0/1.0/0.5 kb) stay as flop arrays. Each one is at or below the ~2 kb line, and they
   are written only at config time. The SRAM_CAL successor belongs to the SAFE3/bc3 lineage (claude/qw-sysface3-1019), which is not on main.
6. Floorplan: PASS. The ROM sits at (172.8, 43.2) R0 on the 43.2 lattice, with one contiguous std-cell band. Pins are on full faces
   (N ~5.5/um <= 6) and the aspect ratio is 2.0. WAIVED-with-reason: utilisation is ~19% because the tile is pin-limited
   (N face 1,322 b at ~5.5 b/um, the same as rs3).
7. Clock: PASS. ck sits at the N-face centre beside the register mass. The mu1 gate measured pin-flop spread 46.0 TT / 46.2 FF (<= 80).
   FIXED: route.io_hold_margin_ns 0.0 -> 0.03.
8. Schedule: PASS. The design is static, the image is constants only, and no cycle is added.

## Benches (fleet ot-epyc9, main c165d6ab2 + this branch; logs in results/rtl/mu_qwen_1018/sysface/witness_root4_1019)
- tb_qfd_sys_face MU 1 MU_HEAD 1 (MU image): MUT 0 PASS (1512 events exact + 4 head contexts). MUT 1, 2 and 7 FAIL as expected.
- MUT 6 is an equivalent mutant at MU_HEAD 1: the HOST context RX filter is redundant with the face's user-0 filter.
  It now runs at MU_HEAD 0.
- mu_kvctx_cal_e2e FAILS on main: C10 filler native contexts 0 vs 108. That check came in with MU-DQ-BOOTCTX
  (it needs ctlm FCTX). This is bench state, not a face RTL change. The cmut 1 mutant errors, because it is missing the solo log.
  Owner: LEAD3-QW (Q.MU.FACE).
