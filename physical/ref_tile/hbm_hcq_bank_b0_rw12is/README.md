# b0_rw12is

HBMb/HC-BANK 10-21 b0_rw12is = b0_rw11is (island spine + clock_rc_cal_measure) + PD-AUDIT 4b: hard placement blockage over every SRAM-SRAM sliver channel < 21.6 um (abutted g_w pairs = one stack with halo; physical/ref_tile/hbm_hcq_bank_pda/macro_stack_blockage.tcl). PD-AUDIT 4a/4c: clock entries stay IO-placed (measured at their consumer faces; W/E/S faces are fully allocated to die-contract buses), g_lg leaves unchanged (<=100 um to both w and x banks infeasible in the die-contract outline with R0-only children). Parallel to live b0_rw11is. Same outline/children/pins/roots/RTL/edges; 0 cycles.

SAFE8: lanes/HBMb-HC.md HC-BANK.
