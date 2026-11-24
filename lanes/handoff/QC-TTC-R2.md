# QC-TTC-R2 handoff (lane memory) — successor of QC-TTC-RETIME, job = QC tt_ctlm only
Brief: COORD 11-23 22:10 (FABLE-RC-QC 80c2feea items 1-5). tt_ctlm HELD until combined-form probe TT>=-42, hold>=0.
Dirs: intel1 /srv/opentallas-scratch2/claude/QC-TTC-R2/{tool,pofix,rt_d10p,lecc_*,neg*}; epyc11 /srv/opentallas-scratch/claude/QC-TTC-R2/{tool,cores,census_rs1b,p_pofix,p_ncmd10}.
Adopted (read-only) inputs: intel1 QC-TTC-RETIME/{in (F5 1166f7d9630f + contracts.json), rs1 (out_unkeep e9be4831f164, work/resynth_yosys.v), tool}; epyc11 QC-TTC-RETIME/{probe.sh, tmplf5}.
Results 22:2x-22:4x:
- census (rs1 as probed, -185.46/-5817.4): u_hr->u_bout_native_cmd 23 ep -3761 worst -185.46; u_core internal 79 ep -1904 worst -65.70 (launch u_2367, u_11072); u_core->bout_cmd 6 ep -125 (-27.6); calrom->core 1 ep -27.4. Hold internal worst -18.47; -122.57 = start_i/arst_n IO.
- form: compose B1..C1d stages F5 1166f7 (staged 6a5f53239424 = calrom alias rename genblk10.g_dual_calrom -> g_calrom). -218.57 = c09b67b7cc1c late_cone (not composed).
- lec.sh (dsec) VACUOUS on 1-output miter (neg control inverted bit passes; bmc3 fires). rs1 has 447 undriven PO bits (native_cmd 357, cmd 90). fix_po.py -> pofix/out_unkeep_pofix.sv 293a1fc70026.
- native_cmd cone: 23 bits share one 498-gate depth-14 reduction over 487 sources, cone gates far (x~587), exclusive to native_cmd -> station after cone useless; rt_out.py retimed stage D=10 (402 flops, ck_hr, dff_p) -> rt_d10p/core_ncmd.sv 24d4fc86612d; LEC gold = rt_d10p/gold_ncmd.sv (source + 380 output regs).
- New LEC: tool/lec_comb.sh (register-correspondence comb CEC, ABC iprove). Sequential for ncmd: bmc3 + dprove (todo).
Next: read p_pofix / p_ncmd10 4_cts_post_hook + census; LEC results; class (b) fix; plan/RTL row (overlay rtl/qwen_dv/headprep13/corepub39/..._f5_cpub39_1.sv staged with calrom alias) + PRE + scoped strict bind; ROW-REBASED to QC-ALLFIX + FABLE-RC-QC; token schedule +1 on native_cmd (lane latency 4 unchanged at boundary; the stage is core-internal).
Update 23:18:
- p_pofix (epyc11 QC-TTC-R2/p_pofix, census_pofix): setup -122.46 / TNS -3384; class (b) u_core internal 104 ep worst -122.46 (u_11072/u_2367 broadcast); native_cmd -30.28 (passes); calrom -37.2; internal hold worst -43.26 (u_rrl_78->79). IO hold -136 (arst_n/start_i).
- p_ncmd10: -215.20 / TNS -37111, hold u_hr -48 / TNS -31k -> ROW-DROP TTC-NCMD-STAGE (no +1 cycle).
- LEC: tool/lec_comb.sh (neg control OK) says SAT on pofix vs source; tool/combsim.py 128 patterns 0 mismatch; yosys SAT CEX running intel1 lecc_pofix2/sat.log (satcex.sh). lecs_ncmd10 dprove running (moot after drop).
- COORD 23:0x UNDRIVEN task: f16_auth is a plan bus in C1d (template kit lacks it); f16_obs[38]/init_u0[1] have no producer anywhere (die_r56, sys_face). Spec: f16_obs = F16WTN obs {16x{v,user2,slice4,pc9}, stage6, epoch16}; init_u0 = static admission INIT selector aligned to DH stage0 (dh comes from sys_face seq_dh). Needs a sys_face producer + plan buses (QC-ALLFIX after C1e).
- Fork for scoped bind: epyc11 /srv/opentallas-scratch2/claude/QC-TTC-R2/cB/tree (from QC-ALLFIX cE, C1d); scripts bind_r2.sh/bindrun_r2.sh + allfix_in/ (c1d.json, ov_tools, rr). tool/stage.sh reproduces 6a5f53 staging.
Next: class (b) fix (fanout split / dup of u_11072,u_2367 cones + cluster), LEC CEX, rebuild probe template from C1d kit_rtl (f16_auth bound), undriven producer.

## 11-24 00:28 PST update
- LEC CLOSED: differing output was d__u_12820 (X arm of mux u_76013); X arm refined to 0 -> UNSAT for pofix3 22cab1f23f17 and rep5 34d8867fe0b2 vs F5 1166f7d9630f; neg control SAT. Tools intel1 /srv/opentallas-scratch2/claude/QC-TTC-R2/tool: lec_comb.sh, lec_comb_model.py, cexo.sh+cexaig.py (name differing ports), evalout.py (strict), fix_dd.py, replicate.py. The positional ABC cec is invalid (PI order differs).
- Combined form = rep/core_rep5.sv (intel1), cores/core_rep5.sv (epyc11). p_rep was built from a broken replica (withdrawn).
- Hold: u_rrl_78->79 / u_srl_141->142 = same-site relays on two taps (cap pass). tap_relay_cohort.tcl (opt-in clock.tap_relay_cohort), lane clone epyc11 /srv/opentallas-scratch2/claude/QC-TTC-R2/wt commit 7431b0710c (NOT pushed; push after p_rep5 census confirms). Armed in p_rep5/kit (6 clock pins moved).
- RUNNING: p_rep5 CTS on epyc11 -> tool/census.sh -> tool/grt.sh p_rep5 -> census2.sh.
- f16_obs/init_u0 producer: QC-F16-PRODUCER (findings posted).

## 11-24 01:12 PST update
- FABLE 00:10 conditions: (1) X arm of u_76013 resolved to 0 = recorded choice; sign-off LEC must compare routed netlist vs the resynth form (22cab1f23f17 / chosen rep form), not F5 with free X. (2) synth log rep5: 0 multi-driver, 0 loops; no-driver only f16_auth 83 + init_u0 (old template).
- p_rep5 CTS: -121.23/-12.4k, sibling u_11071 now worst (258 ep). Group forms rep7 1c26b8af0f76 (k6 L6), rep8 53f6f842dc78 (k8 L4), rep9 42183e9af233 (k4 L8): LEC UNSAT all three; probes epyc11 p_rep7/8/9 (template tmpl_r2 = tmplf5 + relay cohort). FABLE: read rep7 first, no more launches before.
- p_rep5 GRT: tool/grt.sh needs OT_VCLK_CORNER=ff CORNER=BC (fixed), relaunched p_rep5_grt2.ot.
- u_hr hold at CTS: 768 w_mask_in pins of one SRAM (48 mask flops) worst -52, pre-repair.

## 11-24 03:02 PST update
- rep10 4ae91bf1084d (whole word k6 L6 + group B k3) = class (b) CLOSED at CTS (-85.44 only ROM->u_16867; native_cmd -39.53). rep11 bc7159c2b399 = rep10 + depth resynth of u_16867 exclusive cone (tool/conesyn.py). All LEC UNSAT.
- GRT: rep5 hold +2.21, rep9 hold +4.56 (0 viol). rep9 GRT setup -87.49: native_cmd -66.33 (u_90571, 580 um wire to west pins), group B -38, ROM -87.
- ROM lead form: tmpl_rl (core_latency.txt rows u_rom/u_rom1/u_rom2 = 150 ps). Slack into ROMs +193..214, out hold +484..525 at CTS (rep10).
- native_cmd region: tmpl_rlr = tmpl_rl + place_regions_data.tcl (116 source flops, list intel1 ncmd_src.txt, near u_bout_native_cmd).
- All on intel1 /srv/opentallas-scratch2/claude/QC-TTC-R2 (template copy ep11/, tool1/after.sh + after_grt.sh waiters write census_<p>.done / grt_<p>.done): p_rep11, p_rl10, p_rl11, p_rlr10 at CTS; p_rep10 GRT running. epyc11 full at times (ruling a1acc308: no jobs at load >= 80).
- Registered read (3): u_16867 Q feeds addr/ce of the 3 ROMs (loop) + 84 flops: needs RTL/sequencer change + token bench; fallback only.
- tap_relay_cohort landed main e74113c83a93.

## 11-24 03:37 PST TT-XPF transport (COORD top priority)
- Measured C1g cF/latcheck.json: tt_ctlm.hr->sl_W5_fw.hr_wi = 10 -> XPF 11 (1+R_HR). Program T=20 from lane_ages_dv2f14bi R_HR 19; core 21 from HR_SOURCE_CONTRACT (never measured). All 4 program lane ages stale: C1g cmd 14 / hr 10 / ss 10 / ag 13 / st 10 (program 19/19/17/17). Posted 34faf14b: recompile with --lane-ages, core at 11 + new digest. Core regen owner pending COORD (F16-PRODUCER or CODEX-TOKEN).
- Then: re-run scripted row set on new core names + comb LEC, CTS, GRT. All tt_ctlm timing rows on 6a5f53239424 non-final. Early-tap probes HELD (p_rep11/p_rl10/p_rl11/p_rlr10/p_rep10 GRT left running <3 h). rep12 (tool/portrep.py, native_cmd port replica) build timed out, not launched.
- Caveat to verify: LATCHECK delivered vs ctlm_image lane-age convention (old compiled_L1 relay table says hr 26 stages vs lane_ages 19).
