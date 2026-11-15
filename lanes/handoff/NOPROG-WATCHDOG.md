# NOPROG-WATCHDOG handoff (2026-11-14 18:2x PST)

OWNER ORDER 11-14: "we need a no progress watchdog rather than a time limit."

## What runs
- Tool: tools/autopilot/noprog_watchdog.py (branch claude/noprog-watchdog-1114, head 8d121459970, READY to ROOT-MERGE-63), deployed by copy+mv to ~/.local/bin/ot-noprog-watchdog on intel1 intel2 epyc2 epyc7 epyc8 epyc9 epyc10.
- Timer: user unit noprog.timer (every 15 min, :00/:15/:30/:45) -> noprog.service -> `ot-noprog-watchdog tick` = scan --act on the host, plus the hub half on intel2 (the only host with ~/coord).
- State per host: ~/.local/state/noprog/{state.json, report.json, actions.jsonl, policy/keep.tsv, policy/superseded.txt}.
- Hub outputs: lanes/NOPROG-TABLE.md (whole table, every tick), lanes/NOPROG.tsv (one line per cancel), lanes/COORD-REVIEW-QUEUE.md (table line when the flagged set changes, NEEDS-LANE once per cancelled type), all via coord-commit.sh.

## Rule
- Window 6 h, improvement >= 2 % from the best before the window.  Elapsed time alone never cancels.
- Metric: gpl overflow column; drt `Number of violations` per iteration (DRT-0199); grt = repair tables in 5_1_grt.tmp.log (Remaining / Viol / Violations / |TNS|).  The GRT extra-iteration loop (GRT-0101/0102) prints NO overflow in this OpenROAD image (only GRT-0096 once at the end of a call), so while it loops the metric is "any new non-iteration line"; iteration lines and NDR warnings are noise.  Other stages and yosys: log growth.  LEC: newest write under work/lec (hypN.aig, gold.ys.log) -- a LEC that keeps writing is alive.
- Line times are interpolated (log birth -> samples -> mtime) until the tool has watched a job for a full window; interpolated verdicts use a 7.5 h window (x1.25), so a borderline job is judged on real samples later.
- Excluded: OT_HEAVY_PRIO=plan or bind/LATCHECK/G0/die-proto/chain commands; --priority die is NOT excluded; lines in lanes/NOPROG-KEEP.tsv (first tab column = substring of container / kit / work dir).
- Immediate (no window): kit dirs listed SUPERSEDED in autopilot/kit_wave_stages.tsv and HBM (parked).
- Cancel: only after an earlier pass (>= 1000 s ago) listed the job in a table, only when every container of the oth-* scope is flagged (a -lec container beside a healthy flow is REPORT-ONLY), via `ot-heavy-stop --match <kit dir>` after a dry run that hits exactly that unit, else `--unit`.  Kit dir kept.

## Operate
- Mark a job keep: add a line to lanes/NOPROG-KEEP.tsv (hub pushes it to all hosts every tick).
- Stop the watchdog: `systemctl --user disable --now noprog.timer` on the host.  Report only: run `ot-noprog-watchdog scan` by hand (no --act).
- Tests: python3 -m pytest tools/autopilot/test_noprog_watchdog.py (24 pass).
- Redeploy: tools/autopilot/install_noprog_watchdog.sh local intel1 epyc2 epyc7 epyc8 epyc9 epyc10 (copy + mv).

## 11-14 18:5x update
- First act pass cancelled 10 jobs (163.6 GB, 77 reserved cores, ~14 busy): see lanes/NOPROG.tsv.  Superseded kit dirs from kit_wave_stages matched 35 live builds, so they are listed as SUPERSEDED? and NOT auto-cancelled (COORD to confirm).  Branch head now ad0d1cad3a2.  LEC jobs still writing hyp files (serdes t2, seqhost t1, slice_iq_C t1) are alive by rule.

## 11-14 19:2x successor update
- Both open items are DONE and deployed (md5 50b485b2.. identical on all 7 hosts, timer active): (1) LEC > 24 h advisory cancel (LEC-only, or route result exists; standalone LEC container by exact docker stop); (2) SUPERSEDED auto cancel (kit plan sha not a live adopted plan) with keep list lanes/NOPROG-KEEP.tsv holding the 9 col representatives + /claude/s81-col-inherit/ forms.
- Branch claude/noprog-watchdog-1114 head 26d5f26641f (on origin, 26 tests pass) is NOT on main yet: READY posted to ROOT-MERGE-63 19:2x.
