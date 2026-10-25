# Native one-clock SFU lane gate

PASS: one KIND1 SFU lane129/quarter1, ALAT4 via f12_l4 source override,
MLAT4,LEAF1,PINREG1, six real pinned-store SRAMs. Eight operations x64issues:
EXP,scaledexp,sigmoid,SiLU,swiglu,divide-by-B,divide-by-immediate,bypass.
512outputs and1024golden+actualSRAM checks pass exactly on each operation's
compiled edge. Address,data andphase mutants all fail as required.

The existing independent NumPy SFU fixtures retain full512-lane columns;
the smallest real lane reads its own production-width column. The per-op
latency comes from su_arith_sfu_compile.py at ALAT4/MLAT4, plus the pinreg
four-edge shift. This covers nonlinear arithmetic timing as well as words.
The fixture programme.json retains the measured operation/depth contract.

Run SU_ONECLOCK_PROFILE=sfu tools/hbm_layer_vehicle/su_oneclock_1025/run.sh O.
Run dir intel1:/srv/opentallas-scratch2/claude/codex-hbm-su-oneclock-1025/out_sfu;
unit oth-ubuntu-1312160-1792922617. No physical sign-off or whole-die token claim.
