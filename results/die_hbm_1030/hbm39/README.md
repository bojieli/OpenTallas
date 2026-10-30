# DIE-HBM-39 (HBM die owner, 2026-10-30 13:14-) results

CHECKED = from real files/runs; UNCHECKED = estimate. Run dirs: intel1 /srv/opentallas-scratch2/claude/die-hbm-39 (plan, G0,
bind); epyc2 /srv/opentallas-scratch2/claude/die-hbm-39/g2 (50-iteration GRT probes). Tools = this branch (base ca645350465 =
the d35b/d35c gate tools); G2 probes use DIE-HBM-38's run-local g2tools (flow-9-g2cut 7518687ff52 g2.py).

## (1) d38s = d35c + d38r  -> READY as HBM plan of record
- Built by re-running DIE-HBM-38's mk_d38.py mode r on plan d35c (mk_d38.py r plan/d35c plan/d38s <q0_base io.tcl>).
- Structure (CHECKED, json compare): q_b010 and q_b010__physical_v1 partition types are byte-identical to d38r; every other
  difference vs d35c is latency.lanes L28/L28m (28 -> 29 cycles, stations, natural) and the two q_b010 notes. Every other
  plan-dir file equals d35c. die_plan.json sha 4d2868a383c7.
- G0 6 err/918 warn, G0C 14 err/128 pending/910 warn. vs d35c: 0 new / 0 gone apart from the same 3 text-changed findings
  as d38r vs d35b (L28x2 WARN "> 5 station(s)" was "> 4"; pre-existing L204m hop-4 ERROR 900 um was 936 um) (CHECKED,
  g0/setdiff_d38s_vs_d35c.txt).
- Strict bind (bind.py --strict --all-gaps, same elaborated as-built as DIE-HBM-31 b31t) d35c vs d38s: both
  81 UNPLANNED pairs / 57,312 b, 0 tied/undriven/multiply-bound; UNPLANNED pair set identical (CHECKED). bind_latency differs
  only in L28/L28m bound_stages = plan_cycles 28 -> 29 (consistent with the plan, bind/latency_d35c_vs_d38s.diff).
  (The 79 / 51,807 figure is Codex's HH-seam candidate, not in the plan of record.)
- Pins: no partition pin, face or core pins file changes vs d35c (only internal ft_slot bit_sites/regs/stations of
  L28x2/L36x2/L168mx1/L204mx1) -> pincmp against d35c trivially MATCH (CHECKED json compare). No clock tap/entry/core moved ->
  no die clock rerun needed (same as d38r).

## (2) "probe containers exited at pin access with no exit file" -- ROOT CAUSE: stopped by DIE-HBM-38 itself, not memory
- The 4 containers that ended without probe.exit (q0_d38r, q0_d38a, q0_d38r_vb8, q0_d38a_vb8 = the v1 plans) all ended at
  13:02:2x within 10 s. DIE-HBM-38's own transcript has `docker stop -t 5` of exactly those 4 containers at 20:02:04Z
  (= 13:02 PDT) after v1 was superseded; docker stop kills the container's bash, so `echo EXIT > probe.exit` never runs.
  Memory was not the cause: the live siblings sit at 28 GB of a 48 GB cap in the same phase (CHECKED docker stats); no
  kernel OOM entry 12:40-13:10 (CHECKED journalctl -k).
- The fixed-plan probes q0f_d38r / q0f_d38a (intel1 die-hbm-38/g2) are NOT dead: still running pin access (single-threaded,
  ~40k groups at 13:35). Adopted, not touched. Pin access on d38s = q0f_d38r (q_b010 is identical in d38r and d38s).

## (3) HBM GRT, >= 50 iterations -- LIVE on epyc2 in parallel (COORD 13:2x capacity note)
- g50_d38s (= d38r q_b010 probe; regenerated from d38s, diff -rq identical) and g50_d38a (DIE-HBM-38 gen_d38a = core move +
  L36x2 4 stations, L36/L36m 14 -> 15): docker dhbm39-g2-29754/29757, 8 CPU, 56 GB cap, -congestion_iterations 50, started
  13:27. Rate on the earlier 30-it probes ~17 min/iteration (dhbm36 base at it 7 after ~2.2 h) -> 50 iterations ~14 h,
  final ~03:30 10-31 + pin access (UNCHECKED estimate). Collect: epyc2 .../die-hbm-39/g2/g50_*/grt.json (g2.py parse runs at
  exit) + grt_congestion.rpt; judge only at >= 50 iterations.
- NOTE (CHECKED grt.log "Found 0 clock nets"): the G2 partition probe routes data/ft nets only; clock taps are placed as
  blockages but no clock nets. It is NOT the "die GRT0 incl clock" freeze gate, which (PATH-HBM) runs ot_clk + clock GRT
  once strict bind = 0; bind is still 81 pairs, so the real gate cannot run on any HBM plan yet.
- Adoption rule (COORD 13:14 (3)): d38a only if its converged overflow beats d38s.

## (4) Watch: d38r/d38s worst post-DPL hop 404.19 vs 405 um -- recheck on the first routed q_b010 (none exists yet).

## (5) TOK-12 cycle deltas posted (queue 13:3x): d38s L28/L28m 28 -> 29; d38a also L36/L36m 14 -> 15.
