S81-CAPC4 10-20: behavioural evidence for the LANDED capture cluster ot_s81sl_capc5 (source 235089270, branch claude/s81-capc5-land-1020).
Fleet ot-epyc9, Verilator 5.050 (verilator.version), unpinned ot-run, source archive /srv/opentallas-scratch/claude/s81-capc4-1020/src_2350.
gold_pass.out  cap_c5_gold_bench.sh MUT=0: golden cap_model vectors (s_16_24 calendar), 1280/1280 rows written at W+5 exactly once, 7446/7446 lane
               arrivals at A+1, fault 0 -> PASS.  (capc2 contract was W+2: +3 = the three landed crossings into u_rt.)
gold_mut1.out  lp MUT 1 (W-valid landing bypassed) -> CAP_C5_MUTANT_DETECTED (missing writes).
gold_mut2.out  lp MUT 2 (W-valid landing read K+1) -> CAP_C5_MUTANT_DETECTED.
gold_mut4.out  lp MUT 4 (u_rt reset run +64 stages) -> CAP_C5_MUTANT_DETECTED (960/1280, fault).
lp_bench.out   lp.py lockstep landed vs flat ot_s81sl_capc5f MUT0 PASS 3000 cycles + region audit PASS + unland-mutant audit FAIL (expected);
               random-stimulus mutants 1/2/4 waived in the lp spec because random words saturate u_rt's sticky decode; they FAIL above.
