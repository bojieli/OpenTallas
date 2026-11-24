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
