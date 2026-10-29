# TOK-HBM-1 (HBM whole-die token pass: unified 4-role top + 4-role calendar/START authority)

## 2026-10-28 20:37 PDT RESULT / PARKED (slice 1, fresh lane, no predecessor; branch claude/tok-hbm-1-1028@c8255e05b5 on main 410e940f4f)
- DONE (compiler side, CHECKED own tests): tools/hbm_next/four_role_calendar.py = the current 4-role FUSED calendar + START
  authority that fused_job217_emit.py fails closed without (5 boot offsets SW/SE/NW/NE/root, root straps wsc/pk5/pb5, provider
  preload/commit/START, per-record launch/root_capture/root_done/deadline, F30 launch edge). ONE RULE, every constant = bound
  plan legs + RTL contract constants: boot_r = 66 (reset_contract 2+HOLD) + reset_r + 3 (delivered_reset pipe);
  rt_r = down_r + up_r; wsc = max(rt) + RR(10) + 8 (tree form of eng WSC = 2*RL+RR+8); pk5 = |rt_NW - rt_NE|, pb5 = NE earlier;
  START = max(commit+1, max(boot)+6+32 warm); launch >= prev deadline+4; capture = launch+1+ingress; deadline = done+2+status.
  Any leg/service entry without cycles+source -> MISSING, no file (never a default). New opt-in tool only, no shared file touched.
  Tests 8/8 PASS (intel2, die-hbm-10 venv pytest): calendar -> REAL fused_job217_emit.py -> COMPILED_OPT_IN programme.mem (3 jobs,
  fake ISA decoder only); mutants no_leg / no_service / bad_sha (tool) and early_start / ingress off-by-one / swapped roles
  (rejected by the real emitter) all fail closed; per-node pad rule test.
- C24 plan (DIE-HBM-10 c24, sha 3ab76af4, not plan of record): the hub FUSED tree (16 lanes + n1..n4 per hub) IS in the plan as
  internal mu_tree stations: aligned round trip NW 45 / NE 46 station regs, every node pad k <= 6 (strap limit 32), n4 pads
  NW (1, a) / NE (1, b) [CHECKED computation, results/tok_hbm_1_1028/calendar_c24.hub_tree.json; 1 edge per station reg and equal
  node RTL latency = UNCHECKED assumptions]. All 12 bound legs are MISSING from the plan [CHECKED]: reset release is 'wavefront'
  with 0 reset ports/lanes (no per-role delivered-reset edges); NO fused root (ot_hnx_fused_hub_n4ext), provider
  (ot_hnx_fused_host_program) or n4->root lane in any partition_type (root partition has no fused content).
- UNIFIED TOP gap census (read-only, DIE-HBM-10 bindfull/hbm_current_native_top.sv 20:13, results/tok_hbm_1_1028/top_gap_census.json,
  CHECKED): 383 boundary ports; 25 real die IO (5,462 b); 358 OPEN (50,265 b): (a) 52 rst_n (calendar x4, vmb x32, vmm x8, idx x4,
  fused root/programme/n4) = the reset authority; (b) S-role client families of the 8SM->4-role fold (su_S* 16, smw_S* 16, vmdel_S* 16,
  svg_S* 8, hcollks_S* 8, hcollrs/hb_dbk/xl_S*_ctl, hleaf_S* 18 in; vmb_S* 128 + calendar_S* outputs open); (c) idx s_* streams 28;
  (d) fused n4 ua/ub/pad: SOURCE vs PLAN MISMATCH - the composed top has root + programme + n4_nw/n4_ne but 0 hnx_fused_lane and
  no n1..n3 (lower tree absent, n4 inputs open), while the C24 plan has lanes + n1..n4 per hub but no root/programme.
- NOT DONE this slice: the unified top RTL itself (needs the plan delta + fold below); item 2 (full programme compile, whole-die
  vehicle, nominal + must-FAIL mutant, VMX delta) - blocked on DIE-HBM-10 strict-clean bind + the plan legs above.
- NEXT (successor TOK-HBM-2, start from this line): (1) when DIE-HBM-10 posts the plan event with fused root/provider placement +
  per-role reset delivery + n4->root lanes, fill a bound file (legs from the plan, node RTL latency added) and run
  four_role_calendar.py --plan; (2) root service table from the existing native root wrapper bench (Codex 4/4/2 721/0 packet) per
  (op, n); (3) unified top = current_native_top + lower tree (plan's hub tree) + reset authority wired from boot offsets + straps from
  the calendar; fold RTL only after the free-slot count (DIE-HBM-6b default); (4) then item 2 on epyc2 via ot-run.
