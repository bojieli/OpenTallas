# KV OVL boot/runtime calendar producer

Unique variant: ordinary KV bootcfg bc2 and its running route remain unchanged. Master qkd_d2d_cal_seq_pin_ovl_bc combines the known bootcfg merge (7167b4ab7) with two independent ot_qwen_d2d_ovl_seq playheads (95d11133f). Shared release artifact1a73e1e7a contains both dies' codec2 images and all four lists; ordinary admission bytes are pinned5ae543bfa. Constants: C_TXDP0x0a010308/K_TXDP0x03030416, actual registered seam2,2,2,3,2,2/11,11,9,9,9,9,9, admission SEG2=16, FIRST_OFS1176, H4026800, X8. Aggregate composed rate13708.2tok/s stays at the prior frame rate; no further gain is claimed.

The tile has exactly one cfg producer: registered boot writes have priority and load all66 image/base words, while the inner sequencer's constant initialization stream is suppressed. After initialization the runtime SEG2 restore and SEG1 token-base switch reach the link end. Boot/seq collision, boot while running, stale SEG2, or starts before both boot bases latch sticky faults without stretching the schedule. Start RX/segment RX/user TX/user RX are independent outputs, never aliases of TX.

Each of two lists uses one hard4096x72 mask ROM (low32bits used) and one32bit plain capture register. Physical storage589824bits, logical1703x32x2bits; no runtime-indexed flop memory. Player address registers directly drive synchronous ROM addresses; ROM readE1, captureE2, player nextE3, consume no earlier thanE4. Input control capture1+innerEP1+output capture1=KV boundaryEP3, preserving FIRST_OFS1176. Model is results/rtl/kv_dcal_ovl_codex_1019/model.json.

Verilator5.050 fleet exact bench PASS: full F16 period+wrap (1708TX/1710RX starts through the extra partial frame),66 boot words exact, independent rawEP3 sequencer cycle-equal TX/RX starts/segment/user, runtime SEG1 bases selected. Six mutants all FAIL with committed witnesses: dropped runtime cfg, stale admission base, reanchor while lists run, boot during admission, missingRX boot base, and the old mid-list halt/restart pointer. The shared link end's payload/ownership proof belongs to the overlap link vehicle; this bench qualifies the new sequencer boundary/boot integration.

## Safe design before gate

- 1_pins: PASS: all functional control/boot inputs registered; all outputs registered, rst_n two-stage landing plus core release.
- 2_reach: PASS:216x129.6um tile, all direct wires below405um.
- 3_fanout: CHECK SYNTH: no wide datapath; cfg_select40loads matches bootcfg reviewed exception; reset landing tree only leaf~500flops.
- 4_depth: PASS architectural:32bit counter/decode, registered32bit ROM capture, no macro-output mux/logic before capture; gate measures depth.
- 5_storage: PASS: two hard4096x72 ROMs(589824physicalbits; lists~1703x32each); only current and next32bit words live in flops.
- 6_floorplan: REVIEW macro-lattice-bound density exception: each ROM38.016x62.910 at(43.2,43.2)/(129.6,43.2), lattice43.2,5.4um halos,48.384um macro channel and>=20um pin-face core-edge margin. Full bottom stdcell band. Initial129.6square rejected by generator before any synthesis/gate:5.184um channel and3um right-face margin. Safe216x129.6shape aspect1.667; do not squeeze.
- 7_clock: PASS architecture: local root beside bottom logic band, hardROM clock references; io_hold_margin.03; gate must measure TT/FFspread<=80.
- 8_schedule: PASS design intent: EP_SKEW3 at tile boundary, innerEP1 cancels control/output captures; ROM address->ROMq->capture->player prefetch3edges fits4edgeMIN_DT; exact bench+wrap owed.

No datapath masks, multicycles, false paths, or credit/backpressure are added. Gate timing/spread/congestion evidence is still required.216x129.6um is sized by hardROM lattice and pin-face margins: initial129.6square was rejected by geometry validation before any synthesis/gate. Root critical review must approve the macro-lattice-bound low-util rationale; no REVIEW.json or submission is authorized in this lane.

## Die obligations

Bind this distinct master and its two exactROM instances on the shared codec2 OVL variant; provide boot target11 from the same image compile (OVL admission at16). Drive new six OVL ports, including separate starts/users; adopt216x129.6um OVL_DCAL slot. Preserve ordinary bootcfg runtime switch and keep nonOVL branch independent. Epoch/reset/halt exceptional release is before the static frame; no extra runtime cycle is charged. Parent d2d_overlap and KV coordinator own full-die binding and strict seam recheck.

Mandatory recovery successor imports shared510c0cd51: halt or idle reload rewinds both list players to word0 and clears prefetch/current/count (stickyfault reset-only). Positive abort/new-epoch restart checks the first TX/RX event's epoch-relative edge/segment/user against the first epoch, then compares exact starts to the rawEP3 reference. Old unchanged source fails this test; MUT_HALT_REWIND1 reproduces that failure in shipping source. Driver caches by SHA256 source/image/ROM identity.

Diagnostic gate2 (pre-rewind) PASS: standard-cell+macro area5299um2, total20% coreutil, GRT0, setup+223.3ps/hold+51.1ps atTT placementRC; pin-flop spread16.4/15.0ps. The old auto pin plan clustered pins; successor exact io_pins.tcl spreads all97 functional pins over full W/E/S faces with ascending bus bits and S-centre clock. Gate2 is preserved under results/rtl/kv_dcal_ovl_codex_1019/gate2_pre_rewind_* and does not qualify this successor. New gate required before critical review/submission.

Structural clock successor: full-face gate3 failed TTpin-flop spread84.0ps (FF75.1), despite GRT0, textbookPASS456flops/depth308.4ps and setup+206.1/hold+54.1ps. Failure and PNGs are preserved under gate3_fullface_spread_*. The tile now uses the established balanced clock_spine architecture,<=8sink regional leaves and individual hardROM clock leaves. It is still one1:1clock with S-centre entry(108.009,0), no data masks/budget changes, no extra runtime edge. Parent d2d_overlap approved this structural recovery. New gate must pass bothspread<=80 before root review.
