# qkd_d2d_cal_seq_pin_mu (KV-DCAL-MU 10-19)

KV-side MU D2D calendar sequencer: `qkd_d2d_cal_seq_pin` built from `ot_qwen_d2d_cal_seq_dies_mu.sv` +
`d2d_cal_image_mu.svh`. Copy of the closed `_ep3` kit (same ports, pins, outline 18.792 x 28.08 = die slot DCAL_WH).

Image: `D2D_MU=1 tools/qwen_split/d2d_cal_image_production.sh` (mu-die-qw2 05a8c8fe3 tools) on the MU release pair seam
`2,2,2,3,2,2/11,11,9,9,9,9,9`. The same run with D2D_MU unset reproduces `d2d_cal_image.svh` byte for byte. The TXDP lines
match production: TXDP_C 0x0a010308, TXDP_K 0x03030415 [21,4,3,3]. The old _mu image had K 0x03030417 [23] and C [8,3,1,9].
MU delta: one extra C RX and one extra K TX image word (the MU context slot), and C RX / K TX SEG2 go from 8 to 9.

Benches (`rtl/test/qwen_split/run_cal_pin.sh OUT MUT 1`, iverilog, witnesses in results/rtl/qkd_d2d_cal_seq_pin_mu_1019/):
- MUT 0: PASS (74 starts, 72 layers, boot/reload/reset 66 words, halt/reload capture, TXDP match)
- MUT 1 (EP_SKEW anchor -1): fails with CALPIN_FAIL compiled start
- MUT 2 (production dies file under the MU tb): fails with CALPIN_FAIL boot control word
- MUT 3 (stale TXDP_K 23 image): fails with CALPIN_FAIL txdp

## SAFE-DESIGN CHECKLIST (owner 10-19)
1. Pins: PASS. RTL captures each input once. Outputs are the sequencer output FFs (pin_regs off, reason kept from ep3).
   rst_n lands in 2 registered stages (reset_landing, new versus ep3) ahead of the RTL release_q.
2. Reach: PASS. The tile is 18.8 x 28.1 um.
3. Fanout: PASS. Small leaf (~200 flops). Gate checks the high-fanout lint.
4. Depth: PASS. Same logic as ep3, which closed at 770 ps route and 833 ps signoff. The images are constants.
5. Storage: PASS. Constant images, with no runtime-indexed flop arrays or delay lines.
6. Floorplan: PASS. No macros, aspect 1.49, ~45% std util by synthesis area, full std-cell band.
7. Clock: PASS. Single centred S clock. Pin-flop spread is measured at the --cts gate. io_hold_margin is 0.03.
8. Schedule: PASS. Static calendar. The compiler places the MU slot in the image. The reset landing adds 2 edges as a
   boot constant before epoch_go. The calendar timeline is anchored on epoch_go and does not change.
