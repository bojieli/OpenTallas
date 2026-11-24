# QC-CB-SPREAD-R2 handoff (lane memory)
Job: track the 13 cb types of C1j 7fbc73d3f7cf (QC-ALLFIX bind, intel1 cJ unit oth-ubuntu-17244-1795533571, dir /srv/opentallas-scratch2/claude/QC-ALLFIX/cJ) from bind to sign-off; fix structurally any cb type failing on spread or reach.
cb types (rows_j/compose_0726/types.txt): cbn_q01 x3 (cldd6ea846 cld9ff4c40 clab6e67f2), cbn_q00 x3 (cld7bf7197 cldbcda913 cl622f65d2), cbf_q00 x2 (cl870de686 cl1b5a6458), cbx_q10 x3 (cl89936551 cl89936551_h cl94a12200_h), cbn_q11 x2 (cl49ae4555 cl5cc92dfe).
C1j carries ROW A only (u_d pipe relay_sites from rows_j/cb_pipe_0648/<type>/scoped_sites.json). ROW B (lpad na/nb off-pin) NOT in C1j.
Known: C1h-era cbn_q00__cld7bf7197 GRT overflow 27,441 from unseated pipes + u_lpad_na_i00 at pin (FABLE-RC-QC 05:43).
State 07:55 PST: waiting on C1j bind (PRE).
08:50 findings:
- C1j PRE: cb all WARN only. ADV-ROUTE-DEMAND: west strip x30-60 y1160-2250 (na/nb face flop>u_t00) on cbf_q00 x2, cbn_q00 x3, cbn_q11 x2; ft rsf over cores on cbn_q01 x3 + cld7bf7197; cbx_q10 east edge small.
- nb row in plan still at x43.2 but u_lpad_nb seats already run central channel x500-700 + street y~1200 (estimator stale for nb). na lpad seats x13-88 y1390-2230 (in strip).
- Unseated in plan: strap_u_r8b 110k, u_pc_nk 75k, pad_u_pd 16k. Kit hook core_input_chain.tcl (rt tools/die_plan) places u_d/u_lpad/u_r8b_strap/u_pd non-FIRM stages ON street centre lines (nc_route via nc_xs/nc_ys midpoints, no per-bit offset) -> all bits of a 514-bit chain share one x. Candidate flow fix: per-bit lateral offset across street width.
- C1h GRT cld7bf7197 top nets: pq_/lk_u_t_0_0_n_a = u_pc_nk out / lockup into u_t00 n_a pins (pin face), lpad_na (seated, in strip).
- Candidate plan fix: move na lpad seats + station row to central channel + street like nb (no growth). Decide on C1j GRT congestion by location/net.
