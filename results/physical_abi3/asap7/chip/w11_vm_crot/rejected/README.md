# Rejected C_rotate hardening attempts (kept as negative evidence; never overwritten)

All at 1.111 ns, ORFS WC setup, hold WC + BC, 60 / 25 ps (tools/run_abi3_physical.py via harden_crot.sh).

| run | block | layers | result |
|---|---|---|---|
| rot512w4_m5 | ot_v41_vm_rot N=512 W=4 LPS=7, util 20 | M2-M5 | GRT-0116 global-route congestion: M5 REJECTED for the rotate |
| rot512w4_m5u10 | same, util 10 | M2-M5 | GRT-0116 (density does not help: the shifter's long levels need tracks) |
| rot512w4_m6 | same, util 20 | M2-M6 uncapped | GRT-0116 |
| col_k2q4_m5 | ot_v41_vm_group_phys RC=6 NB=2 K=2 WQD=4 RDREG=1 (12 macros), default util | M2-M5 | DPL-0033 detailed placement at CTS (re-run at util 15 / 25) |
| rot512w32 / rot512w32_m5 | N=512 W=32 | - | PPL-0024: 32,768 IO pins do not fit a standalone block; the rotator is bit-slice separable, so it is hardened as W=2 slices |

Adopted: rot512w2_m6c75 (M2-M6 with M6 capped at 75 % of its tracks by physical/abi3/w11_crot_m6cap.tcl, the
condition of W18b's die check claude/w18-die-assembly d59e7f8d), 980.7 MHz SS.
