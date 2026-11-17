S81 next-event START/reset source diagnosis, 2026-11-17

Current D5c is unaffected: no landing_raw_branches rows were added and its source is frozen during S5g bind.

The corrected t47 CTS failure u_rrl_235 -> u_cland_fstart_ft4_o (153 ends, -1538ps, 2880um) matches the existing optional qc_raw_branches_gen.py mechanism: copy an existing raw reset chain at the same depth toward each FSTART sink. It would add state, zero release cycles, if exact phase is preserved.

The unmodified generator fails closed on actual C3 t47: no sited ancestor of rst_n_t20. Actual immutable C3 RTL has u_rrl_235 ot_dp_rrelay, depth7, source rst_rl_234, site(1425.6,17.3). Its predecessor u_rrl_234 is ot_dp_rrelay_nl, depth6, site(1429.3,384.3). The generator indexes only plain ot_dp_rrelay.

Do not merely extend that parser. landing_raw_branches.py driver_index accepts both ot_dp_rrelay and ot_dp_rrelay_nl, but its constructor emits ot_dp_rrelay for every copy, and validate checks clk/D/Q connectivity without module kind. gen_rtl.py defines ot_dp_rrelay_nl as posedge state<=d followed by negedge q<=state (two FF, two phases); it is not a latch or equivalent to one posedge FF. A correct next-event implementation must preserve the original relay module and state count, or explicitly reject the mixed chain. It needs a minimal mixed-phase reset component proof before adding rows. No physical job was launched for this diagnostic.

Read-only input RTL: epyc10 /srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s5f/out/rtl/s81p_ot_s81sl_leaf__t47.sv. Diagnostic copies only in rows/f2s5_S81-DIE-R/start_raw_source_analysis1117. Existing wrapper names do not match the generator's filename matcher; diagnostic copies retain byte-identical contents under type filenames.

The independent t75 START long-reach class still needs explicit origin/reader path rows; the raw FSTART branch mechanism alone does not prove or fix that class.
