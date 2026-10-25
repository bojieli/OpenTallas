# Native one-clock SU arithmetic gate

PASS: ALAT4 with the f12_l4 adder selected by ot_hdc_fastfp_lat_c12.sv,
MLAT4, LEAF1, PINREG1 on one real LIGHT lane (lane205/quarter1), with its
six actual pinned-store SRAM macros. All clocks are the same.

31 arithmetic control classes x64 issues:1984 outputs,3968 golden/actual-SRAM
checks. First output41, issue-to-output29, II1. This is +1 output edge over
the ALAT3/MLAT4 predecessor at first_output40, and the B2 token model receives
the ALAT4 setting. Address, data and phase mutants all FAIL as required.

Runner: tools/hbm_layer_vehicle/su_oneclock_1025/run.sh. The runner derives a
successor of the existing kind0 LAT4-multiply physical wrapper with ALAT4;
it uses the existing independent NumPy golden and native leaf bench.
The full 512-lane fixture is retained, with the one lane's real column used.
No array duplication is needed to test the adder substitution mechanism.
SFU nonlinear functions and whole-native-die token pass are not established
by this arithmetic-lane gate; the source-wide f12 equivalence remains the
separate FP32-lane record. No physical sign-off is claimed.

Original runner finished the base gate then failed on missing rg (exit127).
This was an infrastructure failure after the successful simulation. The
same binary resumed only the three remaining mutants using grep, exit0:
intel1:/srv/opentallas-scratch2/claude/codex-hbm-su-oneclock-1025/out
unit oth-ubuntu-1167299-1792922069.
