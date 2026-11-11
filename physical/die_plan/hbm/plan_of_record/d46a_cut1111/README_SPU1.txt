FTRES-FIX 11-10 addendum (COORD fail_watch q_spu1__physical_v1 GRT-0183 u_bound.u_ft_L40x1_o_4): plan_p11t_taps_cyc 29333b2b19c9
+ ftres rule "cut the die reservation to the measured need" on q_spu1 and q_spu1__physical_v1 (transit-only, no hard cores, so not in
hbm_overcore_97.tsv): NS die band [276.48,786.24] (L2 N->W 2999 b) die_share M5 0.5 / M7 1.0 -> 0.3 / 0.3 (= 2999 b / 18585 M5+M7 tracks at 0.6 use).
Span, layers, ft_slots, stations, windows, clock unchanged. eq_gate.json EQ_BY_CONSTRUCTION (2 paths, die_ft_bands only). G0 639 errors / 1440 warn = base, 0 new.
pin_access.txt: own S/N slot windows inside the band had M7 1.00 blocked (L5101x6 0 free tracks); new <=0.32 (L5091x7 0.62).
Builder mk_plan_spu1.py; record spu1_event.json. Tools: same as 29333b2b. DO_NOT_COUNT until signed off.
