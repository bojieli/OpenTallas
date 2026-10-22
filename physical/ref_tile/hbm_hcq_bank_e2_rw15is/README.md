# E2 e2_rw15is

HBMb/HC 10-21 e2_rw15is (MAIN) successor of e2_rw14is/rw14isb (CTS FAIL clk_d0 pin-flop 93.0/94.1 TT on platform setRC while the island spine balanced d0 to 26.1 on the RCX-calibrated clock RC; rw13isc h1 129.0 vs 26.7 same class). Spine fork=root; spec clock_rc_cal_measure: the in-flow hybrid clock rule measures spine-clocked roots on the same calibrated clock RC the spine balances on and the hold flow times (as main f02b312f0 ck_insertion), placement/GRT only, routed SPEF unchanged. Same outline/children/pins/roots/RTL/edges; 0 cycles.

SAFE8 as rw13is (lanes/HBM-ELEM13.md HC 17:40); 7 clock: island spine + calibrated-RC rule (lanes/STEWARD-HBM.md HBMb/HC 19:2x).
