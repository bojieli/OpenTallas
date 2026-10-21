# qkd_kvs_ctl_c32d — KV-CTL12 10-21 structural successor of c32b (K.STA.CTL)

Predecessor gates (ep9 ref_gate/qkd_kvs_ctl_c32{a,b}-20261020-222038, source a0f130d37/2913c75fa): native32 PASS, then
trial GRT FAIL (GRT-0183 boxed net inside repair_timing of 2224 setup endpoints, overflow 0). Classified TT paths:
boot_image_epoch -> controller/landing strobe (o_hroot) in->reg 1037 ps logic (-687 b / -817 a), i_hroot_EN -> u_bobs f1
in->reg -262, lprg flop -> lp / kg output -281 / -397, boot o_lw -> o_hroot reg->reg 867 ps (c32a placement).

Structural fixes (no squeeze, no retry):
1 Pins: pin registers ON for every data input and every output except o_hroot_* (RTL member output flops already).
  +1 edge per input / output port -> die schedule (KV-CAL) must absorb; reset rst_n / por_n land in 2 stages.
2 Reach: unchanged (345.6 x 561.6, centre-to-face <= 405 um ).
3 Fanout: members unchanged from the native32-PASS source + one 8-bit select leaf (u_pg) and one /6 leaf (div6r) on the raw
  boot address; native census runs in the gate first.
4 Depth: the boot /6 and %6 come from the RAW address in parallel with the seal accept (qkd_kv_ctl_c32_div6r + word-326
  constants 54 r 2 behind ot_s32_sel u_pg): ~350 ps out of the boot accept -> strobe stage; face flops give in/out paths a
  full cycle. 0 added internal edges, same function (tile_a/tile_b/kb benches compare every output every edge).
5 Storage: unchanged (CTLSRAM 2, 64x128 macros).
6 Floorplan: macros on the 43.2 lattice (shifted +43.2 um in Y); W/E 2652 pins over ~449 um usable = 5.9/um (was 7.0/um).
7 Clock: spine as c32b (TT/FF pin-flop spread 49/50 ps measured there); io_hold_margin 0.03.
8 Schedule: static; +1 in / +1 out pin edges handed to the die calendar (LEAD-KV / KV-CAL).

## CODEX terminal gate / coordinator review

10-21 c32d WARN0fail, native census max32 PASS; trial GRT0, M2max21.25%. TT diagnostic setup-136.6ps/hold+34.6ps; clock TT42.1/FF38.0ps pin-flop spread. Six macros on43.2um lattice, broad channels/continuous rows, full-face legal pins; fill11% is pin-bound. Inputs+outputs retain +1/+1 edges already handed KV-CAL; taller slot+86.4um to die. Coordinator personally reviewed exact PNGs and APPROVED64645a5c...; no clock/behavior waiver. Current committed7PASS/3mutant fail witnesses kv_ctl12_1021 now named in job; prior source witnesses preserved. Route timing decides.
