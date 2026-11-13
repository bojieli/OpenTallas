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
- rp18k had 277 NEW G0 "infrastructure pin used 0 times" (new pins without a reader) -> tool declares them start_tree OPEN -> rp18m.
- rp18m = rp18r1 sha 220334aa9b30ef3d: check 0, prepare_plan 0 failures, gen 26/26, G0 0 NEW, G0C 0 NEW err, reset 0 NEW, street = rp17.
- Branch claude/head-96-rp18fix-1112@eb8a6d68eb pushed; READY posted (asks KIT-OPS-1 to also re-kit wshim_tx + turn_a: 4 rows had wrong depth from rawfix, restored).
- DONE, stopped.

## r2 fix job (COORD, 11-13): reader raw export pair + hd_mesh M1 LEC hints
- (A) KIT-OPS-1: hd_spn rst_start_raw_42 on u_rrl_147 = reader raw export pair rr_t58_reader_raw (bd_i stage 5). Tool r2 (branch claude/head-96-rp18r2-1112 off eb8a6d68eb, wt/head-96): reader_pairs() counts them occupied, check flags. rp18n = fix(rp17, rp18j): only raw_42 -> u_rrl_118/rr_t60 d7. check rp18m 1 bad, rp18n 0.
- (B) COORD: hd_mesh M1 LEC NOT EQ 3318 = stale wdata==a_in hints (RBL0) on an RBL1 kit; proven fix = main l48hp1_mesh_hints/lec_hints_rbl1.json.gz (HEAD-92, a9525b39). head-96/mesh_hints.py -> rp18p (= rp18n + hd_mesh.lec_hints a9525b39, 1106 rows). rp18p = rp18r2 candidate, sha cda1ecf604eb.
- LEC proof: epyc9 docker h96-mesh-m1-lec on a copy of VISLAYOUT3 kit_mesh_m1 (netlist 4490e862 unchanged), dir epyc9 /srv/opentallas-scratch2/claude/head-96/mesh_m1_lec. Started 2026-11-13 00:30.
- hd_host_w spread3 NOT EQ (298) is a DIFFERENT signature (r_ce_in/w_ce_in, cones matched) -> not in r2, open item.
- Gates: head-96/gates.sh rp18p; RTL export replay head-96/rtlx.py (prepare_plan all 26 + gen --trial + alias/private patch per export type).
- 2026-11-13 00:39 READY r2 posted (branch 46bb7dfc34, plan rp18p cda1ecf604eb), verified on origin. Remaining: one-line RESULT when epyc9 h96-mesh-m1-lec reports (lec/lec.json); NOT EQ -> hints as r3. Then stop.
- 2026-11-13 02:00 COORD queued NEXT EVENT (r3/rp19, after M1 LEC RESULT): (a) write_chunk 16 on hd_turn_b, hd_turn_a, hd_st_n4 (approved, 0 cycles); (b) hd_spn_wshim_rx reset reach: u_srl_41 / u_rrl_75 single-load hops on 30-37 fF wire, slew 409-411 ps -> shorten hop (move or add relay; +1 reset cycle pre-approved); (c) build on main once train 34 (CLAND 2-copies-per-chunk) is MERGED. Gates as r2, then READY.
- 2026-11-13 03:32 r3 READY posted: branch claude/head-96-rp19-1113@ef7870e5d1, plan rp19c 9249e31961979aa5 (epyc4 head-96/pd/rp19c.json), worktree epyc4 wt/head-96r3 on main fbfb4fc6a6. Remaining: M1 LEC RESULT (epyc9 h96-mesh-m1-lec).
