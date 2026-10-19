# TOK.DS.BENCH.3: HOP consumer check (LEAD2-S81/TOK-B3, 10-19)

**Problem.** The cut_7 L0 users 0/1/2 HOP runs (base, tagdrop, wrongcopy, rtl_tagdrop) all reached
`TB_DV_SLICE PASS` with `out_checks=0`. The simulator compared nothing. The epcheck/check pass never ran either:
`chain_ep.sh` ran `cd` into a pruned worktree.

**Fix.**
- `tools/s81_dv/dv_cut_replay.py epcheck`
  - FAILS on zero consumer checks.
  - Treats any expected beat past the run window as a deadline error. Before, such beats were skipped silently.
  - Takes `--scope all|hop`.
  - Takes `--expect-fail` for mutants. Exit 0 only when the consumer comparison catches the mutant (beat, tag or MU
    fault) on a complete run with a nonzero check count.
- New `epx` subcommand: writes the numeric gold from the compiled schedule (replay `ep_expect`), never from a DUT trace.
- `tools/s81_dv/dv_slice_tb.py --ep-check` adds the same check inside the simulator (`+EPX=<gold>`, `+EPSTRICT`):
  - Every gold beat is checked bit-exact on its edge (pair, kind, MU tag [1077:1045]) at the lep ro pin flop.
  - Missing beats, unexpected beats, MU faults (te, land, mcol) and gold beats left past the run all count as
    mismatches.
- Every dv_slice_tb bench now prints `TB_DV_SLICE FAIL zero checks` when it compared nothing.

**Results.** Python consumer check on the landed runs (ep.txt from the probe; witnesses in `witness/`):

| run | scope hop (480 lowered hop beats) | scope all (564 beats) |
|---|---|---|
| out_base | **PASS** 480/480 exact, 480 tagged, MU faults 0 | FAIL: 78 non-hop RD beats missing |
| out_base_tagdrop (mutant) | FAIL, CAUGHT: 240/480 exact (tag 0, want 1) | FAIL |
| out_base_wrongcopy (mu-win-ab:1) | FAIL, CAUGHT: MU fault te at u_s_7S edge 8229 | FAIL |
| out_rtl_tagdrop (RTL mutant) | FAIL, CAUGHT: 0/480 exact | FAIL |
| zero-gold self-test | FAIL: "ZERO consumer checks" | |

**Open finding (scope all).** Each non-hop RD burst at the end slices should give 14 beats per user per side (84
in all). Only the last beat of each burst appears on rov, at edges 1366/1376, 22678/22688 and 43990/44000. Either the
compiler's event model or the lep RTL is wrong; the cause is not yet known. Owner: HOP compiler / lep RTL.

**Also open.** The strict trace `check` finds 3940 unscheduled words on the four `lt_lk_E*` landing lanes (985
each), and `expected_out` is empty. This is the known S81-SIM-PICKUP2 link-observation issue, separate from this bench.

**Fleet re-run** of `fleet_tokb3.sh` with the checking TB (`tb_slice_top_epcheck.sv`, Verilator 5.050):
- `base` job: base hop (expect PASS), tagdrop hop and wrongcopy hop (expect FAIL), base all (expect FAIL on the 78 RD
  beats).
- `rtl_tagdrop` job: hop (expect FAIL).
- Location: ot-epyc7:/srv/opentallas-scratch/claude/s81-tokb3. Client logs: /home/ubuntu/scratch/s81-tokb3/logs.
