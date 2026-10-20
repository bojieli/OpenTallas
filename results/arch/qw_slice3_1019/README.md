# QW-SLICE3 evidence (10-19): slice2 station, 8 regional clock roots + landed fault ring + OT_ASSERT seam
Benches on Verilator 5.050 (ot-epyc6). Source: claude/qw-slice3-1019 @726e7f1ca (tb fixes) / 1bc537f91 (RTL ws_rep D=3+BT_LAT).
- rg5_p0 / rg5_p1 / rg5_p1_oa: tb_station_regional, 8-region station vs R8/R9 monolith, 20,000 edges, two resets, PIN_IN 0/1, OT_ASSERT build: PASS, 0 mismatches.
- rg5_p1_r1 (RMUT1, region 5 takes region 4's bt_q slice): FAIL REGIONAL_STATION_MISMATCH (witness).
- rg5_p1_r2 (RMUT2, fault-ring hop 3->1 cut): FAIL REGIONAL_FAULT_LATE (witness).
- rg5_p1_m3 (MUT3 both sides): PASS (equivalence holds under a shared station mutant).
- dv2b_e / dv2b_w: full slice2 production dv_bench2 a c f g k q m o n e with DV2_STATION_REGIONAL=1 (+SAFE_RESET/AMAX/SCALAR/STATION_CFG/STATION_MATH, NATIVE_SRAM), FACE 2 / 1, MU_NU 4, SU_LT1 HD_W130: all 10 PASS, timings g 183/134/104/64/190, fused 61 (unchanged). Source 969bc27d1 (bench wrapper BT_LAT=0: RTL identical to 1bc537f91 there).
- dv2b_m14 / dv2b_m15: station mutants FAIL 128/512 and 0/512 (witnesses, same as R7).
- gate3_stnrg: qfd_dv_slice2_stnrg (region tile) --cts gate WARN: util 48%, 10,806 sinks, TT/FF pin-flop spread 53.9/52.6 ps, insertion TT 310.8 (guidance), textbook PASS depth 531.8 ps.
- gate1_stn8: flat 8-root leaf FAIL at CTS: "CTS source ck_r0 must reach only standard-cell clock pins" (multiple_cts_roots leaf cannot clock SRAM macros; needs hybrid_entries raw SRAM clock entries).
- gate4_stnrgc: qfd_dv_slice2_stnrgc (region tile, centre clock entry, source adb01f683) --cts gate PASS 0 warn: util 48%, 10,808 sinks, TT/FF insertion 277.5/231.9, pin-flop spread 55.1/53.9 ps, setup WNS +91.9 ps, hold WNS +37.9 ps (pre-route), trial GRT overflow 0 (M2 30.9%).
