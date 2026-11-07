# QC native reduction to station join

Candidate source composition: `codex/qc-vr4-compose-1107@98752db40fa`.
Captured binding: E2 `codex-watch-qc-1107/bind_strict`, native `qfd_die`.
This report changes no RTL, compiler calendar, count strap, START, or POR.

The actual 48 bound `rsn`/`rsf` lane records in `crossings.json` all originate
at a C16 `u_t_0_0.n_y`. For example, station `sl_E1_st_a.rs_s0` comes from
`c16_E1_1.u_t_0_0.n_y`; `rs_s1` comes from `c16_E1_0.u_t_0_0.n_y`.
The latter crosses the native forwarding path; its transfer latency delta
is zero, but its upstream root computation still acquires the candidate +9.
Applying the candidate uniformly therefore shifts both station inputs +9.
It does not create a nine-cycle relative mismatch at this pair.

The composition ledger independently identifies the accumulated root delta:
`t_out_0_1(+1) -> n_y_0_1(+3) -> n_y_1_1(+5) -> n_y_2_2(+7)
-> n_y_0_0(+9)`. The unchanged post-root fabric does not add another +9.
At 833 ps, the resulting completion shift is 7.497 ns per affected
dependency boundary. A full token price must use the actual dependency DAG;
this is not a nine-cycle charge per record or an inferred whole-token count.

The exact current `sle_st_a_v2` wrapper is `qfd_qc_sle_st_a.sv`:
`rs_s0 -> ot_dp_clk_landing_cas(W515,DEPTH4,WFALL1,WREG1,DSREP1)
-> u_bin_rs_s0 -> u_lpad_rs_s0(D2) -> qfd_dv_s8_frs`.
The source has a single `u_bout_y_o00` register. The FRS source in
`rtl/qwen_dv/s5/s8/qfd_dv_s8_kept.sv` is only combinational slicing: it
splits the two 514-bit payloads into eight paired 64-bit words and two
control pairs. It adds no cycle or arithmetic. Thus uniform +9 requires
no additional local pair adapter at this interface, subject to the
upstream candidate's valid/fault and R8 alignment premises.

The six-bit CA straps for this station are K23 on both `rs_s0` and `rs_s1`.
They describe the clock/START transport window. A computation completion
shift does not change the physical clock/START relation, so there is no
basis here to change K or START. Existing receiver windows remain required.

The difference between bound and native stages is not a freely removable
delay pad. Across 24 `rsn` lanes it ranges from 8 to 16; nine have only 8.
Across 24 `rsf` lanes it ranges from 4 to 14; twelve have only 4 or 5.
Even the E1 `rsn` surplus of 15 includes physical transport and the landing
mechanism above. Subtracting nine from all plan stage counts is unsupported.

Required downstream integration: preserve all 48 physical stage counts and
their CA/START contracts; move each affected root-result availability by
nine edges, and move its dependent station/command completion by nine edges
unless the actual released scheduler shows measured existing slack.
No concrete production compiler calendar API was identified in this bounded
source trace, so no invented calendar was edited. The earlier +9 composition
witness remains the functional candidate evidence; this is the real consumer
source join and an explicit update obligation, not a repeated token proof.
