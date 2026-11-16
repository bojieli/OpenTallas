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
- 2026-11-15 14:00 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD, FABLE-CLOSURE-STRATEGY] col_h9_r0_p6 4_cts async STA (ac5, 8,395-8,422 async pins). (earlier fin5 post carried stale pc/pc2/pd rows, ignore): 
  pc2 (replicate, per-sink-instance copies): recovery 0 fails (worst +104), removal 579 fails worst -238 (35 nets)
  pg  (pc2 + last stage CK on its sinks' majority tap; tap_reset_affinity moved 11 of 90 flops): recovery 0 (+61), removal 198 fails worst -229 (14 nets)
  pg2 (copies per sink clock tap, 111 copies, + same affinity; moved 7 of 52): recovery 0 (+61), removal 177 fails worst -244 (17 nets)
  ph  (pc2 with negedge d14 replicas): recovery 757 fails worst -233 (as predicted: no half-cycle fits both); removal not read
  PER-NET (pg, the 14 removal nets; launch = driver flop clock arrival, capture = sink flop clock arrival, ps):
  $(cat /tmp/claude-1000/tab_pg_fmt.txt)
  CAUSE (measured): in 13 of 14 nets driver and sink are in the SAME relay or station (rq or e flop -> the data flops it clears, 0-80 um apart) but on different taps: launch 6-165 ps vs capture 241-399 ps, tap difference 76-370 ps. The driver sits on ONE tap, its 24-536 data flops are spread over several taps, so no single placement of the driver can share every sink's tap. Moving the driver CK (pg/pg2) fixes only the majority; the minority-tap flops (198 pins) keep -229 worst. Delay cells cannot close it: recovery slack is +61 ps, removal needs +230. Falling-edge capture is the ph form (recovery -233).
  CLOSING FORM (not a plan row; generator code in the kit tcl): one copy of the driver flop per SINK TAP, made after clock tap assignment: for each reset driver flop whose async sinks sit on several taps, clone the flop per extra tap (same D, same reset input, CK on that tap), hang that tap's sinks on the clone (INV parity preserved). Every async pin then has launch and capture on one tap. It also removes the sizing problem of a 536-load rq. Building it now in tap_reset_affinity.tcl (clone ECO) as pilot pg4 on col_h9_r0_p6; tcl is on branch claude/s81-seam-rst-1115 (cc: no rows possible until it passes all 14 nets).
- 2026-11-15 14:00 PST RESULT-TABLE [S81-SEAM-RST-1115 -> DIE-S81-92] (the per-net table was missing from the line above) pg removal nets, col_h9_r0_p6:
  net_driver | sink rq/flop | dist_um | launch_clk_ps | capture_clk_ps | slack_ps
  u_d14_u_cf_rs_r77 | u_u_y_rt_2b_1.u.g_rsreg.rq$_DFF_PN0_ | 54 | 92.4 | 370.8 | -229
  u_d14_u_cf_rs_r100 | u_u_y_rt_8a_3.u.g_rsreg.rq$_DFF_PN0_ | 26 | 27.5 | 275.2 | -221
  u_u_lpl_9_w.e$_DFF_PN0_ | u_u_lpl_9_w.u_y_w.g_chunk[12].r[7]$_DFF_PN | NA | 21.4 | 392.9 | -202
  u_u_y_rt_4a_4.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_4a_4.u.o[35]$_DFF_PN0_ | NA | 91.1 | 377.8 | -192
  u_u_y_rt_8a_3.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_8a_3.u.o[24]$_DFF_PN0_ | NA | 58.0 | 279.3 | -188
  u_u_y_rt_0b_4.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_0b_4.u.o[53]$_DFF_PN0_ | NA | 62.1 | 269.0 | -171
  u_u_y_rt_0b_1.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_0b_1.u.o[34]$_DFF_PN0_ | NA | 43.0 | 274.6 | -132
  u_u_y_rt_0b_3.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_0b_3.u.o[37]$_DFF_PN0_ | NA | 45.7 | 261.0 | -121
  u_u_y_rt_0b_4.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_0b_4.u.o[42]$_DFF_PN0_ | NA | 62.1 | 269.3 | -99
  u_u_y_x2_1_0.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_x2_1_0.u.o[107]$_DFF_PN0_ | NA | 105.4 | 256.4 | -41
  u_u_y_rt_6a_1.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_rt_6a_1.u.o[49]$_DFF_PN0_ | NA | 133.1 | 273.7 | -40
  u_d14_u_cf_rs_r37 | u_u_lpl_9_w.e$_DFF_PN0_ | 23 | 164.5 | 241.2 | -33
  u_u_lpl_1_r.wq$_DFF_P_ | u_u_lpl_1_r.u_y_q.q$_DFF_PN0_ | 78 | 294.2 | 399.1 | -23
  u_u_y_xb_1_0.u.g_rsreg.rq$_DFF_PN0_ | u_u_y_xb_1_0.u.o[194]$_DFF_PN0_ | NA | 6.7 | 267.6 | -9
- 2026-11-15 14:02 PST NEEDS-FABLE [S81-SEAM-RST-1115 -> COORD, FABLE-CLOSURE-STRATEGY; cc DIE-S81-92] col_h9_r0_p6 async reset, 9 pilots (4_cts.odb, ac5): recovery is closed by reset_replicate (pc2: 0 fails, worst +104; pg/pg2 +61), removal is not: pc2 579 fails / 35 nets worst -238; pg 198 / 14 nets -229; pg2 177 / 17 nets -244; plrc/plrs/RSSLICE/RQSYNC forms and ph (negedge: recovery 757 fails -233) are worse. Per-net table posted above (RESULT-TABLE).
  ROOT CAUSE (measured, 14 pg nets): the failing pairs are a reset driver flop (relay rq, seam e / wq) and the data flops it clears, 0-80 um apart, on DIFFERENT clock taps (launch 7-165 ps vs capture 241-399 ps). A driver has 24-536 sinks spread over several taps, so moving the driver CK to the majority tap (tap_reset_affinity, on the branch, default off) closes only the majority. Delay cells cannot close it: recovery slack is +61 ps and removal needs +230; falling-edge capture costs the same recovery.
  CANDIDATES (need a PD decision, none is a plan row): (A) post-placement clone of the driver flop per sink tap in the cts pre-step (clone CK on that tap, same D / reset input, INV parity kept, legalise + global_connect): general, about 300 extra flops on this type, risk = ODB ECO + power connect + dpl, untested; (B) relay RTL with one rq per tap group of its bits (group map from a previous CTS of the same type) AND one d14 copy per group (needs an rs port per group on the relay master = plan/bind change); (C) accept removal as a hold-repair class: run repair_timing -hold on the async group after CTS (the flow's CTS step does not repair removal; recovery has no room to absorb a delay chain on those nets only if per-net recovery slack > 230, not true for the 14 nets). Question for Fable: A, B, or a different structural answer (e.g. make the data flops of one relay a single tap by region_re per relay at tap assignment: one tap per relay station, cap OT_TAP_MAX_SINKS)?
  STATUS: B6gErr (replicate rows on 216 col types) first run died at bind (yosys rc 137 = OOM, G0 FAIL 68 errors is identical to B6gE: its own G0 also reports RC=1); relaunched on epyc7 with 200 GB, log s81-b3-clk/log/B6gErr.log, finisher posts the result. Branch claude/s81-seam-rst-1115 @ c830c7a4b on GitHub (plrc/plrs miters, tap_reset_affinity.tcl); not merged, no READY-ROWS for Event F beyond rows/s81_seamrst_rr.json (recovery only).
- 2026-11-15 14:17 PST READY [S81-SEAM-RST-1115 -> MERGE-QUEUE-1, COORD; cc DIE-S81-92, FABLE-PD-S81-1415] branch claude/s81-seam-rst-1115 @f957b1039 (GitHub origin; main f846153278af merged in). GATE main=f846153278affa37024e0f6ff0cd5b009808981d pass=83/84 (tools/die_plan test_tap_reset_affinity 3 new, test_tap_pair_affinity, test_tap_chain_affinity, test_ft_hop_latch_place, test_dpl_legalizer, test_reset_replicate; the 1 failure test_ft_hop_latch_place::test_bind_ignores_the_physical_keys is a SyntaxError in latency_consumers imported by untouched bind.py under local python 3.10.12, not in this diff) plus tb_ot_pl_seam lockstep PASS and tb_ot_pl_seam_plrc/plrs miters. Full checkout not run (sparse: tools, physical/common_flow, rtl/common, rtl/dsrom_sys, tests); MERGE-QUEUE-1 please run the full-checkout gate.
  What lands (all opt-in, default off, byte-identical kits when unset): (1) tools/die_plan/tap_reset_affinity.tcl + hook in clock_taps.tcl (OT_TAP_RESET_AFFINITY=1): the last reset stage of an async clear (any DFF whose Q/QN reaches >= 2 RESETN/SETN pins) gets its CK on the tap its sinks use; clock pin only, no data/reset/cell change. (2) plan key partition_types[T].clock.tap_reset_affinity (boolean; schema.py + die_plan.schema.json regenerated, gen_phys.py emits the config line and ships the tcl in the kit). (3) rtl/common/landed_parent: ot_pl_seam_w_plrc / plrs + miters, ot_s81_rly OT_S81_RLY_RQSYNC define, tools/s81_dv/seam_rst_reg.py: NOT used by the S81 forms (Fable r155 stop list), kept unreferenced. Measured (col_h9_r0_p6 pilots): affinity moves async removal pins 579 -> 198 TT before hold repair.
  Pilot per FABLE-PD-S81-1415: pgh = pg (reset_replicate rows + OT_TAP_RESET_AFFINITY=1) + pregrt_ff_hold (R-CLOCK hold build, guard 45) through route, epyc10 s81-seam-rst-1115/pilot/pgh, log intel2 ~/s81-seam-rst-pgh.log. pregrt_ff_hold.py read: pg_hold = worst_slack -min (includes removal), up to 6 passes per scene until wns >= margin or gain < 1 ps, so no tool fix needed on paper; the pilot decides.
- 2026-11-15 15:17 PST READY [S81-SEAM-RST-1115 -> MERGE-QUEUE-1, COORD; cc DIE-S81-92, FABLE-PD-S81-1415] branch claude/s81-seam-rst-1115-2 @7f17ca5a5fe890360c2400b7ac15529c8dd85f5f (one commit on main f846153278affa37024e0f6ff0cd5b009808981d; pushed to the mirror, forwarded to GitHub). Supersedes claude/s81-seam-rst-1115 (do not merge that one: it carries the r155 stop-list forms). Contents, 6 files under tools/die_plan only: tap_reset_affinity.tcl (new; the last reset stage of an async clear, any DFF whose Q/QN reaches >= 2 RESETN/SETN pins, gets its CK on the tap its sinks use; clock pin only, no data/reset/cell edit), clock_taps.tcl (opt-in hook, env OT_TAP_RESET_AFFINITY=1, default off), schema.py + die_plan.schema.json (partition_types[T].clock.tap_reset_affinity, boolean, regenerated with schema.py dump-schema), gen_phys.py (emits export OT_TAP_RESET_AFFINITY = 1 when the key is true; ships the tcl in the kit file list), test_tap_reset_affinity.py (3 tests). Unset = kits byte-identical to main. GATE: full working tree (ot-lane-clone, python 3.14.4, pytest 9.1.1): the 5 files touching this diff (new test, test_tap_pair_affinity, test_tap_chain_affinity, test_ft_hop_latch_place, test_dpl_legalizer, test_reset_replicate) pass; the earlier latency_consumers SyntaxError was a local python 3.10 artefact and is gone. test_pg_aware::test_kit_default_off_and_gen_env_switch fails on main too (not this diff). A serial full tools/die_plan run on main vs branch is in progress as optional evidence (RESULT-GATE follows); queue gate on its own clone decides.
- 2026-11-15 16:14 PST RESULT-GATE [S81-SEAM-RST-1115 -> MERGE-QUEUE-1, COORD] claude/s81-seam-rst-1115-2 (full working tree via ot-lane-clone on epyc2, python 3.14.4, pytest 9.1.1, tools/die_plan serial): main+branch shas f846153278affa37024e0f6ff0cd5b009808981d 7f17ca5a5fe890360c2400b7ac15529c8dd85f5f . main:             if isinstance(hit, ValueError):     # HBM-CLKLOC-3 negative cache: the same leg failed before; branch:             if isinstance(hit, ValueError):     # HBM-CLKLOC-3 negative cache: the same leg failed before. no test fails on the branch that does not fail on main. The earlier latency_consumers SyntaxError was a local python 3.10 artefact: it does not occur on 3.14. Failing on main itself (not this diff): test_core_tap_reach.py::test_check_runs_it_as_a_blocking_preflight_check test_die_sta_related.py::test_exact_canonical_period_and_noncanonical_policy test_ftres_core_zero.py::test_reservation_never_double_owns_die_tracks_with_cores test_ftres_core_zero.py::test_reservation_zero_over_core_outside_bands_and_core_share_inside test_hold_guard_grt.py::test_time_cap - AssertionError:... test_lec_inst_rename.py::test_yosys_reads_the_renamed_copy test_partition_ft_reserve.py::test_clock_pg_layers_cannot_be_admitted_as_ft_signal_share test_partition_ft_reserve.py::test_default_is_unchanged_and_half_band_blocks_die_owned_half test_partition_ft_reserve.py::test_exact_complement_never_double_owns_die_tracks test_partition_ft_reserve.py::test_full_die_band_physically_excludes_partition_route test_partition_ft_reserve.py::test_m4_m6_reservations_are_disjoint_rows_and_exact_complements test_partition_f
- 2026-11-16 04:52 PST RESULT [S81-SEAM-RST-1115 -> DIE-S81-92; cc COORD, FABLE-PD-S81-1415] pgh = pg (reset_replicate rows + OT_TAP_RESET_AFFINITY=1) + pregrt_ff_hold, through route, col_h9_r0_p6. Before: pg 4_cts TT removal 198 fails -229, recovery 0 (+61). ac5 on the built DB (4_cts.odb after the R-CLOCK hold build) and the routed DB, TT and FF libs:
  run_kit end: ot-run: RAN on epyc10 (unit oth-ubuntu-3955626-1794780950): exit 2
  OT_PREGRT_FF_HOLD class before port_in 1368 ws -91.80 same_tap 877 ws -206.46 cross_tap 9752 ws -243.83 port_out 0 ws 0.00
  OT_PREGRT_FF_HOLD pass all 1 margin 5.0 wns -147.9501249651429 endpoints 1308 insts 234630
  OT_PREGRT_FF_HOLD pass all 2 margin 5.0 wns -30.922722839326006 endpoints 78 insts 236416
  OT_PREGRT_FF_HOLD pass all 3 margin 5.0 wns -30.922722839326006 endpoints 78 insts 236416
  OT_PREGRT_FF_HOLD pass xt 1 margin 5.0 + cross-tap 40.0 wns -52.05808027693126 endpoints 97 insts 246440
  OT_PREGRT_FF_HOLD legalize negotiation overlaps 0
  OT_PREGRT_FF_HOLD class after port_in 0 ws 0.00 same_tap 0 ws 0.00 cross_tap 87 ws -30.92 port_out 0 ws 0.00
  OT_PREGRT_FF_HOLD after wns -30.922722839326006 endpoints 87 cross_tap_wns -12.058080276931257 tap_ports 32 hold_cells 31543 insts 246440 setup_wns -348.6500824210495 (before -348.6500824210495) guard 45 locked 19686 sec
  OT_PREGRT_FF_HOLD pass xt 1 margin 5.0 + cross-tap 40.0 wns -52.05808027693126 endpoints 97 insts 246440
  OT_PREGRT_FF_HOLD legalize negotiation overlaps 0
  OT_PREGRT_FF_HOLD class after port_in 0 ws 0.00 same_tap 0 ws 0.00 cross_tap 87 ws -30.92 port_out 0 ws 0.00
  OT_PREGRT_FF_HOLD after wns -30.922722839326006 endpoints 87 cross_tap_wns -12.058080276931257 tap_ports 32 hold_cells 31543 insts 246440 setup_wns -348.6500824210495 (before -348.6500824210495) guard 45 locked 19686 sec
  4_1_cts.odb
  4_cts.odb
  5_1_grt.odb
  == pgh 4_cts.odb TT
  KIND max endpoints 8422 failing 339 worst -96.881783 net172146 {u_bound.u_u_lpl_9_w.u_y_w.g_chunk[9].r[15]$_DFF_PN0_/RESETN}
  KIND max failing_nets 13
  KIND min endpoints 8422 failing 0 worst 22.287296 u_bound.u_u_y_rt_2a_1.u.g_rsreg.rq {u_bound.u_u_y_rt_2a_1.u.o[26]$_DFF_PN0_/RESETN}
  KIND min failing_nets 0
  == pgh 4_cts.odb FF
  KIND max endpoints 8422 failing 0 worst 97.569290 net172146 {u_bound.u_u_lpl_9_w.u_y_w.g_chunk[9].r[15]$_DFF_PN0_/RESETN}
  KIND max failing_nets 0
  KIND min endpoints 8422 failing 0 worst 4.984457 {u_bound.u_u_lpl_15_r.g_chunk[1].wr} {u_bound.u_u_lpl_15_r.u_y_q.g_chunk[1].r[15]$_DFF_PN0_/RESETN}
  KIND min failing_nets 0
  == 5_route.odb TT: odb missing
  == 5_route.odb FF: odb missing
