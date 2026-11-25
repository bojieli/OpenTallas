# QC-SUL1-SLW-REFLOOR handoff (lane memory). Parent QC-ALLFIX. OT_LANE=QC-SUL1-SLW-REFLOOR.
Types: slw_su_l1__cla2a78701 (5 insts), slw_su_l1__clcc9d0155 (1). Work dirs: epyc10 + epyc12 /srv/opentallas-scratch2/claude/QC-SUL1-SLW-REFLOOR.
## Census (posted 07:3x, coord e0a0f02c)
- clcc 1124052823 epyc8 R6V4 DRT it19 274k->8519 (it17)->40739->16569; cla2a 1124082633 epyc7 DRT it6 ~38-40k flat; cla2a 1124145701 epyc7 at GRT; all cancelled by QC-OLDKIT-CANCEL (Q7).
- Cause: STATION-PILE. clcc 5_route_drc.rpt-15 8666 viol, 93% x475-525 y200-300 (u_ist_x_su_c_i__u_lane4_u_lane5, u_lpad_x_su_c_i). Kit per-bit L routes (normal_first lane4+5 696b, along_first lane6 571b / lane7 503b) start at cl_x_su_c_i W face x527 y188-278 -> one column each.
## Row SUL1-SLW-CHAN (C1p), base C1o v13 aa3a14fb7484 -> ec946f9fcca2
- script epyc10 .../sul1_slw_refloor.py; leg_order channel (KIT-CHAN-1): lane4+5 [440,520], lane6 [440,463], lane7 [487,522]; regs re-centred; stations/cycles same.
- job.sh (ot-run epyc10 unit oth-ubuntu-3277614-1795621859): IDEMPOTENT, only internal_stations of 2 types, GEOM 0 errors, guard PASS 0 silent, SIDECAR PASS; PRE by path on launch_c1o_bind (baseline r3 + v13 drops) running.
- Estimator: peak 12.22 -> 9.11; residual = pin-row box artifact (sensitivity 6.17) + street 1.45 (needs x growth ~+86 um = die-level; DEFERRED).
- Fable review spawned 08:0x. Next: after BIND-PASS C1o v13 -> private copy of launch_c1o_bind, install row plan, scoped strict bind, place->GRT probe.
