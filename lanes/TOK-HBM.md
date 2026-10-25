# TOK-HBM lane (HBM d4g token-pass gate: HBM-DS + HBM-Qwen), started 2026-10-24 ~13:50 PDT
Branch claude/tok-hbm-1024 (worktree localhost ~/wt/tok-hbm, epyc2 ~/wt/tok-hbm). Host: epyc2 (64 thr share).

## Findings (step 1: locate tooling + latest results)
- Tooling: tools/hbm_layer_vehicle/tok_func_hbm.sh (+ run_pay_replays.sh, check_slice_run.py, coll_transport.py/coll_images.py),
  XDIE: rtl/hbm_accel/generic/collective/xdie/tok_func_xdie.sh.
- Latest vehicle = r18h5 land-direct SW-quadrant slice (src d34578d6f, TB 38766c45, boundary 93fbc670), binary built on ot-gold2
  (lost) = recovered from intel2 old disk /mnt/old-nvme0/claude/tokg-1023/r18h5_landdirect (478 MB Vtb_hbm_slice).
- Leaf-split (P7) twin build hbm-p7-tok-1023/r18h5_ld_split never finished (obj dir has fs errors) -> rebuild.
- Last results (TOKi 10-24 04:37-09:00, val_toki, component_probe scope): DS L0 t_ds_l0 FAIL 667/4745, _x1 FAIL 672/1785,
  _x2 FAIL 5/3831; L2 FAIL 1305/3234, _x1 38/4217, _x2 5/4062; L14_x3 FAIL 5/5847, L14_x4 PASS 3822/3822;
  L14/_x1/_x2 + all Qwen (t_qw_l0_r0/r5, chain r0/r5) NOT RUN (host died). Common faults: fr_SW__fault, hleaf_SE/SW__s_fault.
  rec2_kq PASS 287/287.
- No model checkpoints on the new fleet (HF cache gone) -> cannot re-emit fixtures; emitted replays are reused.

## Run dirs
- epyc2:/srv/opentallas-scratch/claude/{tokg-1023,tokd-hbm2,tokj-1023,hbm-p7-tok-1023} = copies of intel2 old-disk dirs at their
  original paths (hardcoded paths in scripts/binaries keep working).

## Current step
- copying old-disk vehicles to epyc2; xdie main_rows256 co-sim next; split rebuild next.

## 10-24 ~07:30 PDT (epyc2 clock) progress
- XDIE main_rows256 (main RTL, two-die step vehicle): 10/10 PASS = record (commit eb1ce0ea78 on claude/tok-hbm-1024).
  AR-step (r14_coll_ar): DS PASS on r14 + main RTL (launch->pub 537/542); Qwen running; LEAF_SPLIT=1 direct run running.
- Old TOKi DS failure classes mapped to records (priced_layers 1018 numbering): ALL COLL records PASS; ALL SU.VOP records
  FAIL (res_copy 640 checks = no write; moe_sum/scores_bias/w_scale zeros); ALL HC_MIX FAIL (hleaf_SW target hc_SW
  hcq_fault @~5233, s_ready 0x480 expected).
- SU root cause candidate (die.v lane trace, lane_trace.py): su_prog -> pgp_SW lanes UNEQUAL: {r_we,r_bank} 29 edges
  (LAND n54 K4) vs {r_start,r_row} / {r_len,r_data} 55 edges (LAND n79 K1 + 13 relays) -> config write pairs bank of
  drive t with row/data of drive t-26 (corrupt programme) and start lands 55 edges after drive (emitter assumes 9).
  Diagnostic replays running on epyc2 (diag/su31_*): checks shifted 0/64/256/1024/4096 and we/bank +26.
- Running: ld/{t_qw_l0_r0,r5,t_qw_chain_r0,r5,t_ds_l14,_x1,_x2} (4-13 h each), leaf-split slice build (build_split.sh).
- 07:20 epyc2 RAM pressure (KV-TOK verilator 337 GB + my 15 sims): killed my diag su31_d256/d1024/d4096; moved
  t_qw_chain_r0/r5 to intel2:/srv/opentallas-scratch/claude/tok-hbm/ld (binary + replays copied to same path).
- prog_transport.py (new, die.v-only lane pricer, K from landing ties): r18h5 land-direct
  SU su_prog->pgp: we/bank 29/16/29/20 (SW/SE/NW/NE) vs row/data/start 55 everywhere (skew 26/39/26/35);
  HC launch host->hc_SW/SE/NW/NE/eng 74/80/82/90/79 (skew 16); root<->quarter lanes 8-10 edges each way but hc_eng
  binds XRD=XRU=0 (only QDRLY 2, QCHX 11); hc_images assumes launch -> hleaf 2 flops -> target pin (~3 edges).
- Price P7 + leaf-split (hgi_sim.leaf_split_price_1023 on price_p7/stages_g675): DS AR 636,381 cyc = 1885.7 tok/s,
  MTP 3205.3; Qwen 1,272,951 cyc = 942.7 tok/s.
- HC root cause (strong): tools/hbm_die_v16/d4g_layers/l3_vm_hc_coll.py:13 says "XRD = XRU = 0: the relay layer that puts
  stations on the root <-> hub links must set them to its stage counts (RAW0 = 165 + XRD + XRU)"; r18h5 die.v relays
  those links 8-10 edges each way (unequal per quarter: d_v SW 9 / SE 8 / NW 10 / NE 9; qps_v 9/10/8/9) and still binds
  hc_eng #(QDRLY 2, QCHX 11) with XRD = XRU = 0  -> HC root mis-timed on every HC_MIX record. Fix owner: HBM die
  generator (relay layer: equal-depth root<->quarter groups + XRD/XRU bind) = HBM-ARCH.
- 08:30 diag results (DS L0 rec31 attn.res_copy, 640 checks): control FAIL 640 (reproduces TOKi); checks +64 FAIL 640;
  we/bank +26 (config pairing fixed) FAIL 640 with checks +0/+64 -> dest never written. pgp_SW runs serial 4301-4438
  (start drive 4240 + 55 lane + 6) and fr_SW fault fires during it -> writes refused (likely VM calendar grant window /
  vmstat: SU executes ~55 edges after its scheduled grant). Next diag running: all su_prog drives ADVANCED by 50/55/60
  (we/bank by A-26) so pgp executes on the scheduled edge (diag/su31_adv{50,55,60}).

## CODEX notes
- 2026-10-24 08:54 PDT CODEX results: ar_main cross-die AR-step report now DS PASS + Qwen PASS (both done rc0). Advance50/55/60 diagnostics still live at record 6/cycle911; long DS/Qwen runs still live. Qwen L0 rec17 mismatches show full-float observed versus expected BF16-truncated values, distinct from missing writes; inspect emitter precision contract next.

- 2026-10-24 10:20 PDT CODEX: Advance50/55/60 allfinished FAIL640/1046 (406commitOK). Root config pairing repair cannot fix downstream skew: pgpSW→SUcontrol19cycles, vmr/vmw/tree14/9/13/7 for slices0/1/2/3, i.e5/10/6/12cycle misalignment. Source l23 explicitly requires same relaydepth. Extended prog_transport inventory in own TOKbranch; evidence epyc2:/srv/opentallas-scratch/claude/tok-hbm/prog_transport_downstream.json. HC XRD/XRU and calendar offsets remain known independent blockers. No native token pass claimed.

- 2026-10-24 11:00 PDT CODEX: 6d46b1f539 pushed. Globalfixedprogrammebundle target61serial, rootconfig55;288-leg RTLmiterPASSmutantCAUGHT,1,210,724padFF and113serial/151stream rootadvance pricedperprogramme. Actualleafsplitcut97legs339070FF miterPASS; realVerilatorbuild epyc2scratch2/codex-hbm/prog_r8_leafslice, afterBUILD_PASS autoSU31diagnostic through run_diag.sh (guarded; shiftall6rootports-113/checkrec31+4leafsplit). Fulltoken/calendar/VMroundtrips/HCXRDremainopen.

## RESUMED 2026-10-24 12:14 (Claude, after 08:50-12:04 usage limit)
- Branch claude/tok-hbm-1024 fast-forwarded to codex/tok-hbm-1024 @157ac8a65b (linear on my e420d5afb2; pushed).
- Adopted (NOT relaunched): epyc2 scratch2 codex-hbm/prog_r8_leafslice (padded-programme leaf-split build -> guarded SU31
  diag by Codex watcher); intel1 scratch2 codex-hbm/hc_r8_unit/gate (native HC XRD=XRU=10 exact gate + wrong-DING2 mutant).
- My jobs still live: epyc2 ld/{t_qw_l0_r0,r5,t_ds_l14,_x1,_x2} (5 h+, ~40 GB each, 34k cyc), intel2 ld/t_qw_chain_r0/r5.
  Partial Qwen L0 r0: rec6 32 + rec10 16 got_zero, rec17 1024 + rec23 127 got = vm_pre row (dest unwritten / input
  passthrough; consistent with SU programme-skew class).
- diag su31_adv50/55/60 all FAIL 640/1046 (as Codex logged).
- Leaf-split (unpadded) r18h5_ld_split binary BUILD_RC=0 09:40; launched split/{rec2_kq,corrected_rec2,ls_ds_l14_x4} on it.
- 2026-10-24 14:25 leaf-split slice: rec2_kq PASS 287/287, ls_ds_l14_x4 PASS 3822/3822 (corrected_rec2 FAIL 72/287 kept). Price
  bracket tools/hgi_sim/transport_fix_price_1024.py: HC +20 -> no AR change; SU +104 exposed -> DS 1561.2 / QW 893.4 tok/s.
- 2026-10-24 14:25 HC gate (adopted): Codex run INFRA FAIL (neg prog.mem at ding 12); fixed generator --t0; my rerun
  intel1 scratch2/claude/tok-hbm/hc_r8_t0fix: PASS 24/24 mixes + 4/4 outs, HC_MIX_CYCLES 1029, DING2 mutant CAUGHT.
  Merged main 681cc61dab. prog_r8_leafslice build still compiling (Codex watcher will run SU31 diag).

## PARKED 2026-10-24 18:56
- Branch claude/tok-hbm-1024 @909ec66a01 (pushed). Last main merge 681cc61dab (= @a46de47f7b); 909ec66a01 (transport_gate WIP) NOT merged.
- Live jobs (mine): intel2:/srv/opentallas-scratch/claude/tok-hbm/ld/t_qw_chain_r0, t_qw_chain_r5 (pids 150727 150729 ; exit.txt on finish).
  All epyc2 runs finished; Codex jobs adopted and collected (prog_r8_leafslice build PASS + SU31 diag run; hc_r8 gate).
- Results: XDIE 10/10 + AR-step DS/Qwen PASS; leaf-split slice rec2_kq 287/287 + ls_ds_l14_x4 3822/3822 PASS;
  HC native unit gate XRD=XRU=10 PASS (24/24 mixes + 4/4 outs, HC_MIX 1029, DING2 mutant caught; my rerun
  intel1:/srv/opentallas-scratch2/claude/tok-hbm/hc_r8_t0fix after Codex run infra FAIL).
  Price (P7+leaf-split): DS 1885.7 tok/s (530.3 us), Qwen 942.7 (1060.8 us); SU advance exposed: 1561.2 / 893.4.
- Failures: layer benches FAIL: DS L14 640/1991, _x1 1305/3234, _x2 38/4217; Qwen L0 r0/r5 1424/1424; prog_r8
  padded-programme SU31 diag still FAIL 640/1046 (all 8 banks; fr_SW fault 5722).
- transport_gate (r18h5): HC XRD/XRU bound 0 (need 10, pads 1/2/0/1 + 1/0/2/1, RAW0 185), HC launch skew 16; SU cfg
  we/bank 26 short; SU cmd legs 9-19; SU bank read RT = READ_RETURN 22 OK (write-side trace gap for odd banks);
  SU calendar relation slot-lg-rq per bank -1/-3/6/6/-1/-1/3/3 -> the remaining SU suspect.
- Next: equalize SU calendar relation (pad lg_read/write per slice + rq per bank) on the prog_r8 die, rebuild, rerun
  SU31; then HC die bind (pads + XRD/XRU=10) and HC_MIX replays re-emitted with RAW0; hand transport_gate to HBM-ARCH
  as the B2l native-bind check.
- OWNER?: none new (B2l native bind accepted 18:47).

## RESUMED 2026-10-24 19:32 PDT (rtx-pro lane agent; wt rtx-pro:/home/ubuntu/wt/tok-hbm-1024r sparse, branch claude/tok-hbm-1024 @909ec66a01)
- 2026-10-24 19:32 PDT TOK-HBM: intel2 ld/t_qw_chain_r0/r5 (pids 150727/150729) still running at 12 h, cycle 33552/67531: both FAIL so far
  1600 checks / 9 records (rec 6,10,17,23,27,33,37,41,54; rec17 128 checks = got_zero/dest unwritten) = same SU class as L0. Left running (exit.txt on finish).
- 2026-10-24 19:32 PDT TOK-HBM: FINDING: every layer replay installs the SU calendar as cx_layer_1021.epoch_calendar = ONE row (rslot_v=wslot_v=lg_local_read=lg_local_write=0xff, owner 0) looped over the
  whole epoch (replay_su31: target 96 installs at stream 94/621/1104, loops 303/285/4834). With a constant word the per-bank SU_CAL relation (slot-lg-rq) cannot mis-time anything
  inside the epoch -> the 'SU_CAL' suspect is NOT the SU31 fault; calendar padding would change nothing. Also hb_vms_SW__vmstat never changes in the prog_r8 SU31 run (bank
  schedule faults not raised). fr_SW fault (stream 5722) must come from fl_SW chain (su lg_fault / su / sfu / hc fault), sfault_SW, sucore, subr, cij, dbk, ring.
- 2026-10-24 19:32 PDT TOK-HBM: launched instrumented rebuild (prog_r8_leafslice die.v + display-only monitor of 195 fault/valid nets: su lg_fault per slice, vmb pin valids per owner, rslot/wslot,
  rr/wq_done) + SU31 replay: ot-run on epyc2 /srv/opentallas-scratch2/claude/tok-hbm/r/su_mon (run_build.sh; launcher epyc1 pid 3416951, log epyc1:~/tokhbm-logs/su_mon.log). ~3 h.

## CODEX notes 2026-10-24 21:10 PDT (PARKED: Claude reset)
CODEX took over: SU transport diagnosis on codex/tok-hbm-r2-1024 @53e6ebba0. Own tree /srv/opentallas-scratch/claude/wt/codex-tok-hbm-r2. Analyzer now follows single-line ot_codex_prog_r8_pad corrective stages rather than reporting root codex_r8_* / latency 0. Targeted trace/depth mutant test + existing timing test: 2 PASS. No RTL change or added cycles. Actual full padded-die gate NOT RUN yet; next copy hier_wraps.sv from epyc2:/srv/opentallas-scratch/claude/hbm-p7-tok-1023/r18h5_ld_split/slice/ next to die.v then run transport_gate.
Collected: epyc2 su_mon/out/build.log updated21:07, hierarchy generation still running (no build.done); no duplicate launched. Existing su31_late replay also active on epyc2 PID1352843. Intel2 Qwen chain r0/r5 both live CPUs100%, PIDs150730/150728, logs buffered at cyc33552/rec54 with partial1600 failed checks in9 records; no exit yet. Known SU_CAL suspicion disproved by constant calendar; monitor is needed for actual fault source. No process killed, no new heavy jobs.
Shared FETCH_HEAD race encountered in worktree setup and corrected before edits: own branch reset to explicit origin/claude/tok-hbm-1024 @ae1addd27. Use explicit lane refs in parallel. No owner questions.
- 2026-10-24 21:15 PDT TOK-HBM (Claude, after Codex 21:10 handoff): adopted codex/tok-hbm-r2-1024 @53e6ebba0 (ff onto claude/tok-hbm-1024, pushed). transport_gate on the prog_r8_leafslice die
  (epyc2 scratch2/claude/tok-hbm/r/tg_prog_r8_leafslice.json): SU_CFG_SW PASS (all 6 cfg legs 55), SU_CMD_SW PASS (all 16 legs 61) = Codex padding confirmed;
  SU_BANK_SW 'FAIL' is a tool gap only (READ_RETURN/WRITE_RETURN params live in hier_wraps *_hw<k>, not on the die.v header; odd-bank wq trace null) -- r18h5 header had READ_RETURN 22 = need 22;
  HC_XRD/XRU/LAUNCH FAIL as known (bind 0, legs 9/9,10,8,9; launch skew 5). SU_CAL INFO. So the SU31 640/1046 fault is NOT a transport-gate class -> su_mon monitor run decides.
  Live: epyc2 su_mon build (hier verilation), epyc2 su31_late (prog_r8 binary, rec31 checks +1500 serial = 'late write?' probe), intel2 Qwen chain r0/r5.
- 2026-10-24 21:43 PDT TOK-HBM: su31_late (prog_r8 binary, rec31 checks +1500 serial, 8400 stream edges): still FAIL 640/1046, all got=0 -> res_copy destination NEVER written (not check timing); fr_SW fault 5722, pgp_SW busy 5585-5766 unchanged. Replay data deleted; summary epyc2 scratch2/claude/tok-hbm/r/su31_late/run_summary.log. su_mon monitor build still verilating.
