# MU.TOK (S81): multi-user programme bench on the real dsdv_seq_host (MU-S81/TOK, 2026-10-19)

The question is whether the S81 sequencer can run the static shift calendar: user k runs the single-user layer programme
shifted by shift_k, with its own {user, pos, tok} context, and user 0 stays cycle-identical. The vehicle is the smallest
component that holds the mechanism. That is the real `dsdv_seq_host` (L0 link, L1 `dsdv_sh_sq` with
`ot_dsdv_fixed_issue` (two job contexts), L2 V packer with context splice, L3/L4 hops), booted with the compiled L0 / L2
programme through its host lane. Bench: `tools/s81_dv/layer_prog/tb_dv_prog_seqhost.sv` with `+mu=FILE`. With no `+mu`,
the TB is the single-user bench, unchanged. Checker: `check_mu.py`. Driver: `run_mu.sh`. Built with Verilator 5.050 on
ot-epyc4 via ot-run. The RTL is unchanged.

## Inputs
- Calendar: `results/arch/mu_s81_1018/calendar_ar_q4.json` (`dv_mu_calendar.py --phase-q 4`, see Finding).
- Programmes: `dv_layer_compile.py --layer L0|L2 --die-ref 3923ae6de --mu-ctx --mu-cal calendar_ar_q4.json` gives
  `prog_L0_mu/`, `prog_L2_mu/` (with `prog/mu_slots.json`). `--mu-ctx` (default off; without it the output is
  byte-identical, test_dv_layer_compile PASS) gives the HLOAD V row context 1. Its beat then carries
  body[159:108] = {user, pos, tok}; the HLOAD template leaves those bits 0. Row edges are unchanged.
- Job starts (`runs/mu/*.txt`, "shift user pos tok"): the users of one die's group copy, shift = start minus the copy's
  first start, pos = pos0 + 3 x stride, tok = 1000 + 7 x user (bench data).

## Results (`runs/summary.txt`, `record.json`)
| run | users (shifts) | result |
|---|---|---|
| base: committed single-user L0, default TB | 1 | SEQHOST_PROG PASS C=11 (TB default intact) |
| L0_all: S000 (not duplicated), one seq_host | 46 AR users, 0 .. 959,112 | **PASS**: user 0 identical, 414 events = 46 x 9 shifted, no fault, 46 jobs |
| L2_A: S002 copy A (latency user 0 first) | 23 users, every 2 slots (42,624/42,628) | **PASS** |
| L2_B: S002 copy B | 23 users | **PASS** (first B user = its single run) |
| m_shift4: mutant, shift 4 < programme span 77 | {0, 4} | FAIL as required: issuer **fault code 9** (two contexts issue V south on one edge), no stall |
| m_ctx3: mutant, 3rd job while both contexts are live | {0, 8, 16} | FAIL as required: **fault code 5** |
| m_raw: mutant, raw 1-cycle-grid calendar shift | {0, 21313} | FAIL: **fault code 5** (off the 4-edge start phase) |
| m_drop: mutant, issuer job_user forced 0 | 46 | FAIL as required: 45 context beats carry user 0 |

(a) is checked line by line: every event (VO/CW/SJ/KD, edge and payload) before user 1's KS equals the single-user run.
(b) is checked as an exact multiset: users' post-KS events equal user 0's moved by shift_k, with user k's context in the
HLOAD beat and its tok in the KIT done. Nothing is missing and nothing is extra. A two-edge spacing is legal: the two
contexts overlap without a fault unless they issue the same engine on the same edge. The real calendar spacing is
21,312 edges or more, against a programme span of 77, so only one context is ever live.

## Finding (compiler)
`ot_dsdv_fixed_issue` accepts a job only when phase_q + 1 == start_phase. phase_q is a free-running 2-bit counter, so
every user's start must be a multiple of 4 edges after user 0's on every die. The lane calendar uses a 1-cycle grid
(shifts 21313, 42627, ...; period 980425). It is infeasible on the RTL: m_raw faults on code 5. `dv_mu_calendar.py
--phase-q 4` quantises the shifts and the period to 4. The default `--phase-q 1` output stays byte-identical. Results:
AR 46 users, slot 21,313.7, period 980,428 (+3 cycles); MTP 10 + 1, slot 124,524, period 1,303,400; lemma brute force
PASS, 0 collisions; tok/s unchanged at 0.1 resolution. The lane lead should adopt `calendar_*_q4.json` as the record.

## Tiles
No RTL changed. No tile and no CLOSED tile changes or needs to re-close. The only edits are the bench TB and checkers
and the compiler options (default off).

## Vehicle 2
The svc 2-user bench is owned by MU-S81/SVC and was not reported at 10-19. MU-S81/HOST (dsdv_mu_hslot) is a separate
leaf, which this run neither composes nor covers.
