# BUS-GEAR-2 lane handoff (S81 x feed 2:1 bus gear), updated 2026-11-12 07:15 PST

## 1 Scope
S81 x feed 2:1 gear (owner street lever 4): commit BUS-GEAR-1 work, unit benches + EQ (tb_s81_xgear_eq), plan lane-cycle
declaration, TOK-VERIFY, strict bind on ready12 base (then ready12b), READY to COORD + DIE-S81-88. Folds into ready12b if READY by
11-13 18:00 PST, else ready12c.

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/bus-gear-1, branch claude/bus-gear-1-xint-1112, HEAD b490b95b86 (pushed to hub), clean.
Commits: 360aaab821 (BUS-GEAR-1 work), b9553ae961 (merge origin/main d767dc851b), b490b95b86 (design fix below + generated
inputs/die_b178_xg.v, models/s81_asb_xgear_models.sv).
DESIGN FIX (b490b95b86): ot_s81_xc_gear_tx passes beat 0 combinationally into the partition face flop, holds beat 1 one edge
-> lane register stages unchanged, word +1 edge. Plan decl = beats 2 / word_bits 1104 / beat_index_bits 4, fixed_cycles NOT
touched (fixed_cycles becomes a bind pad stage u_lpad_*). EQ reference = ungeared die delayed 1 edge.

## 3 Running jobs
- Benches+EQ: ot-run client intel2 pid 2044573, log intel2 ~/bus-gear-2-logs/bench2.otrun.log; runs on epyc2
  /srv/opentallas-scratch2/claude/bus-gear-2/pkg/run.sh (package from b490b95b86). Results: epyc2 .../pkg/out/summary.txt
  (unit rc, xlane rc, xeq_h9 rc, xeq_h10 rc, "ALL DONE"); logs out/unit.log, xlane.log, xeq_h9.log, xeq_h10.log.
  Expect: unit "BENCH PASS (9 configs exact, 5 mutants caught)", xlane "XLANE BENCH PASS", xeq "XEQ BENCH PASS (h9|h10)"
  (H2/H3 MUT0 PASS; MUT1/2/3 FAIL).
- Bind prep: epyc9 nohup bash /srv/opentallas-scratch2/claude/bus-gear-2/prep_r12ng.sh (pgrep -f prep_r12ng.sh), log
  epyc9 .../bus-gear-2/r12ng/prep.log + prep.out. Copies bsrc4_r12ng (48G) to r12ng/bsrc_xg, applies gear stage g2
  (t65 ft4 nudge) on ready12ng 77cad171c6ee, decl, latency (only geared rows may change), landing width sync, xgear_die on
  asbuilt_f_s87r12g.json -> r12ng/asbuilt_xg.json, G0 plain + completeness. Ends with "PREP DONE".

## 4 Watchers
Only local background poll loops (no cron). Nothing for Codex to re-arm.

## 5 Results not yet posted
xgear_die.py from commit reproduces BUS-GEAR-1 outputs byte-for-byte (die_b178_xg.v md5 6a563e4a, models c864ce1f). Bench/EQ pending.

## 6 Next steps
1. When prep says PREP DONE: check r12ng/g0_plain.log / g0c.log vs ungeared ready12ng G0 (s_2N_L1 cut 0.72 should drop; census
   "as-built 1104 planned 556" rows should be absent once bound). If prep FAILs (e.g. nudge "requested slots not changed"), retry
   with stage g (apply_xgear_1112.py) and report.
2. Strict bind: on intel2 `ot-run --mem 64 --threads 8 --hosts epyc9 --dir /srv/opentallas-scratch2/claude/bus-gear-2/r12ng -- bash
   /srv/opentallas-scratch2/claude/bus-gear-2/run_bind_xg.sh` (~55 min, 57 GB). Result r12ng/bind.run; rc 0 = clean. Watch for
   LANE_CYCLES errors (should be none: cycles unchanged) and width/census errors.
3. TOK: tools/token_pass/reform_rebaseline.py --die s81 --base <ready12ng plan> --batch r12ng/plan_xg.json --out ...; it will read ~0
   (compose_tok_ds ignores word_cycles/cadence); real cost = TOK-VERIFY-1 cadence estimate AR -2.5..-4.4%.
4. Post READY branch@sha + files + tests + bind result to COORD, DIE-S81-88. Re-run prep with SRC0=<ready12b tree> when DIE-S81-88
   names ready12b.

## 7 Open asks
- COORD: owner of the compiler x cadence 2 change (xs_field_calendar/xs_place x_cadence; no branch on hub). Gear must NOT enter a
  kit wave before it lands. Also +1 word edge must be absorbed by the compiler / landing calendar (S81-ARCH-RTL-2).
- DIE-S81-88: ready12b plan path/sha.

## 8 Gotchas
- epyc7 load gate blocks ot-run for long; use epyc2/epyc9.
- Never edit files in bsrc4_* trees (DIE-S81-88's); my tree is a full copy r12ng/bsrc_xg.
- Do not set fixed_cycles on geared lanes (bind adds pad stage).
