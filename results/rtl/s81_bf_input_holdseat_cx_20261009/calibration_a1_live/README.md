# H7 calibration attempt 1 live diagnostic

This is a bounded snapshot of an advancing job, NOT a terminal failure or
physical verdict. Original job and all objects remain live and untouched.
Source c674dadfd, actual driver2372561/OpenROAD3612910, EPYC1 run
/srv/opentallas-scratch/claude/closure-loop/bfk_recut_hs4_sm15-c674dadfd-tc-cx.

Driver sets OT_CAL_CTS_ONLY=1, which skips CTS repair only. Calibration
intentionally does not source calib.env before measuring insertion. The
native route wrapper therefore uses fallback CK_SS_MEAN1042 and passes
--ins-ss1042/--ins-ff1042. Actual generated1_synth.sdc has core clock730ps,
input min1042/max1292ps, setup uncertainty60ps and hold uncertainty25ps.
The preCTS setup objective is infeasible with an ideal zero-insertion clock:
even zero data delay misses by622ps before library setup. Real four-HB2
cells add delay; actual floorplan endpoint cfg_v misses757.305ps. Snapshot
iterations563–578 show zero moves and unchanged TNS/WNS, while CPU advances.

This classifies provisional preCTS reference pressure, not candidate routed
setup or hold. It does not prove the flow cannot eventually terminate and
reach CTS despite negative preCTS slack; the same predecessor also began
from this provisional seed. Preserve the advancing process, no settings
change or duplicate retry. If it terminates before insertion is measured,
collect the full immutable cause and propose configuration-only calibration
reference correction; the real route must still use fresh measured TT/FF
insertion,730ps/833.333ps clocks,60/25ps uncertainty,SM15 setup ECO and the
already-qualified native RTL/exact bench. No relaxed signoff or new RTL.

Binding confirmed review-0400 R7 now authorizes correction immediately,
superseding waiting for the provisional seed attempt to terminate. Exact
calibration seed701.5540326188421ps is the committed actualrouted TT
PINREG arrival_max_rise mean (original6e8f0b698). Registry807ps is from a
newer placement-estimated calibration and is not the selected routed receipt.
Only the calibration command prepends CK_SS_MEAN; route still loads its
own freshly measured TT/FF calib.env. Original1042 spec retained here.
Clock730/833.333ps,60/25ps uncertainty,SM15,RTL/exactbench and resources
stay unchanged. Fleet owns preserved exactattempt retirement and locked
same-job attempt2 requeue. No duplicate route or source change.
The corrected preCTS inputmax951.554ps remains above the idealclock setup
budget: correcting stale reference does not itself qualify preCTS/routed
setup. Actual phase advance and newmeasured closure are required.
