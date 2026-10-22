# qkd_kvs_pc_sr13a (SQ-PCH2, 2026-10-21) -- PD-AUDIT compliant frame

PC sr13a (SQ-PCH2 MAIN): PD-AUDIT compliant frame (owner must-do 10-21): outline 267.84x300.24 -> 388.8x356.4 um, every face's pins stretched over the full face (N 1547 pins / 386.8 um = 4.0/um, E 1422 / 354.4 = 4.0/um); the 23 SRAM banks in 5 single-memory columns (front x43.2, return x103.68, tag queue x164.16, CDC down x224.64, CDC up x285.12; >=28.5 um std-cell channels) at 38.88 um pitch = 21.6 um gaps (10.8 um placeable rows beyond the 5.4 um halos for the wd_in hold buffers; was 22 abutted 0-um pairs). RTL = sr12g (face regs i_grp/i_grp_h +1 edge, kept so_ld_c / wq_rp / es_v_qb copies), sink CTS 8/20, SRAM-edge guard 2.4/1.2.

Why: PD-AUDIT (owner must-do, lanes/PD-AUDIT.md / STEWARD-QK 19:26): the 267.84x300.24 frame carried N 1547 pins / 262.6 um =
5.9/um and E 1422 / 292.2 = 4.9/um (limit ~4) and 22 abutted 0-um bank pairs (u_ecdc.down wd_in hold -17.5, FF -26/-60, DRC 3).
Die cost: frame 270.0x302.4 -> 390.96x358.56 per PC slot (x124 slots in kits_b) -- die owner (lanes/SQ-KDIE2.md) re-plans the slots.

## SAFE 8-point review
1 Pins FIXED: every face stretched to its full length (N/E <= ~4.0 pins/um, W/S lower); i_grp/i_grp_h kept face regs (+1 edge each, priced).
2 Reach PASS: largest crossing 388.8 um (< 405); chain i_next(N)->o_prev(S) hop 356 um < 405.
3 Fanout PASS: native census max 32 (sr12g census PASS on the same RTL; kept so_ld_c / wq_rp / es_v_qb copies).
4 Depth PASS: input->lookahead cones start at the face regs; TT placement reg->reg +136 on sr10e.
5 Storage FIXED: 23 SRAM banks on the lattice in 5 single-memory columns, 21.6 um gaps between banks (10.8 um placeable rows
  beyond the 5.4 um halos for wd_in hold buffers), >= 28.5 um std-cell channels between columns.
6 Floorplan FIXED: enlarged outline instead of squeezing (util ~18-20 %, pin-bound); 2.4/1.2 um SRAM-edge guard kept.
7 Clock: ck/hck local sink CTS 8 sinks / 20 um; spread <= 80 TT+FF measured by the gate.
8 Reset: landed 2-stage rst_n/hrst_n unchanged; face regs reset-free.

Benches (V5.050, RTL unchanged from sr12g): kvpc_tile_pc m0 PASS 20k (528046 checks), m4/m5/m7/m8 FAIL, DNR m0 PASS.
