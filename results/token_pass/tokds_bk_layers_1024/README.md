# DeepSeek S81 layer control verdicts with the BK addressed-drain sink candidate (TOK-DS, 2026-10-24)

Vehicle: fc31 `cut_3S_ctl` (HOST/control cut: u_seqhost, G-unit, BK, column-4 slices) rebuilt with the opt-in BK drain sink
(Codex candidate `codex/s81-integrate-1024` 51ae2e4cef; `ot_dsdv_vstop.sv` sha 5ef19b8b = that commit; the kit's `dsdv_bk_g.sv`
(3fc47cc3) hard-sets `BK_DRAIN_SINK(1)` on the cut's one BK, `.uid 8'h5B`). Build: Verilator 5.050 `--binary -j16`,
epyc3 `/srv/opentallas-scratch/claude/codex-s81/bk_drain_layer` (started by Codex, collected by TOK-DS; build rc 0).
Idle 2000 cycles: 0 faults. Programmes: main compiler on tree_fc31, split into the native job0 + job1 by
`prepare_split_control.py` (main, 49f7915d5a); replay `run_entry_replay.py` (strict dv_cut_replay check + bit-exact CTL line
faces + bench fault count) with KS 3093 (L0 3089). Mutant: job1 `corrupt:hf_7N_l0:33` (calendar-length bit) on the same binary.

| layer | job0 cycles / checks | job1 cycles / checks | faults | line W/E | mutant | verdict |
|---|---|---|---|---|---|---|
| L0 | 13,541 / 849, 0 mism | 3,332 / 41, 0 mism | 0 | PASS/PASS | CAUGHT (10 mism) | PASS_CUT_COMPONENT (no regression from the sink) |
| L2 | 24,703 / 847, 0 mism | 3,336 / 41, 0 mism | 0 | PASS/PASS | CAUGHT (10) | PASS_CUT_COMPONENT (candidate) |
| L14 | 24,734 / 847, 0 mism | 5,217 / 73, 0 mism | 0 | PASS/PASS | CAUGHT (18) | PASS_CUT_COMPONENT (candidate) |
| L20 | 27,571 / 847, 0 mism | 3,336 / 41, 0 mism | 0 | PASS/PASS | CAUGHT (10) | PASS_CUT_COMPONENT (candidate) |

L2/L14/L20 use `--bk-drain-sink 5b` (dv_cut_replay/run_entry_replay, opt-in, c9c5cc8540): the compiler still schedules
the addressed drain `bk.attn.idx.topk_final.drain` (payload186 0xa515b = BK uid 0x5B, op 1) as a slice CTL beat (vi + both
line directions); on a sink build the BK stop consumes it, so those events are dropped from the expectation (recorded in
each json `bk_drain_sink.consumed_events`). Without the flag the same build fails ONLY on that beat (2 mismatches per job,
0 faults; `*_legacyexp_FAIL.json`, kept). On the canonical build (sink OFF) job1 faults 122 cycles (slice SID8 decodes the
forwarded drain as target 10), Codex 11:24.

Scope: control path of the layer on the HOST cut only (no arithmetic, no data-cut exactness, no full layer/stage/token).
NOT canonical: adoption needs (1) the BK_DRAIN_SINK profile/bind in the die, (2) the compiler not emitting addressed drains
as slice CTL, (3) the legacy BK bench expectation (transparent forwarding) retired -> lane S81 / OWNER?.
Cycle columns are replay windows (bench cycles incl. host boot), not stage latencies.
