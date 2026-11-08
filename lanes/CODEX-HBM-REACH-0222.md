# CODEX HBM REACH + KITPARAM collection, 2026-11-08 02:25 PST

CODEX took over: result collection for DIE-HBM-91-REACH and KITPARAM remaining dry paths. No source, plan, tag, merge, deletion or running-job change.

## CODEX notes

- PASS: strict bind control and reach candidate both rc 0, collected from epyc4 `/srv/opentallas-scratch3/claude/die-hbm-91-reach/bind2_{ctl,new}/rc`. New bind completed, maximum RSS is in bind.log. This is connectivity only, no physical pass.
- PASS: KITPARAM `q_su11__physical_v1` dry completed KITRTL=0, PROV=0, TOPO=0, GEN=0, LINT=0 at epyc4 `/srv/opentallas-scratch3/claude/die-hbm-91/dry_tip3/rc.txt`. This closes the outstanding physical-v1 dry followup from 02:12.
- RUNNING: KITPARAM `q_b110` and `q_b110__physical_v1` gen_lint Yosys PIDs 2138502/2316194, ~33/27 min elapsed at collection, each 99.9% CPU. The `gen_lint_yosys.log` records memory-to-register warnings only; no terminal error. Keep healthy jobs. Parent unit `oth-ubuntu-1912187-1794131164`; output `/srv/opentallas-scratch3/claude/die-hbm-91/dry_tip2`. Six other rows there already have all five rc 0. This is not a new failure or hang.
- RUNNING: REACH fresh tests base PID 2644391, output `/srv/opentallas-scratch3/claude/die-hbm-91-reach/tests_m85.log`, ~18 min. `tests_cmp.txt` and `tests_m85tip.log` are stale (09:54 UTC); do not report their TIP-ONLY 0 as the current run result. The old tests stopped in collection on missing Python tkinter in two unchanged suites; environment dependency, not reach regression. The fresh base test currently spends time in a git status subprocess (3382943, CPU active).
- RUNNING: REACH faithful new dry paths on epyc4 `/srv/opentallas-scratch/claude/die-hbm-91-reach/dry/new`; q_hub_ne/q_hub_nw kit-rtl PIDs 3192904/3181659 CPU 100%; q_su30 PID3429368 CPU 100%. Other rows progress through topology/gen/lint via ot-run. No duplicate launched.

## Next

Collect q_b110 and pv1 lint completions and post exact result to KCLS/HBM lead. Collect fresh tests only after the base/tip pair finishes; do not repeat the broad sweep. Collect REACH dry final receipts from the controller on intel2 (remote item logs dirs are empty because the controller captures stdout). Preserve existing POR; candidate branch `claude/die-hbm-91-reach-istareach-1108@178842a72a` awaits its own remaining result and Claude merge lane.

## 02:31 PST class fix

NEW FAILURE diagnosed: REACH new q_su11/q_b113 and siblings failed kit-rtl before the known KITPARAM class: `invalid native station placement receipt: stations`. The writer emits both station-chain rows and macro-placement `{cell,site}` rows. The reader incorrectly requires a stations array on every row.

FIX READY: hub `codex/hbm-reach-receipt-1108@a4143b6aa7`, based on `178842a72a`. Only reader and focused regression test changed; recognized macro-site rows are skipped, malformed station records still fail, station identity/placement checks remain. Three focused tests PASS, unmodified-base control fails as expected, actual candidate q_su11 receipt/Tcl/RTL now accepted with 4 stations and 0 added cycles. No plan/RTL/clock changes.

Actual fixed branch-head kit-rtl pilot running via ot-run epyc4, own tree `/srv/opentallas-scratch2/claude/codex-hbm-reach-receipt-0222`, kit `pilot/q_su11_fixed`, controller log intel2 `/tmp/codex-hbm-reach-receipt-0222/pilot_fixed.otrun.log`. First command accidentally ran before the patch applied (git am lacked local committer identity); it reproduced the old failure and remains in `pilot.otrun.log`. Patch application completed before the fixed pilot launch. No P&R and no repeated physical run.

Local fixed source `/home/ubuntu/codex-hbm-reach-receipt-0222`. New worktree `/home/ubuntu/codex-hbm-phy-0222` created from d6e906593cc at KCLS parent's request and handed entirely to KCLS; do not modify it from this lane.
