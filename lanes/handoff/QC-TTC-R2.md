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
