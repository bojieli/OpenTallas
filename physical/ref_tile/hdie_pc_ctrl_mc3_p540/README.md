# hdie_pc_ctrl_mc3_p540 (main) / hdie_pc_ctrl_mc3_q648 (fallback): RELEASE HBM PC controller, MC3 structural fix

Lane HBM-MC3 (10-19), branch `claude/l2h-bw-safe-1019`. Owner 10-19: the successor HBM controller is the RELEASE HBM
controller. It keeps one open row per bank, 32 banks, and measures 91.6-92.9 B/edge/SM with the rotated compiler layout.
GEN2e4 binds whichever of these two kits closes first.

Top `ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face` with SRAM_P192=1, PURE_FACE=1, RESET_LANDING=2, RST_FOREST=1 and PCID_LOCAL=1.
The floorplans are the face_p540 and face_q648 floorplans (physical/hbm_bw_face_1019/README.md). Only the reset tree,
the pc_id copies and the pc_id pin face changed.

## Why (native census hold of hdie_pc_ctrl_bw_face_p540, bw_p540_v6)
- 202 drivers had more than 32 endpoints, about 190 of them reset:
  - region copies drove 50 to 237 reset pins each (bank_n_word_local, mf_valid, refresh_sel_local, ac_row);
  - the relay's synchroniser drove 94 D pins;
  - the face landing flop drove 96 asynchronous clears.
- 9 nets were longer than 405 um: pc_id_q to the K legality compare at 441-500 um, and the reset landing at 413 um.

## What changed (0 data cycles, 5 reset-release edges as before)
- **Reset forest.** `rtl/lib/ot_rst_forest.sv` replaces the 94-region ot_rst_relay: s0, then 8 l1 copies, then 192 l2
  copies, all KEPT same-clock D flops.
  - Release takes 3 edges after the face landing, exactly as the relay did (2+3 = 5 with RESET_LANDING=2).
  - The synthesis pass `physical/common_flow/ot_rst_copies.tcl` (spec `reset_relay_split`, max_loads 28) proves each
    copy family identical. It then re-points the 192 l2 D pins over the 8 l1 copies (24 each) and every reset load over
    the 192 leaves, sorted by hierarchical name. Each leaf therefore serves one bank, bank group or slice, and placement
    puts it there.
- **Asynchronous clears.** The synchronous resets on the reset family became asynchronous clears, so that each flop is
  one counted endpoint: ring_bw_safe and skid2_bw_safe (ARST=1), ready_seen, k_rdy_q and fault_detail.
  - Release behaviour is unchanged, because the reset is a flop output.
  - The default parameters keep the existing users unchanged.
- **Local pc_id copies.** pc_id_q (the pin capture) feeds KEPT per-use copies for the K legality compare and the refresh
  slot parity. The pc_id pins moved from the E face to the N face, beside k_addr. pc_id is a static die strap.

## Evidence
- face_txn_mc3: PASS on 6000 requests against released H9b, every tag, beat and data compared, edges_safe 166921 (the
  same as before the fix). The MUT_ID_TAG mutant FAILs, and its witness is committed
  (results/rtl/hbm_ds_layer_tput_1018/hbm_bw_safe_1019/mc3/).
- Bank latency (tb_hbm_bw_pc4 EXPOSE, OT_PC_SAFE_MC3): ds layout 91.62, 92.74 and 92.94 B/edge/SM; packed 103.89. The
  per-PC EXPOSE census is line-identical to MC2. The threshold is 90.
- Production full96 (bwsafe_face + FACE_MC3) and native census: see lanes/HBM-MC3.md.

## SAFE-DESIGN checklist
1. **Pins: PASS.** Every port is a flop D or Q in RTL, and the reset lands in 2 kept face stages (rst_l0/rst_l1).
2. **Reach: fixed.** pc_id has per-use kept copies and N-face pins, and the reset is a 3-level forest of regional
   copies. The native census reach check (0 nets over 405 um) is the check of record.
3. **Fanout: fixed.** The reset forest gives at most 28 loads per leaf, 24 per l1 copy and 8 on s0. The other drivers
   were already at most 32. The census (0 roots over 32) is the check of record.
4. **Depth: unchanged.** No logic was added; the gate reports the worst stage.
5. **Storage: PASS.** No change from face_p540.
6. **Floorplan: PASS.** Same outlines, macros and band as face_p540 and face_q648.
7. **Clock: measured at the gate CTS.** W-face M4 spine at the band centre; io_hold_margin 0.03.
8. **Schedule: PASS.** No data cycles were added and the reset fixed point is unchanged at 5 edges.
