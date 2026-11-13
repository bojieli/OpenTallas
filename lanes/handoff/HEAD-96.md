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
- 17:1x COORD scope cut: post rp18 once approved content passes; lep0N rst_n fix / single type may go to open list; only functional lane/reset mismatch blocks.
- lep0N rst_n: centre pin is in the SIGNED core view (vE_1106 LEF, core-local 388.8,246.2); a fix = core re-pin rebuild. Script head-96/lep_rst_edge.py (S face M5 x 397.464 -> push-off 34.6 um) -> rp18f/rp18g. DROPPED from rp18 (open item).
- Found: column re-solve renumbered hd_spn/hd_spn_end/hd_tile/hd_turn_a relays; landing_reader/writer_start stage raw_reset stale -> gen rc 1 on all types. Fix script head-96/remap_start.py (physical identity, else same depth offset nearest) -> pd/rp18i.json (= rp18e + remap). Gates: head-96/gates.sh rp18i -> g_rp18i/ ; baseline g_rp17/ ; cmp.py.
- rawfix2.py (existing_port raw exports follow the out on the pin, else private raw export, same role + depth offset) -> pd/rp18j.json sha 1f167af2038687ac = rp18 PLAN OF RECORD.
- Gates rp18j (g_rp18j/): gen rc 0 26/26; G0 1 ERR (native PENDING) 0 NEW; G0C 0 NEW ERR, 5 NEW WARN geom_clock_reach; reset 0 NEW, max release 109; street = rp17; reach errors 0.
- GEOM verdict posted (GEOM-REVIEW.md, renders lanes/head-96-rp18/). READY + PLAN EVENT posted (COORD-REVIEW-QUEUE.md), branch claude/head-96-rp18-1112@7bf527a804 (plan_of_record/head_rp18_1112).
- LATCHECK: HEAD has no bind.py elaboration/as-built manifest -> CLI not runnable, UNMEASURED (structural argument in the post). Open list in the post (a-f).
- DONE. HEAD-96 stopped. Worktree epyc4 wt/head-96 kept for the merge; work dir head-96/ (has tmp gen dirs removed).

## 20:3x fix job (COORD): rp18 reset-export defects found by KIT-OPS-1
- (1) 5 private export rows without landing pin (my rawfix2 conversions), (2) 2 duplicate relay pairs (HEAD-95 rawfix nearest rule collapsed twin relays).
- One-class tool tools/s81_head/head_reset_exports.py (fix OLD IN OUT / check PLAN) on branch claude/head-96-rp18fix-1112 (wt/head-96, off main b9c049d416).
- rp18k = fix(rp17, rp18j): check 8 bad -> 0; kit_rtl head_start_raw_private.prepare_plan failures 2 -> 0. Gates head-96/g_rp18k.
