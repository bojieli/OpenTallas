# qfd_sys_face_n32oa -- Q.MU.FACE.2 die-bound sys_face (MU 1 / MU_HEAD 1) on the native5 bounded source + obs_fault (QW-ORPHANS 10-20)

CRITICAL prefix (qfd_sys_face): gate PNG + checklist go to lanes/COORD-REVIEW-QUEUE.md; no REVIEW.json, no submit.

Source: rtl/qwen_split/qfd_sys_face_n32_bounded.sv_p192.sv (= the n32o source with module name + ROM master renamed only) = Codex b7be1b295/448cd5a2f
bounded5 (captured actual pin wrapper of the closed mu1 gate, 35 same-edge producer copies, 512-leaf reset forest) patched by
tools/qwen_split/sysface32/add_obs_fault.py: new input obs_fault (die fault-OR root, Q.BIND.1 qfd_fault_or) -> pin FF u_obs_pin ->
OR2 u_obs_or with the face_fault cone -> the existing registered fault output FF. fault(t+1) = face_fault(t) | obs_q(t); 2 edges
obs_fault -> fault; observation only (no admit/t_go/result/schedule edge). Also the generator's never-indexed [0:0] 1-bit ports are
declared scalar (same names as the closed view; no functional change). ROM: ot_rom_4096x72_m8_escape_p192 (Codex 0415f7a77 owned escape apron: 47.736 x 62.910, 4.860 um side apron, W/E contacts 192 nm = 5.2/um; Lib PROPOSAL-ONLY metal lower bound +1.49 ps, VIA34 RC uncalibrated).

## Pre-gate evidence (fleet, Verilator 5.050 / ORFS asap7lock)
- Native census (real ASAP7 synth, all drivers incl reset, official tools/ref_tile/native_census.py): 38330 roots, max 32 loads, 0 > 32 PASS
  (ot-epyc5 /srv/opentallas-scratch2/claude/qw-sysface4-1020/native6b; native5 was 38327: +3 = obs raw/q/d).
- Protocol (paired actual old wrapper vs new wrapper, every output bit from the first epoch edge, no mask): MUT 0 PASS
  (1512 events exact, boot 68->69, cal_ready 75->76, epoch 79); MUT 40 obs_fault causal negative: pulse at ep+50 caught as
  SYSFACE32_WRAPPER_MISMATCH port=fault cyc=131 (2 edges) (ot-agidock128 /srv/opentallas-scratch/claude/qw-sysface4-1020/p6b_m{0,40}).
- Constants: cfg_data[6,7,8,9,16,30,31] TIELO outputs are source-literal: every cfg_data source word (reset 0, C/K TX/RX IMG x32,
  SEG1, SEG2 of d2d_cal_image_mu.svh) has exactly these bits 0 (results/arch/qw_sysface_native32_1020/cfg_data_constant_proof.json).
  seq_dc[54] has no endpoint because qfd_sys_face.sv never reads it (uses [31:0],[49:32],50,51,52,53,55): reserved input, no tie.
- Storage: ROM 4096x72 macro holds the config image; calendars NE64/32/16 x 32 b = 2.0/1.0/0.5 kb flop tables (native FF
  qfd_syscal64/32/16_n32 = 2493/1307/713 incl copies/control), written only at config time.

## SAFE-DESIGN checklist
1 Pins: PASS (RTL wrapper; flow pin regs / reset landing OFF to avoid double wrapping; rst_n u_3691 -> u_3690, 2 stages).
2 Reach: PASS by outline 259.2 x 129.6 (corner-to-corner 388.8 um < 405).
3 Fanout: PASS native6b 38330 roots max 32.
4 Depth: measured by this gate (closed mu1 on the original source: TT setup +64 ps at 833 ps); obs path adds one OR2 before the output FF.
5 Storage: WAIVED-with-reason (as closed mu1): each calendar <= 2 kb and config-time written; image in ROM macro.
6 Floorplan: ROM at (172.8, 43.2) R0 on the 43.2 lattice, one std-cell band, faces as mu1 (N D2D, W tt_ctlm/native, S embed/io + obs_fault at 255.31-255.85, E seq_*);
  ROM contacts: 192 nm PASS; fill ~31% synth (pin-bound, N face ~5.5/um).
7 Clock: ck at the N-face centre beside the register mass; pin-flop spread <= 80 TT+FF measured here; io_hold_margin 0.03.
8 Schedule: static; +1 boot/cal_ready edge (bounded copies, priced); obs_fault observation only.
