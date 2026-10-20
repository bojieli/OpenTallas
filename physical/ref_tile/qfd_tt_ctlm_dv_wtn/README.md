# qfd_tt_ctlm_dv_wtn (QW-F16PROG4 10-19): CTLM-core F16 typed witness face (hard child of qfd_tt_ctlm_dv_gi, F16WTN=1)

RTL rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv -> SAFE_PHYS qfd_dv_typed_witness_control (QW-F16PROG3 d766dfa16 + cy latch fix).
Fallback kit (PARALLEL): qfd_tt_ctlm_dv_wtn_b (120.96 x 60.48, 2:1). Bench: results/arch/qwen_calendar_integration_1019/f16_wtn
(face == controller every edge on 28 stimuli, BEGIN withdraw, FMUT 1-3 FAIL; Verilator 5.050).

SAFE-DESIGN CHECKLIST
1 Pins: PASS -- every input pin-registered (f_*), every output registered (+2 edges total), reset 2 stages + 3 kept leaves; kit pin_regs off (reason in spec).
2 Reach: PASS -- 86.4 x 77.76 um tile, every wire < 405 um.
3 Fanout: PASS regs (native census 4666 FF, max FF load 32); 5 comb nets 36-45 WAIVED as buffered comb (QW-F16PROG3).
4 Depth: OPEN -> this gate (TT setup / FF hold pre-route STA).
5 Storage: PASS -- 1742-bit template < 2 kb in kept write-enable sectors; no runtime-indexed flop array > 2 kb.
6 Floorplan: no macros; outline from census area 2682 um2 (+reserve) ~48% util; aspect 1.1:1 (fallback 2:1); full std-cell band.
7 Clock: single local root (small tile); spread measured by --cts gate; io_hold_margin 0.03.
8 Schedule: static; +2 status edges, +1 input edge, 0 SU/token cycles -- tools/qwen_static_schedule/f16_calr_edges.py.

## Benches (QW-F16SUB 10-19)
- f16_wtn_face (pass, `F16_WTN_FACE_PASS`): rtl/test/qwen_dv/run_f16_wtn_face.sh generates the 28 WTN1 stimuli from the
  committed PW image (typed_witness_control_vectors.py) and checks the face == standalone SAFE_PHYS controller on every edge
  of every stimulus (nominal CLEAN, 27 FAULT) + BEGIN withdrawal.  Verilator 5.050 (daemon PATH).
- mutants f16_wtn_fmut1 (no BEGIN withdraw, `F16_FACE_BEGIN_NOT_WITHDRAWN`), fmut2 (installed epoch as identity) and fmut3
  (retire user swap) (`F16_FACE_EDGE_MISMATCH`); committed witnesses bench_witness/ (fleet unit oth-ubuntu-588286, ot-epyc5).
