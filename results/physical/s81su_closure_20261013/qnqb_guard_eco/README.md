# s81su qnq/qbe: hold-ECO rc=9 root cause and the macro-edge via guard (2026-10-13, [s81su-qnqb])

- `qnq_v2_eco_rc9_abort.txt`: the abort on s81su_qnq_ref-v2-a02a02ee9 (std::vector operator[] assertion in
  grt::GlobalRouter::removeWireUsage). Cause: the v2 routes (kit a02a02ee9, older than dc5594311) hold real M6 signal
  wire under the M5 cap (QNQ 280 segments, 6_final.def 263 NEW M6 + 18 ROUTED M6; QBE 366 + 35); the ECO's GRT is M2-M5.
  The v2 "DRC 0" routes violate the layer cap and are not ECO candidates. main ad611ad21 refuses them with a reason.
- `qnq_spx_v4_hand_eco_*`: HAND RUN, not a loop record and not a close. The shared hold ECO (main ad611ad21) with the
  macro-edge via guard on a private copy of s81su_qnq_spx_ref-v4-spx-1ec43dde7 5_2_route.odb (route: TT +97.9 /
  FF -5.17 / DRC 2), KEEPWIRES=0: TT +105.14 / FF +23.01 / DRC 0, 2,169 hold cells (real delay cells; local hold patch
  on an otherwise sound route). ot-epyc1tb:/srv/opentallas/claude/s81su-qnqb/qnq_spx_eco1.
- Loop successors with the guard in the route itself: s81su_{qnq,qbe}_{spx,sp8}_ref-v5-{spx,sp8}-2df2353b8.
