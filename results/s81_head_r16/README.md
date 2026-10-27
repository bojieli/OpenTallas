# HEAD-CORE-R16 (2026-10-27): R14 rebuild hold stall root cause + per-mode FF hold binding fix

## Ruling 1: R14 elemA_rb_m2 / m12 (intel1) and elemB_rb (epyc2) GRT hold repair
Stopped 06:07 PDT (exact pids 2580773, 2581051 on intel1, 94241 on epyc2, plus containers hd-r14-hd_elemA_rb-2580773-grt,
-2581051-grt, hd-r14-hd_elemB_rb-94241-grt). State at the stop: m2 10,971 HB4, WNS -97.666; m12 10,956, -99.918;
elemB 12,803, -67.529 (all at input pin registers g_pin.x_q). Logs are in r14_stopped/. The run data is deleted.

### Generator FF binding check (the HBM-CORES-R6 bug): NOT present in HEAD (CHECKED)
Every HEAD kit carries `sdc_lint.json insertion_ff_ps 202.5` and `config.mk OT_VCLK_FF 202.5` (TT 250). That holds for
elemA_hold2, elemA_rb_m2/m12, elemA_eco, elemB_src and elemB_rb. IO contract: `set_input_delay -min -40 -clock vclk`
on every data input, and output min 0. The sign-off FF hold uses bound-ff 202.5 (elemA_eco signoff.json).

### Root cause (CHECKED from logs and probes)
1. **elemA m2/m12:** the R14 GRT ran a single-mode two-corner session (`CORNERS 'tc bc'`). The kit hook
   bind_ff_actual.tcl sets `set_clock_latency -source 202.5 [vclk]` GLOBALLY, so the TT scene timed input-pin-register
   hold against the FF virtual clock. TT hold is not a gate (signoff.py: hold_ff only).
   Probe on the R14 4_cts.odb (placement RC, x_q[137]; r14_stopped/*modeprobe*):
   | vclk binding | TT scene WNS | FF scene WNS |
   |---|---|---|
   | global 202.5 | -173.0 | -114.4 |
   | global 250 | -125.5 | -66.9 |
   So the repair padded every one of the 15,194 endpoints for a phantom TT requirement. The R10 hold2 GRT (BC-only
   session, correct FF binding) closed the same netlist with 15,658 + 321 HB4.
2. **elemB:** the kit IS multi-mode (OT_HOLD_MM=1, scenes tc/BC), but head_core_r14_rebuild.sh applied the
   orfs_hold_mm.py patch only inside the place container. The CTS and GRT containers are fresh images, so the
   multi-mode setting was inert: there are 0 OT_HOLD_MM lines in its 5_1_grt log, and it ran the same single-mode
   global-latency session. Latent: elemB's vclk_ff.sdc said 170 (stale), not 202.5.
3. Not the cause: the rebuilt trees' insertion. On placement RC, calibrated against hold2 (est 254.0/205.3 -> RCX
   228.5/184.8, ratio 0.90), elemA R14 is about 255 TT / 208 FF and elemB about 232 / 190. Both are inside 12.3
   250+-20 / 202.5+-20 (UNCHECKED estimate; RCX after route decides).

### Fix (tools/s81_head/head_core_r14_rebuild.sh, fail-closed)
- Every stage container runs the orfs_hold_mm patch: scene tc (mode ss, TT setup) and scene BC (mode ff, FF hold),
  each with its own SDC.
- `vclk_ff.sdc` is generated from config.mk OT_VCLK_FF. It must equal sdc_lint insertion_ff_ps, or the run FAILs.
- The hook's global FF latency line is dropped (mode ss keeps TT 250). The run FAILs if any global latency remains.
- A single-mode MCMM kit FAILs unless `OT_R16_MM_CONVERT=1` converts it (elemA: CORNERS tc BC, OT_HOLD_MM=1,
  OT_MM_SETUP_CORNER tc).
- elemB place accepts the 'already patched' status.

### Reruns (ot-run --mem 16, launched 06:26-06:28 PDT; GRT runs for hours: COLLECT, do not poll)
- intel1 /srv/opentallas-scratch2/claude/head-core-r16/elemA_m2 (unit oth-ubuntu-3884804-1793107589) and elemA_m12
  (oth-ubuntu-3884805-1793107589). The GRT log shows `OT_HOLD_MM: scenes WC (mode ss) / BC (mode ff) from 4_cts.sdc`.
- epyc2 /srv/opentallas-scratch2/claude/head-core-r16/elemB (oth-ubuntu-574953-1793107694).
- The script stops after GRT + read-only STA for render + GEOM. Then actual_head_route.sh, then
  head_post_route_eco.sh (the post-route HB4 step that signed elemA), then sign-off and LEC.
- OPEN: head_post_route_eco.sh still runs single-mode `tc bc` with a global 202.5. On elemA_eco the residual TT
  phantom was small (PRE_RCX hold -4.06 over 6 endpoints), but it needs the same per-mode fix before these rebuilds
  reach the ECO.

## Ruling 2: strap LEC
intel2 pid 3013060 was already gone at 06:0x. The monolithic run had FINISHED at 05:41 with `HEAD_STRAP_LEC EQUIVALENT
instances=264 ... 1682472 proven, 0 unproven` (hb4_lec/all/lec.txt, CHECKED). It agrees with the chunked 264/264.
