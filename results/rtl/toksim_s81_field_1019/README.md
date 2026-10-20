# TOKSIM-S81/FIELD: attn.wq_b slice phase measured on the TOK2 fullsix bench (10-19)

Bench: TOK2 fullsix L16/E24 (claude/tok2-capld-1019@e9ed82c83, exe sha256 63eccd91). It is one real slice (sid6) with six
real frames (col_h10_l4, col_h9_MX_l4, col_h9_l4 x2 each), 72 q pairs (ot_v41_rom_elem_q_qxpq_w10), real ROM images (1012),
and all 512 rank-local wq_b rows (3072..3583), K 1280, in 15 epochs (14 x 36 rows + 8 rows).
Only change: the bench epoch calendar `shift=1100+600*i` becomes `--epoch-period P` (retained_xs_program.py). Same exe.
run_period.sh is the fleet script; runs/ has the ot-run logs; sweep.json has every point.

RTL: 123 of 126 RTL files are byte-identical to release GEN mu4c 19bf4121e (rtl_blob_vs_release_19bf4121e.txt). Every field
element, frame, bf_col, xs, vp, vq, rstop and cap_rt/tr file matches. The three that differ: ot_s81sl_cap (the bench has the
EDLY24/WL3DLY16 successor plus cap_ed and cap_ld), ot_s81sl_slice and ot_s81sl_xr (both on the source/capture side).

Definition: start = first operand capture at an element (ACTUAL tag capture, t 1573); retire = last frame-root return word
(frame_return_words). The bench does not retire at CAP: CAP runs in the reset-F9 diagnostic, with 0 CW events.

| P (edges/epoch) | pass | start->retire (512 rows) |
|---|---|---|
| 600 (TOK2 default) | yes, reproduces TOK2 exactly | 8,623 |
| 250 | yes | 3,723 |
| 230 | yes | 3,443 |
| **224 (minimum)** | yes | **3,359** |
| 223 and below | FAIL: from epoch 1 the source issues no reads, srcerr 16, 476 rows missing | - |

Pass means: 512 rows, 0 missing, 0 unknown, source errors 0, and all 625 return words (row, row16, value) identical to the
P=600 baseline. The per-epoch latency is a constant 231 edges (first capture -> last frame word, 36 rows, 44 words).
Law: T(512 rows) = 231 + 224 x 14 + 1 = 3,359 edges (last epoch has 8 rows). Steady state: 224 / 36 = 6.2 edges per row
per slice.
Not measured: the CAP tree and CW after the frame root (+24 EDLY on R frames plus the CAP pipe, which the source contract
bounds at <= 64), the VP/QR hand-off, and the cross-slice/hub wire. Numeric PASS against gold is not asserted by this bench.
The word values equal the baseline, whose golden-tree match was shown only by the takeover3 model on the 757 run.
