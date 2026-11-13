# HEAD-96 lane handoff (narrow successor of HEAD-95: build, gate, post HEAD rp18 plan event, then stop)

Started 2026-11-12 16:53 PST. Coordinator: COORD. Brief: rp18 = rp18a (lep0N windows + wshim_tx relay_um 300) + reset.column {} on
the six chain types (no in_sites) + fix hd_lep0N u_pair.rst_n buried core pin (250.6 um) + no outline change + G0/G0C latency/reset rows.
NOT mine: HEAD-95 routes (lep0N v3, hd_mesh M1, SP3n2).

## Paths (epyc4)
- Worktree: /srv/opentallas-scratch2/claude/wt/head-96 (branch claude/head-96-rp18-1112 @ origin/main 14685c8552d3, sparse like head-95-col, + head-93 prep1 links)
- Work dir: /srv/opentallas-scratch2/claude/head-96 (scripts, gate outputs)
- Base: HEAD-95 rp18e = rp18a + column + rawfix (epyc4 head-95/pd/rp18e.json), built with 39e04ecad5 tools (tools/ tree-identical to main 14685c8552d3).

## State
- 16:53 start; rp18e verified: column {} on 6 types, in_sites dropped, G0 1 ERROR (native qual PENDING row) 0 NEW.
