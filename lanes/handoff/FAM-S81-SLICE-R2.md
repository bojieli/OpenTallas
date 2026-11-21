# FAM-S81-SLICE-R2 handoff (Opus 5.5, 11-21 ~05:40 PST) -- STOOD DOWN (context); successor FAM-S81-SLICE-R3 needed
W=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice (R1 root, clone).  L=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r2 (R2 root).
My local waiters die with this session: RE-ARM on every unit below.

## 1. WREG (OT_S81SL_XS4_WREG) -- NOT PUSHED
- R1 form 4f03fa6cea FAILED xs4_equiv wreg: 1 mismatching word per case at the first read-out (write->read hazard).
- Fix 13fbc4181e (clone $W/clone, branch claude/fam-s81-slice-wreg-1121): define = exact retiming of xs4 with every input +1
  edge (+1 latency on xw_v/xw_d/fault, pre-approved): plain input reg on rst_n + issuer word; gather capture valids keep
  undelayed early reset (ge1); W reg on write ports, arrival-table set one-hots (o_w), exponent writes (g_ew e_w/a_w),
  wrng/wdup; parity address bits sampled at W edge. tb: 2-edge ref relay under the define.
  Bench (epyc8 $L/bench2_{wreg,base}.log): wreg 21/21 PASS, base PASS.
  NOTE: 13fbc4181e message got truncated by shell quoting and has no trailer. Do not rewrite; add a follow-up commit adding
  $L/xs4_lec.sh as tools/s81_slice/xs4_lec.sh with the full message + "Co-Authored-By: Claude <Model> 5.5" trailer.
- Default-off LEC (yosys equiv, main 39d243610b $L/xs4_main_39d243610b.sv vs new file): first run failed on a script bug
  (missing support files, ot_v41_inc); rerun epyc8 client PID 1126734, out $L/lec_off2/{lec.log,equiv_status.txt},
  log $L/lec_off2.otrun.log (yosys read alone ~50 min). On EQUIVALENT: follow-up commit, ot-push-main from the clone
  (clone is on epyc10; copy of inputs on epyc8 $L/clone), post define+sha+"+1 latency xs4 (xw_v/xw_d/fault)" to S81-J6-ASSEMBLY-R3.

## 2. t9 WREG proof kit -- running, BUT hand-written env (COORD ruling d442c09bb6e)
- unit oth-ubuntu-949753 epyc8 (client PID 948431), kit $L/t9_wreg/dsdv_slice_c1x_C__t9 (copy of $L/t9_c1n/gen + xs4 with
  `define OT_S81SL_XS4_WREG), GOAL grt, log run_grt.log. Read post-hook CTS (OT_CTS_POST_TIMING) + GRT; check gd_b->u_mem wd_i
  (2,113) and xf->f_d (1,603, xfin DLV=1) paths.
- config.mk vs wave kit (465cb9fe2d3 attempt_2): effective env identical, but MISSING OT_GPL_SPARSE_OVERFLOW = 0.25; other diffs
  plan-derived (SDC sha, OT_TAP_MAX_SINKS 1000 vs 1500, OT_TAP_SPAN_UM 300, OT_RELAY_MID_HALF_*, OT_PLACE_MAX_TRANSITION 320).
  Next iteration: regenerate with the exact wave env/gen args (incl OT_PGCAP grt_pre hook, OT_IO_HOLD, OT_GPL_SPARSE_UTIL).
- Gen script $L/t9_kit_e8.sh (R1 t36 template env subset). C1n tree copy $L/candC1n (plan 44be6051), rtpin $L/rtpin/93b5c482240d.

## 3. t37 lever 2 (FABLE-CLOSURE-0600): FSTART + reach1
- $L/t37_reach: reach_rules.py fix --rules 1 --types ^slice_station__t37$ on C1n: R-REACH-1 2 errors -> 0 (reader_start depth 5
  share_trunk 6 hubs; writer_start/FSTART depth 4, 5 branches). Plan $L/t37_reach/plan_t37_reach1.json.
- Private strict gate running: epyc8 client PID 1087032 (unit oth-ubuntu-1088408), script $L/t37_gate.sh, tree $L/candC1n_t37
  (hardlinks of $L/candC1n, real copy of physical/die_plan/s81), out $L/gates/candC1n_t37, log $L/t37_gate.log (~70 min).
- Then: t37 kit with the WAVE env/gen args (not the t36 template), GOAL route to sign-off; on sign-off rows to S81-J6-ASSEMBLY-R3
  and the same fix on slice_station siblings (t51 next).

## 4. Other units
- t36 on C1n: epyc10 unit oth-ubuntu-344587, kit $W/t36_c1n/gen/slice_station__t36 (template env -> same ruling caveat).
  POST-hook CTS setup +141.35, hold -78.3; pre-GRT hold -69.3 port_in only (limit -240), setup +106.7; in GRT.
- c1x_C census 6 yosys jobs epyc10 $W/census/t{1,5,6,7,8,10}/stats.json (running 1 h+); -> strip/body sizes to S81-J6-ASSEMBLY-R3.
- t6 attempt_46: not live anywhere (posted). R1 benches/t9 epyc10 clients cancelled (never admitted).
- census DONE: totals posted (t1 335k, t5 329k, t6 352k, t7 332k, t8 363k, t10 341k generic); per-module strip/body split still to compute.
