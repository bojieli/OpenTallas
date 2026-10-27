# HBM-CORE-LAT-R5 hcroot hcp_sys1 (2026-10-27; COORD RULING HBM-CORE-LAT-R4 (1): reset the command registers in RTL)

RTL: `ot_hdc_v41x_hcp_sys1_static` gains the opt-in parameter `CMD_RST` (default 0 = unchanged for the hc_eng / hc_root_static users).
`CMD_RST=1` puts npos_r nout_r scale_r nrun_r nlast_r nf_r eps_r wbase_r p o r ssph wcur xpos on an async reset (rst_n, value 0).
`ot_hbm_hc_root_hcp_sys1_core` sets `.CMD_RST(1)`.

Root cause (R4 diagnosis, CHECKED from RTL + R3 lec.json): nlast_r and the other command registers had no reset and are loaded from
wrapper-tied cmd fields. Yosys folded them (a legal X refinement) while lec.py saw a free initial state, so the result was NOT EQUIVALENT
7724 proved / 1070 differ / 1772 gold-only. With the reset, the lec.py structural constant closure can prove the tied bits constant from reset.

Kit: intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r5-hcroot/hcp_sys1 (copy of the R4 kit kits_cts/hcp_sys1 without run/, new rtl/;
lec.py = tools/die_plan/lec.py of claude/hbm-core-lat-r4-root-1027 aebda01144 with the dup-name FSM fix).

- Synth + LEC: `run_kit_hbm.sh synth`, ot-run unit oth-ubuntu-697730-1793093921 (intel2, started 02:38 PDT; the R3 LEC of this core took 3756 s).
- After it, `after_synth_r5.sh` (detached on intel2) launches `chain_r5.sh` through ot-run, ONLY if lec/lec.json is EQUIVALENT:
  place -> R3 `run_plan.sh` (same plan tool + fixed choice rule; NEW frozen named membership, because the R4 tree spec names the old
  netlist) -> plan-built CTS + FF hold gate (`cts_r5.sh` = R4 cts_r4.sh) -> `run_kit_hbm.sh route` (GRT BC hold repair -> per-corner
  insertion gate -> DRT -> finish -> abstract -> corners -> signoff) -> routed LEC.
- Progress: chain_r5.status in the kit.

Results: appended below when collected. Every number is UNCHECKED until it is written here.

## Status 2026-10-27 04:02 PDT (fork F1 stops polling here)
- Synth done 02:45 (1_2_yosys.v). LEC still in correspondence refinement at 04:00: hyp20, failed hypotheses 622 (hyp9) -> about 120 (hyp5-8) -> 6.4 kB list (hyp20), converging (UNCHECKED, no verdict yet).
- Remaining failing-hypothesis classes in hyp20 (CHECKED from lec/hyp20_failed.txt): u_div r_mb / r_rem vs gate r_rem#t (array-layout naming, gold-only and gate-only), u_div g_rec[].src_q / q / y, dld[228..328] delay-line bits, g_tail[2..3].u_a.s1_small, one xpos bit. The command-register class (nlast_r / nrun_r / nout_r / scale_r cones) no longer appears.
- To collect: kit lec/lec.json + lec_run.log tail (unit oth-ubuntu-697730-1793093921). If EQUIVALENT, after_synth_r5.sh (intel2 pid 1138617) has started chain_r5.sh through ot-run (chain_r5.otrun.log, chain_r5.status). If NOT EQUIVALENT, the chain is not started (status line "NOT launched"); next step = the u_div r_rem/r_mb correspondence (lec.py naming) and dld/s1_small cones.

## RESULT 2026-10-27 04:13 PDT: synth LEC NOT EQUIVALENT (CHECKED, lec_synth_r5.json)
cp 8530 / proved 7455 / differs 1075 / undecided 0; gold-only live 2036, gate-only 610, gold_constant_flops 0 (R3: 8794/7724/1070).
Chain NOT launched (after_synth_r5.sh: "NOT launched"). CMD_RST alone does not close it. Why (CHECKED from lec_synth_r5.json and the RTL):
1. The reset command registers are still gold-only (nrun_r 170 cones, nout_r 50, scale_r 33). Their bits that are tied 0 hold the value
   (reset 0, D = accept ? 0 : Q), and Yosys folds them to constants legally. The lec.py structural constant closure proposes a constant
   only when the D literal is constant, not for an enable-hold mux, so gold_constant_flops = 0. A reset-based invariant proof
   (Q = 0 at reset and D in {0, Q}) is real equivalence, not an allowance. It is a lec.py capability gap: owner of lec.py.
2. d0[6..13] (no reset, D = const 0 once nlast_r[7:0] = 0) are still "removed although not constant". Resetting d0 as well
   (variant prepared, not built) moves the same problem into the gate-folded d0 -> dld / sd_nv chain, so it only helps after fix 1.
3. Unrelated to the cmd registers: st[] FSM (250 cones, gold-only; st[3] reachable-constant, Yosys FSM re-encode),
   u_div r_mb / r_e / r_rem vs gate r_rem#t / r_e#t (array-layout naming, gold-only + gate-only), g_tail u_a.s1_small (144),
   u_tvv.gd.line (33). These were already in R3 and are lec.py correspondence / FSM issues.
Options: (a) lec.py: reset-invariant constant proof for enable-hold registers + FSM re-encode + #t array naming (LEC owner), then rerun;
(b) RTL owner: pass the static wrapper's tied cmd fields as parameters, so these registers do not exist (removes class 1/2 only).
