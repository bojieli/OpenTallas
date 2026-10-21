# CTL c32c terminal gate 10-21

Original exact staged source gate ot-epyc9:/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_ctl_c32c-20261021-053438. Gate FAIL, retained unchanged. Local gate client completed 09:00; execution.log GATE_SCRIPT_RC=0/GATE_DONE. Trial GRT itself GATE_GRT_RC=2.

Initial route overflow 0, worst layer M2 25.56%; failure occurs during incremental post-GRT hold repair, after iteration 740: [ERROR GRT-0183] Net net30189: the 3D maze router ran out of legal paths (heap underflow), boxed by local congestion/blockages. SS setup worst -112.79ps/FF hold -30.57ps at repair failure are diagnostics, not a closure verdict. Frozen resume ODB remains remote 5_1_grt.grt183_resume.odb; preserve.

Clock passes guidance: root ck TT/FF pin-flop spread51.2/44.7ps. This failure is not a clock-spread admission issue. Existing taller c32d (345.6x561.6 vs475.2) has initial GRT0 and remains live; 09:42 hold repair step480, real worst+24.57ps, TNS0. Do not duplicate it. If c32d fails, identify boxed net physical endpoints and change pin-face/macros/channel access structurally before a new kit.
