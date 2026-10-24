# TOK-QW (lane file)
Branch claude/tok-qw-1024 (worktree localhost:~/wt/tok-qw, base main 8a5d1f3dab). Hosts: intel1 (64 thr share) + ot-run.
Scope: Qwen ROM token-pass gate: compute-die layer runs (stg/head/attnret), compute<->KV D2D co-sim (TOK.QW.XDIE), composed 1u/4u.
Not mine: xt1/tp8/xdie-link/ovl4u (QC-TOK), KV-die token tests (KV-TOK).

## Current step
06:58 PDT recovered old-fleet inputs before the 07:03 wipe -> intel1:~/ot-scratch/tok-qw/recovered (66 GB):
  fx_in (TP4 P8191 36-layer ISA gold + img_p1 + oracle.json, 32 GB), tokd-qw-main-1023 (head fx, link fx, xt1 in),
  tokqwm-1023 (10-23 record run), tokqw4-1022/stg3/fx, tokfunc-qw-1021 (non-build), codex qw-head-main-a970-1023,
  qw-r56-head-selected-1023, codex-kvchain-2140. NOT found: kv_pkt r17 explicit packet (lived on ep5/ep9).

## State found (task 1)
- stg4 is DONE (10-21 19:55, PASS 527/527, ISA 1,032,336/1,032,336, cal gate + VM ages qualified). The stg3 "normalized FAIL"
  = original pos MAT calibration without XC framer pre-arms + no VM-write probe (ages UNKNOWN); fixed by bench-only patches
  stg_cal_prearm.patch + stg_vm_probe.patch (stage_stg.sh). Release config is SU_LT=0 (stg5lt0).
- Latest record TOKe-QWM 10-23 (main 92c2417f6, results/rtl/tokqwm_1023): 8/9 PASS, head FAIL (lpf SEGCAL lockstep
  3317/27981, h16y leaf absent on main); compose 1u 269,452 cyc = 4,455.3 tok/s, 4u 11,811.3, price HELD (head FAIL, tp8 diag,
  gaps IMAGE CAPACITY / TILE DELIVERY / RoPE ROW producer->consumer).
## Runs (RUNROOT intel1:~/ot-scratch/tok-qw/r1024, assembly = git archive main 8a5d1f3dab; logs localhost:~/wt/tok-qw-logs)
- stg   : ot-run intel1 --mem 240, stage_stg.sh --su-lt 0 --fx recovered tokqw4 stg3/fx (36 layers) -- RUNNING since 07:01
- head  : stage_head.sh --leaf (die-selected leaf h16za native32_1r) -- DONE 07:05 PASS
- xhead : stage_xhead.sh (new) calibrate + per-consumer sweep + 4 cases + 10 mutants -- RUNNING
- s8exp : tb_qfd_dv2 FACE 3 = BOUND die slice row (s8 flat / ce_w5 / ce_l9h / ce_e5 per position) lint/build -- RUNNING
- xdie_bound: sub-lane (fork), see its section
## Results
- head PASS (RTL-functional, die-selected leaf, main 8a5d1f3da): img0 123/123, imgh 131/131, bmut3 FAIL as required;
  LM-head stage start->END 3,135 = compiled 3,135 (plan price 3,101, +34). 10-23 FAIL cause: the behavioural h16y family is
  not on main + generic LP lockstep (abandoned LP, not the die parent). stage_head.sh --leaf added.
- FINDING: bound_r8 substitutes qfd_dv_slice2 by qfd_dv_s8_flat (+ chain-end variants) = SU_LT 1 / HD_W130 1 / MU_NU 4 /
  ARF1 RP1 + HARD leaf registers + treq lane. The stg stage (tb_qfd_dv2, qfd_dv_slice2 SU_LT 0) is the predecessor slice,
  not the bound slice -> building a FACE 3 tb on the bound s8 row.
- kv/chain: KV r17 vehicle readset 53/53 non-bench files byte-identical 92c2417f6 -> main (record.sv identical too); the
  10-23 r17 child archives (explicit packet) were lost with ep5/ep9 -> carried, not re-run.
## OWNER?
