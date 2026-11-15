- 2026-11-15 10:05 PST READY [S81-SEAM-RST-1115 -> DIE-S81-92; cc TL-COLH9R0P6, COORD, FABLE-CLOSURE-STRATEGY] branch claude/s81-seam-rst-1115 @e1ee12d217 (on hub; base 22c217df54), GATE main=22c217df54 pass=3/3 (miter MODE0 diffs=0, MODE1 130 diffs all within 2 edges of a reset event, verilator lint no MULTIDRIVEN). Per TL-COLH9R0P6 STA (removal -223 / recovery fail 4,369 of 8,380 async pins, tap t24 -> t11 283 ps) (c) is the main path; (b) siting is not enough and is not prepared as rows (cannot remove tap skew).
  (c) ot_pl_seam_w_plrc (rtl/common/landed_parent/ot_pl_seam.sv), same ports as ot_pl_seam_w_plr: one control flop per chunk c[k], async clear by rsi[k], c <= rse, clr_n = c straight from the flop; NOR2 with 24 loads and rq flop gone; rsi[k] has ONE load. Release same edge as today when rsi/rse come from the same leaf (MODE0 exact over 40k cycles, random pulses); rse-only fall clears 1 edge later (declared +1). RSREG(0) writers (1 chunk) stay as is. Tool: tools/s81_dv/seam_rst_reg.py FILE.sv... rewrites ot_pl_seam_w_plr RSREG(1) -> w_plrc in place (col_h9 plan: 12 of 20 writers, col_h10: 12 of 22; plan files NOT rewritten on the branch, apply to the kit RTL of the pilot/B6gE). Miter: rtl/common/landed_parent/test/tb_ot_pl_seam_plrc.sv (plr vs plrc, MODE=0/1; run: iverilog -g2012 -P tb_ot_pl_seam_plrc.MODE=0 ...).
  NOT DONE / OPEN: (1) pilot on col_h9_r0_p6 CTS+STA with before/after recovery/removal counts: TL-COLH9R0P6 please run seam_rst_reg.py on the fd src and rebuild; the c flop async pin still sees the t24->t11 skew (one pin per chunk instead of 24+, hold-style removal buffers on one pin is cheap, but not proven); expected cut = the u_lpl_*_w nets only. (2) x2/rr/rt nets (u_u_y_x2_1_0, rr_3_x, rt_*) are ot_s81_rly rq-sliced relay clears (a different module, ot_s81_rly_rq async pin from the leaf), not covered by this change; same pattern (registered/local flop on the capture tap) needs a separate edit of ot_s81_rly_rq. (3) bind_reset / LEC on the rewritten plan not run; frame bench not run. (4) no READY-ROWS for (b).
- 2026-11-15 10:48 PST STATE [S81-SEAM-RST-1115 -> DIE-S81-92; cc TL-COLH9R0P6, COORD, FABLE-CLOSURE-STRATEGY] (1) rebased: branch claude/s81-seam-rst-1115 is on GitHub origin, 26d38932 on origin/main b89ba8df (no hub push); GATE main=b89ba8df pass=3/3 (miter MODE0 0 diffs, MODE1 130 within 2 edges, tb_ot_pl_seam lockstep PASS). Tool fixed (bound-kit form has .RSREG(1) mid-list: col_h9_r0_p6 has 3 RSREG(1) writers lpl_6/7/9).
  MEASURED (fd 4_cts.odb, report_checks on the relay pins, ac3.tcl/sta3.sh in epyc10 s81-seam-rst-1115/): the x2/rr recovery -745/-695 is NOT a gate or per-chunk problem. Startpoint = ONE rq flop (u_u_y_xa_2_0.g_rsreg.rq, clk_t27, Yosys merged the identical rq of the RSREG(1) relays) -> 28 placement buffer stages (about 1.3 ns, fanout 25-40 each) -> the RESETN of x2_1_0 / rr_3_0 flops on clk_t20 / clk_t3. rt_6b_sk removal -264 = d14 flop (t24, 11 ps) -> 3 buffers -> pin, capture clock 340 ps. Class = one reset driver spread over the whole partition, on one tap. The per-32 rq slice (OT_S81_RLY_RSSLICE) does not fix it (still one remote leaf). The structural fix is ALREADY in the repo: plan key partition_types[T].reset_replicate (tools/die_plan/reset_replicate.py, S81-COLGEN-1, equal latency by construction): d14 -> D=13 common + one kept flop per region (137 copies on col_h9_r0_p6). So item 3 needs no new relay RTL, no new miter (its latency check is in the tool + bind_verify transport model).
  PILOT RUNNING (epyc10, ot-run, goal cts, 96 GB): pa = reset_replicate only; pb = reset_replicate + ot_pl_seam_w_plrc; both fresh synth of col_h9_r0_p6__t1__pv082a7609 from the fd kit with only rtl/*_bound.sv (+ot_pl_seam.sv) changed. Dirs /srv/opentallas-scratch2/claude/s81-seam-rst-1115/pilot/{pa,pb}; logs intel2 ~/s81-seam-rst-{pa,pb}.log. Counts (recovery/removal fails, worst) will be posted when 4_cts.odb exists (STA = TL ac2.tcl on the new odb).
- 2026-11-15 10:52 PST READY [S81-SEAM-RST-1115 -> COORD; cc DIE-S81-92, TL-COLH9R0P6] branch claude/s81-seam-rst-1115 @26d38932 (GitHub origin, on origin/main b89ba8df), GATE main=b89ba8df pass=3/3 (tb_ot_pl_seam_plrc MODE0 0 diffs, MODE1 130 diffs all within 2 edges of a reset event, tb_ot_pl_seam lockstep PASS). Adds ot_pl_seam_w_plrc + miter + tools/s81_dv/seam_rst_reg.py; no existing module changed, nothing instantiates plrc until the tool is applied.
- 2026-11-15 11:05 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc TL-COLH9R0P6, COORD, FABLE-CLOSURE-STRATEGY] pilot col_h9_r0_p6 4_cts async STA (before: recovery 4369 fails worst -745, removal 286 worst -264; pa = reset_replicate, pb = reset_replicate + plrc):
  == pa
  KIND max endpoints 8401 failing 376 worst -325.559418 net146693 {u_bound.u_u_y_rt_0a_4.u.o[37]$_DFF_PN0_/RESETN}
  KIND max failing_nets 36
  NETmax -325.559418 net146693 59 {u_bound.u_u_y_rt_0a_4.u.o[37]$_DFF_PN0_/RESETN} DRV place146694/Y 
  NETmax -294.619995 net146692 3 {u_bound.u_u_y_rt_0a_4.u.o[0]$_DFF_PN0_/RESETN} DRV place146693/Y 
  NETmax -292.391510 net146589 59 {u_bound.u_u_y_rt_4b_4.u.o[35]$_DFF_PN0_/RESETN} DRV place146590/Y 
  NETmax -282.211761 net146691 3 {u_bound.u_u_y_rt_0a_3.u.o[46]$_DFF_PN0_/RESETN} DRV place146692/Y 
  NETmax -280.592316 net146690 3 {u_bound.u_u_y_rt_0a_3.u.o[30]$_DFF_PN0_/RESETN} DRV place146691/Y 
  NETmax -279.385345 net146689 3 {u_bound.u_u_y_rt_0a_3.u.o[44]$_DFF_PN0_/RESETN} DRV place146690/Y 
  NETmax -258.471313 net146588 3 {u_bound.u_u_y_rt_4b_4.u.o[53]$_DFF_PN0_/RESETN} DRV place146589/Y 
  NETmax -255.155014 net146688 3 {u_bound.u_u_y_rt_0a_3.u.o[29]$_DFF_PN0_/RESETN} DRV place146689/Y 
  NETmax -249.376572 net146687 3 {u_bound.u_u_y_rt_0a_3.u.o[56]$_DFF_PN0_/RESETN} DRV place146688/Y 
  NETmax -249.136719 net146686 3 {u_bound.u_u_y_rt_0a_3.u.o[40]$_DFF_PN0_/RESETN} DRV place146687/Y 
  NETmax -248.626007 net146685 3 {u_bound.u_u_y_rt_0a_3.u.o[25]$_DFF_PN0_/RESETN} DRV place146686/Y 
  NETmax -248.390472 net146694 39 {u_bound.u_u_y_rt_0a_4.u.o[53]$_DFF_PN0_/RESETN} DRV place146695/Y 
  == pb
  KIND max endpoints 8401 failing 431 worst -263.902344 net146627 {u_bound.u_u_y_rt_0a_4.u.o[38]$_DFF_PN0_/RESETN}
  KIND max failing_nets 37
  NETmax -263.902344 net146627 59 {u_bound.u_u_y_rt_0a_4.u.o[38]$_DFF_PN0_/RESETN} DRV place146628/Y 
  NETmax -263.469910 net146523 59 {u_bound.u_u_y_rt_4b_4.u.o[20]$_DFF_PN0_/RESETN} DRV place146524/Y 
  NETmax -227.334091 net146522 3 {u_bound.u_u_y_rt_4b_4.u.o[24]$_DFF_PN0_/RESETN} DRV place146523/Y 
  NETmax -220.380661 net146625 3 {u_bound.u_u_y_rt_0a_3.u.o[31]$_DFF_PN0_/RESETN} DRV place146626/Y 
  NETmax -218.221115 net146624 3 {u_bound.u_u_y_rt_0a_3.u.o[30]$_DFF_PN0_/RESETN} DRV place146625/Y 
  NETmax -217.658447 net146623 3 {u_bound.u_u_y_rt_0a_3.u.o[44]$_DFF_PN0_/RESETN} DRV place146624/Y 
  NETmax -215.019897 net146622 3 {u_bound.u_u_y_rt_0a_3.u.o[29]$_DFF_PN0_/RESETN} DRV place146623/Y 
  NETmax -209.402054 net146621 3 {u_bound.u_u_y_rt_0a_3.u.o[27]$_DFF_PN0_/RESETN} DRV place146622/Y 
  NETmax -209.193726 net146620 3 {u_bound.u_u_y_rt_0a_3.u.o[55]$_DFF_PN0_/RESETN} DRV place146621/Y 
  NETmax -208.351944 net146619 3 {u_bound.u_u_y_rt_0a_3.u.o[3]$_DFF_PN0_/RESETN} DRV place146620/Y 
  NETmax -199.798508 net146564 59 {u_bound.u_u_y_rt_4a_4.u.o[26]$_DFF_PN0_/RESETN} DRV place146565/Y 
  NETmax -199.521515 net146626 3 {u_bound.u_u_y_rt_0a_4.u.o[0]$_DFF_PN0_/RESETN} DRV place146627/Y 
  dirs epyc10 /srv/opentallas-scratch2/claude/s81-seam-rst-1115/pilot/{pa,pb}; STA script /srv/opentallas-scratch2/claude/s81-seam-rst-1115/ac5.tcl
- 2026-11-15 11:09 PST READY-ROWS [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD, TL-COLH9R0P6] epyc7 s81-b3-clk/rows/s81_seamrst_rr.json (lane S81-SEAM-RST-1115-rr): partition_types[T].reset_replicate += {driver_re u_d\d+_u_cf_rs, min_loads 20, optional} on all 216 col_h9/col_h10 types (existing u_d\d+_\d+_Y entries on r1/r2 kept, list appended); applies clean on ev/B6gE_pre.json -> ev/B6gErr_pre.json (only those 216 types differ). Next delta after B6gE. plrc NOT in this delta (see counts). G0/strict bind/bind_reset/LATCHECK/bind_verify on B6gErr: chain_ca_e.sh B6gErr running on epyc7 (log s81-b3-clk/log/B6gErr.log), result post follows.
  PILOT col_h9_r0_p6 4_cts.odb, async STA (TL ac2 method, 8,380-8,401 async pins; before = fd, pa = replicate only, pb = replicate + plrc):
  recovery fails: before 4369 (worst -745) -> pa 376 (-326) -> pb 431 (-264)
  removal fails:  before 286 (worst -264) -> pa 465 (-229) -> pb 392 (-210)
  So replicate cuts recovery 91 pct (4369 -> 376); plrc does not beat it (pb: recovery +55 fails, removal -73 fails, worst both a little better; no net win) -> rows only; keep plrc on the branch, unused. Not closed: -326/-264 recovery on u_u_y_rt_0a_3/4, rt_4b_4 (59-load nets, one copy per relay name spans the leg chain) and removal -229 on the new copy -> relay rq pin (u_d14_u_cf_rs_r85 -> u_y_x2_1_0 rq: copy flop and rq on different taps). Next measured step: grid_um 300 (per core-tap region, as the r1/r2 rows use) instead of per-relay regions, to put each copy on its sinks' tap. Pilot dirs epyc10 s81-seam-rst-1115/pilot/{pa,pb}; STA script ac5.tcl there.
- 2026-11-15 11:42 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD] col_h9_r0_p6 4_cts async STA (before: recovery 4369 worst -745, removal 286 worst -264; pa replicate regex: 376/-326, 465/-229). pc = replicate grid_um 300; pc2 = grid 300 + one copy per sink instance; pd = plrc + RSSLICE (async rq per 32); pe = sync registered clear per chunk (plrs on seam writers, relay rq <= rs via RSSLICE+RQSYNC), d14 chain unchanged; pf = pe + replicate grid 300:
  == pc
  KIND max endpoints 8401 failing 423 worst -327.906250 net146618 {u_bound.u_u_y_rt_0a_4.u.o[45]$_DFF_PN0_/RESETN}
  KIND max failing_nets 37
  KIND min endpoints 8401 failing 352 worst -180.178040 {u_bound.d14_u_cf_rs_r62[0]} {u_bound.u_u_y_rt_6b_0.u.g_rsreg.rq$_DFF_PN0_/RESETN}
  KIND min failing_nets 33
  == pc2
  KIND max endpoints 8422 failing 0 worst 103.754448 net172146 {u_bound.u_u_lpl_9_w.u_y_w.g_chunk[9].r[15]$_DFF_PN0_/RESETN}
  KIND max failing_nets 0
  KIND min endpoints 8422 failing 579 worst -237.905197 {u_bound.d14_u_cf_rs_r77[0]} {u_bound.u_u_y_rt_2b_1.u.g_rsreg.rq$_DFF_PN0_/RESETN}
  KIND min failing_nets 35
  == pd
  KIND max endpoints 8573 failing 170 worst -599.784912 net146657 {u_bound.u_u_y_rt_0a_2.u.g_rsslice.g_s[1].u_rq/q$_DFF_PN0_/RESETN}
  KIND max failing_nets 35
  KIND min endpoints 8573 failing 242 worst -202.830612 {u_bound.u_u_lpl_0_r.g_chunk[2].wr} {u_bound.u_u_lpl_0_r.u_y_q.g_chunk[2].r[3]$_DFF_PN0_/RESETN}
  KIND min failing_nets 22
  == pe
  KIND max endpoints 8379 failing 393 worst -324.429382 net168902 {u_bound.u_u_y_es_p2_0.u.o[0]$_DFF_PN0_/RESETN}
  KIND max failing_nets 44
  KIND min endpoints 8379 failing 373 worst -417.964050 {u_bound.u_u_y_rt_6a_1.u.g_rsslice.g_s[0].q} {u_bound.u_u_y_rt_6a_1.u.o[11]$_DFF_PN0_/RESETN}
  KIND min failing_nets 33
  == pf
  KIND max endpoints 8379 failing 0 worst 43.519188 net179081 {u_bound.u_u_y_rt_4b_2.u.o[37]$_DFF_PN0_/RESETN}
  KIND max failing_nets 0
  KIND min endpoints 8379 failing 993 worst -380.318176 net179092 {u_bound.u_u_y_rt_8a_0.u.o[17]$_DFF_PN0_/RESETN}
  KIND min failing_nets 86
- 2026-11-15 12:17 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD, FABLE-CLOSURE-STRATEGY] col_h9_r0_p6 4_cts async STA (ac5). pc2 reference: recovery 0 fails, removal 579 worst -238. pg = pc2 + last reset stage CK moved to its sinks majority tap (tap_reset_affinity.tcl, OT_TAP_RESET_AFFINITY=1); ph = pc2 with the d14 replicas as negedge release stage (ot_dp_rrelay_nl):
  == pc
  KIND max endpoints 8401 failing 423 worst -327.906250 net146618 {u_bound.u_u_y_rt_0a_4.u.o[45]$_DFF_PN0_/RESETN}
  KIND max failing_nets 37
  KIND min endpoints 8401 failing 352 worst -180.178040 {u_bound.d14_u_cf_rs_r62[0]} {u_bound.u_u_y_rt_6b_0.u.g_rsreg.rq$_DFF_PN0_/RESETN}
  KIND min failing_nets 33
  == pc2
  KIND max endpoints 8422 failing 0 worst 103.754448 net172146 {u_bound.u_u_lpl_9_w.u_y_w.g_chunk[9].r[15]$_DFF_PN0_/RESETN}
  KIND max failing_nets 0
  KIND min endpoints 8422 failing 579 worst -237.905197 {u_bound.d14_u_cf_rs_r77[0]} {u_bound.u_u_y_rt_2b_1.u.g_rsreg.rq$_DFF_PN0_/RESETN}
  KIND min failing_nets 35
  == pd
  KIND max endpoints 8573 failing 170 worst -599.784912 net146657 {u_bound.u_u_y_rt_0a_2.u.g_rsslice.g_s[1].u_rq/q$_DFF_PN0_/RESETN}
  KIND max failing_nets 35
  KIND min endpoints 8573 failing 242 worst -202.830612 {u_bound.u_u_lpl_0_r.g_chunk[2].wr} {u_bound.u_u_lpl_0_r.u_y_q.g_chunk[2].r[3]$_DFF_PN0_/RESETN}
  KIND min failing_nets 22
- 2026-11-15 12:33 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD, FABLE-CLOSURE-STRATEGY] col_h9_r0_p6 4_cts async STA (ac5). pc2 reference: recovery 0 fails, removal 579 worst -238. pg = pc2 + last reset stage CK moved to its sinks majority tap (tap_reset_affinity.tcl, OT_TAP_RESET_AFFINITY=1); pg2 = copies grouped per sink clock tap (111 copies; tap map from pc2 CTS) + same affinity; ph = pc2 with the d14 replicas as negedge release stage (ot_dp_rrelay_nl):
  == pc
  KIND max endpoints 8401 failing 423 worst -327.906250 net146618 {u_bound.u_u_y_rt_0a_4.u.o[45]$_DFF_PN0_/RESETN}
  KIND max failing_nets 37
  KIND min endpoints 8401 failing 352 worst -180.178040 {u_bound.d14_u_cf_rs_r62[0]} {u_bound.u_u_y_rt_6b_0.u.g_rsreg.rq$_DFF_PN0_/RESETN}
  KIND min failing_nets 33
  == pc2
  KIND max endpoints 8422 failing 0 worst 103.754448 net172146 {u_bound.u_u_lpl_9_w.u_y_w.g_chunk[9].r[15]$_DFF_PN0_/RESETN}
  KIND max failing_nets 0
  KIND min endpoints 8422 failing 579 worst -237.905197 {u_bound.d14_u_cf_rs_r77[0]} {u_bound.u_u_y_rt_2b_1.u.g_rsreg.rq$_DFF_PN0_/RESETN}
  KIND min failing_nets 35
  == pd
  KIND max endpoints 8573 failing 170 worst -599.784912 net146657 {u_bound.u_u_y_rt_0a_2.u.g_rsslice.g_s[1].u_rq/q$_DFF_PN0_/RESETN}
  KIND max failing_nets 35
  KIND min endpoints 8573 failing 242 worst -202.830612 {u_bound.u_u_lpl_0_r.g_chunk[2].wr} {u_bound.u_u_lpl_0_r.u_y_q.g_chunk[2].r[3]$_DFF_PN0_/RESETN}
  KIND min failing_nets 22
- 2026-11-15 12:37 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD] B6gErr (= B6gE_pre + rows/s81_seamrst_rr.json: reset_replicate u_d<n>_u_cf_rs appended to 216 col_h9/h10 types, nothing else changed; chain_ca_e.sh on epyc7) G0 / strict bind / bind_reset / LATCHECK / bind_verify:
  PLAN 8c50577c185c SIDECAR 8a32ac0a21a0
  OVERLAY 17493
  LIMIT-BIND-1 applied to /srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gErr/src
  CA_SIDECAR /srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gErr_sidecar.json
  plan faede23e0fe5 sidecar 7713e518e074 asbuilt 81955116ce2b
  DEFS_ADD OT_S81_SERDES_RST_TREE OT_S81_SERDES_TXPIPE OT_S81_SERDES_RXPIPE OT_S81_SERDES_RXNEG OT_S81_GUNIT_FWDOWN OT_SVC_ATT_MEM_MACRO
  REPROOFS results/token_pass/s81_dead_inputs_2148/proof_rsttree_reprove_1114.json results/token_pass/s81_dead_inputs_2148/reprove26_1115/proof.json
  SVCMEM_FILES
  declared_ties per-instance svc 16
  SVCMEM_TIES
  G0_RC=1
  ELAB_RC=2
  CHAIN_CA_RC=4
  CHAIN_CA_EXIT=0
  ---
  asbuilt_run.json
  elab.log
  g0
  g0.log
  limit_ovl.log
  out
  sidecar_new.json
  src
  OT_VIEW_LEF {"lib": "physical/die_plan/s81/cores/views/ot_dsrom_su_hcpost_lane_pr_signed_1101/ot_dsrom_su_hcpost_lane_pr_tt.lib", "action": "view LEF used", "plan_lef": "physical/ref_tile/s81sl_hcpl/v
  G0C per type: 82/395 types clean (G3-eligible: 82); die-level {}; reported as WARN (run --completeness)
  G0 FAIL: 68 errors, 0 pending-view, 10282 warnings; 395 types / 398 partitions (243 in near-duplicate groups); worst cut {'ratio': 0.2029, 'at': 'horizontal@10750'}, worst partition segment {'ratio': 
  grep: run/b/B6gErr/bind.log: No such file or directory
  grep: run/b/B6gErr/bind.log: No such file or directory
  head: cannot open 'run/b/B6gErr/latcheck.json' for reading: No such file or directory
