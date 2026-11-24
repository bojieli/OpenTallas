# S81-IQF-RELAY handoff (Opus 5.5; started 11-24 08:2x PST). Narrow lane: row IQF-SEQH-RELAYSITE (iqf__t1, seqhost__t1) -> S81-ALLFIX-INT.
Brief: localhost scratchpad resume_1124b.txt + s81_open_brief.txt (+ rules/split/allfix briefs). Lane dir E9 /srv/opentallas-scratch2/claude/s81-iqf-relay.
## Findings (J8 18a2688b741 placed geoms, c9 048fa468f0a2 plan)
- iqf J8 relay_collapse 240 = ring-fed u_bin_idx_i0 q dragged 390 um into core (1029,701). c9 already has relay_sites u_bin_idx_i0/ql_i0 (1028 keys), 5 internal station chains (worst hop 332, no macros), landing_writer_start flt_o0/idx_o0 chains (fixes J8 cland_origin->fstart_flt_o0 1384 um / -110 REACH). -> iqf IN-BASE (c8 == c9 for iqf).
- seqhost J8 relay_collapse 19 = core l3->l4->u_bout_xtier_o1 (c9 xtier_o1 stations cover it). Ring-fed u_bin_unit_i2 q[*] at x 700-773, u_bin_vid_i0/q at x 685 (eq at face). c9 internal_stations: 3 seats INSIDE hard macros (unit_i2[2] in u_mem0, xtier_o0[3] + unit_o7[2] in u_m).
## Row IQF-SEQH-RELAYSITE (seqhost__t1 only, 0 cycles, counts unchanged)
- ops E9 s81-iqf-relay/row_ops.json (sha 3fd787f180a8; builder build_row.py, report row_report.json): 4 chains re-seated off macros (halo 8.64 + 5), worst hop 291.5; relay_sites add u_bin_unit_i2 (14 keys) + u_bin_vid_i0 (2 keys, 1-bit key ".../q") at ring band centre.
- plan c9+row E9 s81-iqf-relay/plan_c9_relaysite.json afa2391634ad. c8 seqhost/iqf == c9 (ops apply to c8 too).
- render: E9 s81-iqf-relay/seqhost_row.png
- gate: E9 s81-iqf-relay/gate_row.sh (unit oth-ubuntu-771484-1795538396): PRE base vs row + scoped strict bind iqf,seqhost (amd1_tree, rt 69de849b3da1, c8 elab reused, asbuilt_run_allfix2). Logs gate/.
## Next
- On gate result: post ROW-REBASED to S81-ALLFIX-INT.
- Kits: c8 GO (INT, after c8 strict ~11:00) launches iqf/seqhost on c8 form = current-form probes; adopt (iqf = IN-BASE representative). seqhost private rep with row: c8seal_tree + plan c8+row + c8 bind (try without --allow-bind-stale; fallback type_overlay regs_um only).
## 11:1x PST result
- Gate unit oth-ubuntu-771484-1795538396 done. PRE c9 base vs c9+row: both FAIL findings=52 (ANCHORDRY/GENDRY/SCHEMA), identical sets; none name iqf/seqhost. Scoped strict EMIT 2/2, 0 errors on both types (1049 die-wide crossing errors = c8 svc class). Logs E9 s81-iqf-relay/gate/.
- ROW-REBASED posted to S81-ALLFIX-INT (11:1x).
- OPEN: (a) c8 GO kits for iqf__t1/seqhost__t1 (INT, after c8 bind ends) = adopted current-form probes; read their place/GRT/route. (b) private seqhost rep: run intel2 ~/tmp/s81-iqf-relay/launch_seqhost_row.sh once c8seal_tree has the sealed c8 bind (INT post "c8 SEALED"/GO); if BIND_STALE, fall back to type_overlay regs_um only (relay_sites not overlay-able) or wait for the c9 suffix bind with the row.
## 11:3x PST kits blocked
- c8 GO held (c8_post failed: ot-run --priority plan w/o --plan-job; launch_c8 --rt 6d967ec98ec6 mismatches bind rt 69de849b3da1). iqf/seqhost not launched.
- My reps REFUSED KIT_TOPOLOGY_BIND_STALE: bind OUTs (allfix_c8_out, my bind_out) lack native_topology.json; bind writes it only when no in-scope errors; untyped svc crossing errors (UNDRIVEN_OPEN 848, TIED 200, TIED_TOTAL 1) block it even for a 2-type probe. Posted to INT/COORD/BIND-ALL-ERRORS.
- Launch when a receipt exists: intel2 ~/tmp/s81-iqf-relay/launch_rep.sh iqf__t1 <c8|c9 plan> <bind_out> TAG ; seqhost__t1 with plan incl. row (re-run my scoped bind: E9 s81-iqf-relay/gate_row.sh, needs a fresh bind_out dir).
