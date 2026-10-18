KVJ-A9 (2026-10-17): qkd_host_qm_ingress16_service_debt RP_REPL (opt-in, default 0).
Bench: rtl/test/qwen_host/tb_rpr_lockstep.sv (iverilog -g2012, -Ptb_rpr_lockstep.SEED=<s> -Ptb_rpr_lockstep.ES=<0|1>);
RP_REPL=1 vs RP_REPL=0, 554 output bits compared 4-state every cycle; lockstep.log = 4 seeds x ES{1,0} x 50k cycles, all PASS;
mutant.log = -DQKD_RPR_MUTANT (replica 4 advances by 2) FAIL as required.
Yosys 0.68 synth -flatten: RP_REPL=0 cell stat identical to the pre-change file at ENABLE_SERVICE=1 (26203 cells) and 0 (25966);
RP_REPL=1 (ES=1): 25944 cells, $_DFFE_PN0P_ 14 -> 41 (27 kept replica flops = 9 slices x rp[2:0]).
