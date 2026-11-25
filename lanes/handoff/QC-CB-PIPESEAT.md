# QC-CB-PIPESEAT handoff (row CB-PIPESEAT-SPREAD, QC cb family)
- C1k plan = C1j 7fbc73d3f7cf (the carries are RTL only). The row touches relay_sites pipe keys (u_d<D>_*) only, which keeps it disjoint from CB-TAPBINS (clock.sink_bins_file + retap) and from CB-COREPHASE (clock keys).
- Tool: main d3725d6b7b tools/die_plan/pipe_seat_spread.py (+ test). Row run: intel1 and epyc11 /srv/opentallas-scratch2/claude/QC-CB-PIPESEAT/c1j_r2/<type>/pipeseat_sites.json (17 types), report.json. Default args.
- Verify: scratchpad verify.py: 0 hops worse than max(405, legalised old); hops >405: 2809 -> 2743.
- Gate: epyc11 QC-CB-PIPESEAT/tree (fork of epyc7 QC-ALLFIX/cK/tree). gate.sh (apply_row -> PRE -> scoped elab + strict bind --types cb*), run_gate.sh under ot-run, log gate.log, pre.log, bind/.
- C1k base PRE: FAIL ROWS-NO-PROOF only (epyc7 cK/pre.log).
- TODO: on gate PASS, post ROW-REBASED to QC-ALLFIX + COORD. When the CB-TAPBINS plan sha arrives, re-apply apply_row.py on it (disjoint fields) and re-run PRE.
## 15:59 PST ROW-REBASED posted
- Row plan 002c58551eec (C1k + row): PRE 0 new; scoped strict bind of the 17 cb types: rc 0, 0 errors (epyc11 QC-CB-PIPESEAT/bind, gate.log).
- QC-CB-C1L composes C1l = C1k + PIPESEAT + CB-TAPBINS + CB-COREPHASE. When it asks, apply with apply_row.py on the TAPBINS plan.
- Residual (not this row): 2743 pre-existing >405 pipe hops; 457 cl622 seats inside u_t01 on reach-bound crossing stages -> those pipes need stages or a re-solved line (type_relay_sites --pipes on current core boxes).
- Fork epyc11 QC-CB-PIPESEAT/tree (58 GB): keep until C1l binds, then ot-delete.
## 19:47 PST CB-PIPEREACH ROW-REBASED posted (also covers COORD 17:2x north-strip ruling)
- Tool: epyc11 QC-CB-PIPESEAT/pipe_reach_seat.py (not on main yet). Pipe ends come from the bound topology (topo.json: core pin via the pins file + orient; xstn at the core tap face; u_pc_nk -> sink core n_a/n_b pin). Kit segments come from kit_dly_lockup (kitseg.json). Stages sit at even arc length on the BFS street route, bits on a grid; horizontal streets spread up to 0.9 x hop spacing.
- Row: epyc11 QC-CB-PIPESEAT/reach_r2/<type>/pipereach_sites.json, apply with apply_reach.py on 002c58551eec -> plan 0f77be78cc8d; tarball reach_r2.tgz 9ac4b9b73c75.
- Result: hops >405: 2743 -> 0 (worst 379.9); buried 0; dup 0; +70k seats for pipes that never had seats; north strip 7-11 columns, max 30 per 10 um cell. Bucket (b) empty: no stages, LATCHECK, LEC or tok/s change.
- Gate: PRE 0 new; scoped strict bind rc 0, 0 errors, EMIT 17/17 (gate_reach.log, bind_reach2.log).
- Next: when QC-CB-C1L asks, re-apply on the TAPBINS/C1m plan. Land pipe_reach_seat.py on main. ot-delete the fork after C1m binds.
