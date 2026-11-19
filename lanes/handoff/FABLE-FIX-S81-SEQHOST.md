# FABLE-FIX-S81-SEQHOST handoff (started 11-19 02:1x PST)

Goal: close seqhost__t1 TT setup (gate TT >= -42, FF hold >= 0, DRC 0, bind + LATCHECK).
Lane dir: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-seqhost (repo/ = lane clone, eq*/ bench outputs, depth/, bench/, shadow/ = bench root with
physical/ and results/ linked from the D8f live tree). Kits: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-seqhost/kit1, kit2.
ot-run logs + pids: intel2 ~/.local/state/fable-fix-s81-seqhost/kit{1,2}.otrun.{log,pid}.

## Cause (read in the RTL)
seqhost u_win = dsdv_mu_hwin (rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv, instantiated by dsdv_seq_host_mux in the same file; the kit binds this file as is).
- due / fire: rp or pe[e] (6-bit binary) -> 47:1 x 32-bit mux of ts[] -> 32-bit add (+RL-1 / +D[e]) -> 32-bit compare with tm.
- then an 8-row procedural priority chain into mu_c / mu_rc, and the vld / pointer / fd update, and the ep / eu / ts write decode behind
  the full record condition (47 x 10-bit user duplicate compare). 27 gate levels, 21..32 fanout buffers (yosys netlist max fanout 8).
- fire -> pe / fd and due -> rp / vld are single-cycle loops, so an output stage (+1) alone does not close it.

## Fix (0 cycles, same ports, same output on every edge; no bind K / latency change)
- New cell dsdv_mu_hwin_age (same file): per entry an age counter b = (tm - ts) + 1 and REGISTERED compare flags for the next edge:
  mf[e] (ts + D == tm), lf[e] (late), df (ts + RL - 1 == tm). ts[] and tm are gone.
- One-hot shadows rp1h / pe1h[e] / ss1h beside the binary pointers; every select is an AND-OR reduction.
- Endpoint merge = parallel highest-row select per endpoint (same last-row-wins rule, same col_w).
- Payload / fired-flag / age write enable = st & slot & !vld (superset of rec; an entry that is not valid is never read).
- nw, nw+1, nw+2, RL-1 kept as registers written with lw / crl; arming compares on the low bits; group-lookahead x+1 / x-1 / a<b.
- Out-of-range pointer values (possible while idle after lw shrinks) read "not valid" and step on = the 2-state behaviour of the old source.
Structural depth (yosys synth -noabc, 2-input gates): 71 -> 25.

## Proof (rtl/dsrom_sys/s81_dv/unit/test/run_mu_hwin_eq.sh OUTDIR [EPISODES])
1. Lockstep vs the 11-18 source (test/ref/dsdv_mu_hwin_ref_1119.sv): NSLOT 47 NEV 8, 3 seeds, 592k edges + small tables 693k edges,
   mu_c / mu_rc / t_wf equal on every edge; dut MUT 3 / 4 / 5 caught.
2. Age cell induction (yosys sat -tempinduct, 32-bit, covers the 2^31 late-flag wrap): SUCCESS; broken cell fails.
3. Bounded SAT miter NSLOT 3 NEV 2 (yosys sat -seq, all pins free): see state below.
Existing benches on the new source: run_mu_hwin_bench.sh, tools/s81_dv/hwin_events_1113/run.sh, run_seq_host_mu_bench.sh: see state below.

## Kits (r712, ot-run --priority proof, goal grt, D8e kit copied from wave attempt_22 on epyc7, ONLY rtl/dsdv_mu_hwin.sv replaced, OT_LEC_ASYNC=0)
- kit1: first form (sha 94dfb953, `+` arithmetic). kit2: FINAL form (sha 5de3f4aa = the commit). Both launched 02:5x / 03:0x PST.
- Read TT: epyc7 <kit>/seqhost__t1/run/logs/.../ and tt_setup_repair output; the tail lane's frame = epyc8 tail1118-sta/seqhost_in/run.sh
  (awk prefix of tt_setup_repair.tcl + report_checks on 4_cts_pre_tt.odb). Control = -854.3 (4,895 ends).
- The kit is D8e without the LEPE tap rows: clock-tap classes (302 ps tap spread, FF hold -269) stay in it and are NOT mine.

## Open / next
- Push: python3 -I /srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-push-main in repo/ (commit has trailer Fixes-Items: s81/seqhost*).
- Adoption (S81-DIE-R3): one file for the S81 live tree, rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv; ports and cycles unchanged, so bind K and
  LATCHECK rows do not change; tools/s81_dv/layer_prog/native_hwin_calendar.py accepts both source shas.

## State 11-19 03:2x PST
- Lane clone commit 87f0991319 (NOT pushed yet). kit1 past synth (262k cells class), kit2 in synth. Waiters live in the Fable session.
- Running on epyc8: bounded miter eq3_12 / eq3_20, run_seq_host_mu_bench (bench_seqhost.log). MU_HWIN_GATE PASS, hwin_events EV_RC=0, check_ledger PASS.
