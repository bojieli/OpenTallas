# qkd_d2d_cal_seq_pin_bc (KV-DCAL-BOOTCFG 10-19)

KV link-end calendar sequencer with the boot cfg merged in. RTL `rtl/qwen_sys/d2d_static_20261015/qkd_d2d_cal_seq_bootcfg.sv`,
top `qkd_d2d_cal_seq_pin_bc`, around `qkd_d2d_cal_seq` from `ot_qwen_d2d_cal_seq_dies_mu.sv` (MU image). The sequencer
`ot_qwen_d2d_cal_seq.sv` and the compute side are unchanged.

Bug it fixes: on the KV die (92490a06b), boot image target 11 was the only producer of the link end's calendar cfg port,
and the dcal cfg outputs were left without a load. Target 11 loads the tables and the INITIAL segment-1 bases (SEG2 =
admission: K TX 9 / RX 10). The sequencer also writes those base registers at runtime: SEG1 (TX 2 / RX 4) after each
admission, and SEG2 again at each epoch. Without those writes, every KV token run replayed the admission segment
(bench MUT 1).

Behaviour:
- bcfg_* (the dispatcher's link_cfg_*) are pin-registered. cfg_* is the boot write when one arrives. Otherwise it is the
  sequencer's own write, but only after its init stream. The inner init's 66 table writes are suppressed.
- Every output goes through one tile register. The inner anchor runs at EP_SKEW-2, so cal_start, cal_seg, layer,
  tok_start and the runtime base writes leave on exactly the qkd_d2d_cal_seq_pin edges (the bench checks this cycle by
  cycle). A few outputs are one edge later than the pin tile: the adm_done fall, the e=1,2 restore writes (>= 60 edges
  before admission), and the reset- and halt-relative outputs. None of these is bound on the die.
- Sticky faults are ORed into `fault`: COL (a boot and a sequencer write on the same edge), RUN (a boot write while
  the token programme or the admission run is active), STALE (a boot base word differs from the tile's SEG2 constants),
  and EARLY (a calendar start before both boot base words arrived).

Bench: `tools/qwen_static_kv/run_dcal_bootcfg.sh OUT MUT` (Verilator 5.050, tb `rtl/test/qwen_static_kv/tb_kv_dcal_bootcfg.sv`).
It runs the real dispatcher (LINKCFG=1, targets 1..9, 11, 0), this tile, and a real ot_qwen_d2d_cal TX/RX pair. The
reference is the MU pin tile on its own pair. The sequence is epoch 1 (admission plus the full 36-run token programme),
then epoch 2 (SEG2 restore, admission, token run, L1). Witnesses are in `results/rtl/qkd_d2d_cal_seq_pin_bc_1019/`.
- MUT 0: PASS. 66 boot writes, 2 admissions, 2 token runs, 36 layer runs, event streams identical, 6 runtime base writes.
- MUT 1 (sequencer writes dropped, today's die): FAIL, "token run would replay segment 9".
- MUT 2 (non-MU boot image, SEG2 8): FAIL, tables differ and the tile reports stale 1.
- MUT 3 (boot write on the epoch-2 restore edge): FAIL, col 1.
- MUT 4 (boot write during the token programme): FAIL, run 1 (the calendar also faults).
- MUT 5 (boot RX base masked): FAIL, early 1.

## SAFE-DESIGN CHECKLIST (owner 10-19)
1. Pins: PASS. RTL captures every input once (reload, epoch_go, halt, bcfg_*), and every output is a tile register
   (pin_regs is off, with the reason given). rst_n lands in 2 registered stages (reset_landing).
2. Reach: PASS. The tile is 18.8 x 34.6 um.
3. Fanout: PASS. ~250-flop leaf. The widest select is the 40-bit cfg merge. The gate's high-fanout lint checks it.
4. Depth: PASS. Per stage: a 2:1 merge mux, a 32-bit equality and a 6-bit decode. Sequencer logic is as in ep3/_mu, which
   closed at a 770 ps route.
5. Storage: PASS. Constants and boot words only, with no runtime-indexed flop arrays or delay lines.
6. Floorplan: PASS. No macros. 18.792 x 34.56 (aspect 1.84), grown from the 28.08 die slot for +94 flops: yosys gives
   251 flops vs 157. The target is 40-60% util. Full std-cell band. W/E pins at a 3-track pitch (2.3/um).
7. Clock: PASS. Single S clock entry. TT/FF spread is measured at the --cts gate. io_hold_margin 0.03.
8. Schedule: PASS. Static. Epoch-anchored outputs fall on the pin-tile edges, and the boot path adds no runtime cycle.

Die slot: `DCAL_WH` grows to 18.792 x 34.56 under `OT_KV_DCAL_BC=1` (kv_die.py). That change was sent to MU-DIE-KV2.
