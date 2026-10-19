# MU-DIE-S81/MUWIN (10-19): the compiler emits the multi-user window and replay timings

## The gap
MU-DIE-S81/MUREPLAY (9fbc143b3) found that `dv_layer_compile --mu / --mu-ctx` emitted no `dsdv_mu_hwin` / `dsdv_mu_hslot`
(NEV > 0) event rows. Without them, the end-slice MU lanes stayed idle in every replay: `mu_c` (TX tag windows) and
`mu_rc` (landing replays). Any `--mu-win` run was diagnostic, built from hand rows.

This branch is `claude/mu-die-s81-muwin-1019`. It is MUREPLAY 9fbc143b3, plus this work, merged with LINECOL 170b432c1.

## What changed
- New file `tools/s81_dv/dv_mu_win.py` holds the compiler side. `dv_layer_compile.py --mu-cal CAL --mu-ctx --mu-win A|B`
  now writes four files into `prog/`:
  - `mu_win.json` holds:
    - one event row per stage h hand-off (`substage_hop<i>`) and per end slice (s_7N / s_7S / s_0N / s_0S = hwin ep 0..3);
    - each row's `{kind tx|replay, ep, inst, lane, lane age, D}`. D counts edges after the f_ks capture edge: the
      output register takes the value on edge capture + 1 + D;
    - the user-0 edge where the command lands at the slice pin;
    - the per-slot `{land, ab}` of this die's copy, in local slot order. land is 0 only for the latency user;
      ab = copy B;
    - the slot gap table, RL, and the static checks.
  - `mu_cfg.cfg` is the boot stream in the format of `tb_dsdv_seq_host_mu`:
    - CSR 0x15 (f_mc): one sel-0 word per slot gap, then RL;
    - CSR 0x16 (f_mw): for each event, select + D + the per-slot attributes.

    This is the GEN mu2 master: `dsdv_seq_host_mux` = gap-table hslot + `dsdv_mu_hwin` (MU-S81-2 ac336f805 + 5dd45e769).
  - `mu_boot.memh` holds the same words as 515-b host words.
  - `mu_cfg_mu1.cfg` holds the same rows in the GEN mu1 format: hslot NEV 8, with window words on 0x15 sel 1 d[23]. It is
    written only when the copy's starts lie on ONE uniform period. The record q4 calendar does not, because its gaps
    are 21,312 / 21,316 (see 5dd45e769).
- Timing model. These are the constants in `dv_mu_win.py`:
  - **Layer-to-capture mapping.** Layer cycle c = capture + c - layer_issue0 + 4 (dsdv_seq_host).
  - **Lane convention.** A lane of age A lands a register value on edge e + A - 1.
  - **TX command lead.** The TX command lands LEAD_TX = 4 edges before ceil(hop.start). The lep needs at least 2.
  - **Replay command lead.** The replay command lands REPLAY_LAT = 6 edges before ceil(hop.end) - NB. That is the
    cut-through stream's first beat on ri: dsdv_mu_land needs 4 edges and the lep pin flop needs 2.
  - **D.** D = (pin - layer_issue0 + 4) - A.
  - **RL.** RL = job-0 KIT age + 7.
- Static checks. The compile refuses with verdict FAIL when any of these fails:
  - NEV ≤ 8 and nw ≤ 47;
  - every gap ≥ nw, and RL > nw;
  - every D in [nw + 2, RL - 2];
  - at most one command per end-slice port per edge over the whole period;
  - **port alone:** no scheduled outbound lep event of any user falls inside any user's TX window.
- `dv_cut_replay.py gen --mu-win auto` reads the compiled table and refuses it if the verdict is not PASS, if the copy
  differs, or if any lane age differs from the build. It drives each user's commands at the slice pins (user-0 edge +
  shift). On seq_host cuts it appends the CSR boot words after `host_boot.memh`, before the first start. When the
  slice sits outside the cut, the MU lanes become strict output checks. Two new mutants: `mu-win-shift:<ev>:<n>` and
  `mu-win-drop:<ev>`.
- New bench `rtl/dsrom_sys/s81_dv/unit/test/run_mu_win_prog_bench.sh` (checker: `dv_mu_win.py cases|check`). It runs on
  the real MU seq_host master: the RTL of 5dd45e769 (hslot, hwin and tb, staged as `mu2/`) around the real
  `dsdv_seq_host`. It boots the compiled job-0 programme over the host lane and then the compiled `mu_cfg.cfg`, and
  starts the users at their calendar starts for 2 periods. The check requires:
  - every compiled `mu_c` / `mu_rc` command on its exact edge (capture + 1 + D), with the start's {pos, user} and the
    slot's {land, ab};
  - nothing else on the MU ports, and t_mf 0000.
- L0 MU was recompiled with `--mu-ctx`: HLOAD arg 0x75 -> 0xf5. Against TOK's prog_L0_mu, this is the only calendar
  difference. LINECOL found and fixed the same svc-tag recursion bug. The merge keeps both arguments, and `mu_win`
  also passes through the line-delay recursion.

## Compiled tables
Compile: tree = TOK tree_mu (mu1 die.v sha 81498f42), `calendar_ar_q4.json`, fixtures `layerbench-s81`, LINECOL line
slots 0 collisions. The full tables are in `compiler/prog_<L>_mu_<copy>/mu_win.json`.

| layer / copy | nw | RL | hops | TX D (ep 0..3) | replay D (ep 0..3) | verdict |
|---|---|---|---|---|---|---|
| L0 A (46 users) | 46 | 11,194 | hop0 8,053-9,126 | 7,992 / 8,014 / 8,016 / 8,011 | 8,983 / 9,005 / 9,007 / 9,002 | PASS |
| L14 A, B (23) | 23 | 22,844 | hop0 19,640-20,713 | 19,646 / 19,668 / 19,670 / 19,665 | 20,637 / 20,659 / 20,661 / 20,656 | PASS |
| L20 A, B (23) | 23 | 25,565 | hop0 22,427-23,500 | 22,363 / 22,385 / 22,387 / 22,382 | 23,354 / 23,376 / 23,378 / 23,373 | PASS |
| L2 A, B (23) | 23 | 22,854 | hop0 + hop1 | 16 rows | | **FAIL nev**: 2 hops x 4 ends x 2 = 16 > hwin NEV 8 |

## Proof on the seq_host master (fleet ot-epyc4, Verilator 5.050)
See `bench/`. Fleet chain: `fleet_run.sh`, MU_WIN_PROG_GATE.

| run | starts | result |
|---|---|---|
| L0 A, users 0/1/2 x 2 periods | 6 | **PASS**: 40/40 compiled events on their edge, t_mf 0000 |
| L0 A, all 46 users x 2 periods | 92 | **PASS**: 728/728 |
| L14 A, 23 users x 2 | 46 | **PASS**: 360/360 |
| L20 A, 23 users x 2 | 46 | **PASS**: 360/360 |
| mutant `mut_winshift`: TX row 0 D + 1 (window moved one edge) | each run | **FAIL** as required (missing MC0 on the compiled edge) |
| mutant `mut_replaydrop`: replay row 4 never loaded (replay dropped) | each run | **FAIL** as required (missing MR0; the hwin config fault also rises) |

The fail witnesses are `bench/L0_u012/mut_*_fail_witness.log`, with the runs in `run_mut_*.log` and the regexes in the
runner: `MUWIN_PROG FAIL.*(missing|unexpected) MC` and `MUWIN_PROG FAIL.*missing MR`. A first chain on the
pre-LINECOL compile (same L0 table) put the same 40/40 and 728/728 events on their edges.

The base run raises one issuer fault, code 8, on the edge first start + svc done age + 6 (L0: 5,092 + 3,987 + 6). The
cause is the bench, which has no svc_rs model, so the compiled svc job's done never returns. The checker accepts
exactly that one fault and nothing else. In `ot_dsdv_fixed_issue`, run_fault is status only, so the KIT returns still
match RL: t_mf 0000 means the hslot return check passed on every start.

## cut_7, users 0/1/2: the drive works, but nothing can be checked yet
`gen --mu auto --users 0,1,2 --mu-win auto` on cut_7 (L0, mu1 die.v) drives the compiled commands:
- TX on ht_7N / mu_7S at user-0 pin edge 8,050, plus the shifts 21,312 / 42,624;
- replays for users 1 and 2 at 9,041 + shift.

The mutants change exactly those words: `mu-win-shift:0:1` moves 3 words one edge, and `mu-win-drop:4` removes the 2
ep-0 replays. Generator logs are in `logs/gen_R_cut_7_*`. The replay still has **0 checked lanes**, so none of these
runs can FAIL. I did not run it on the fleet, because the result would mean nothing. There are three reasons, all
found here:
1. **No h beat reaches a lep.** Every programme lowers `substage_hop<i>` as a GAP: the lowering record names "end-slice
   send cfg + vp RDOUT -> lep", family vpx, the same ABI as a_allgather. On cut_7 the opened window therefore never
   counts its NB beats. The next user's window, or any ring beat inside the window, is then a sticky lep fault. A
   replay of an empty landing slot is a dsdv_mu_land fault.
2. **ABI mismatch.** The lep MU window stamps and lands only XB / XQ beats (`ot_s81sl_lep_core`: "the stage h message
   is XB beats ... ot_s81sl_vq"). Any other kind inside a window is a fault. The compiler's planned hop ABI uses RD
   (kind 4) beats, like a_allgather. One side must change before the hop is lowered. A fix agent or COORD decides.
3. **The lep fault is unbound.** In die.v, `u_s_7N` / `u_s_7S` (and every MU lep) leave the slice `.fault` output
   unconnected, so neither a cut bench nor the die status fold can see a TX-window, landing or replay fault. The
   window outputs that remain are lt_lk link frames, which are offdie and unchecked.

The seq_host side of the contract is proven exact (above). The slice side becomes checkable once three things exist:
(1) the hop lowering emits the h beats in the lep's ABI; (2) the lep `.fault` is bound to a die / cut output; (3) a
GEN mu2 die.v exists. With them, the same `gen --mu-win auto` makes the MU lanes strict on cut_7, and on cut_3S_ctl
(seq_host, real hwin) the lanes become output checks.

## Owed (to the parent / COORD)
- **L2 (2 hops).** `dsdv_mu_hwin` NEV must be 16, or the second hop must not hand off through the ends. This is an RTL
  parameter of the die master: re-gate the hwin kit. Until then the L2 compile refuses.
- **Multi-job layers.** All four layers run as 2 issuer jobs (calendar > 128 rows): L0 job 1 starts at layer
  12,750, after the job-0 KIT. If job 1 needs its own f_ks start, the hslot / hwin record it as a second start of the
  same user, off the slot grid: an off-calendar / dup fault. The job-1 start path in MU is unmodelled (dv_cut_replay
  drives job 0 only). The parent must check this with the die lead.
- **GEN mu1 vs mu2.** The mu1 die.v binds the 908a67c18 hslot (NEV 8, uniform S), which cannot run the record calendar.
  GEN mu2 must take 5dd45e769's gap-table hslot + hwin (hslot re-close 7046f5b72 running) for `mu_cfg.cfg` to apply.
