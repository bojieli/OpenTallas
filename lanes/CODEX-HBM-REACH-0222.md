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

## 02:34 PST pilot followup

Fixed pilot `oth-ubuntu-3722036-1794133841` cleared the receipt stage, then failed because the new sparse source lacked rtl/lib/ot_reset_sync.sv. This is a pilot source prerequisite, not a code regression. Added rtl/lib to the own source sparse checkout and launched the source-complete kit-rtl dry (no physical run), output `pilot/q_su11_sourcecomplete`, controller log `/tmp/codex-hbm-reach-receipt-0222/pilot_sourcecomplete.otrun.log`. Original failure logs preserved.

Complete base dry census: 25 finished rows, WCOPY16 + RING2 + provisional6 + recursive-root1. Candidate dry currently has 12 mixed-receipt failures plus known source-class dependencies. The 12 affected rows are q_b113(+pv1), q_su00(+pv1), q_su01pv1, q_su11(+pv1), q_su20(+pv1), q_su21, q_su31(+pv1). The source branch used by that inherited dry predates KITPARAM/kcls fixes, so those repeated known classes are not reach regressions. HBM token agent notified that reach LAT_85-lane/PIN83-lane ledger is unadopted; reader fix adds 0 cycles and needs no token reprice.

## 02:42 PST progress

- Receipt real branch-head q_su11 kit-rtl PASS rc0, ot-run `oth-ubuntu-3809543-1794133985`: 30 files, 2 variants, unbound0. Source-complete kit and exact controller log are above. The earlier sparse-source failure is resolved; no physical run.
- Recovered predecessor respreader onto hub `codex/hbm-ista-respread-0222@1ee657291e` from d6e906593cc, exact kit_istations.py/test predecessor files. Focused26 tests PASS. t3 tip/base242 file rc lines identical. dry3 hub topology rc0 both; plain gen still CPU100%, RSS~0.87GB (NE2613041, NW2777180), not stopped. pg_hub provisional fails both, so no geometry release; respread max hops1076/899/717um still require actual review and physical pilot.
- NEW provisional direction classes diagnosed/fixed on hub `codex/hbm-prov-dir-0222@8a7de434e0` from main289149dea5: xload bsel's packed dimension contains arithmetic parentheses, so `_DECL` stops before the port; strip ranges before matching. Real source fixed bsel=input vs base missing. Q2N2 module working copy intentionally absent; recipe files_at pins the exact module at97b0810d615ae4f7847fed52d3a4a286456ee2a9. Reader now takes directions from that exact pinned file/top, preserving failure for unknown/ambiguous tops. Real pinned header40 ports, including writer_kq4 output and vmasm_rd_il input. Focused12 tests PASS including wrong-top negative.
- Actual provisional-only hub dry of branch tool launched via ot-run E4, own outputs `/srv/opentallas-scratch2/claude/codex-hbm-reach-receipt-0222/provdir`, controller log intel2 `/tmp/codex-hbm-prov-dir-0222/dry.otrun.log`; no P&R/overlay weakening/POR change. Collect next.

## 2026-11-08 02:46 PST runtime class and open inventory

Direction package now hub `codex/hbm-prov-dir-0222@bd4edf5333` (8a7de434e0 + process-local source index). Parent requested this bounded fix after measured repeated13-second scans. One git grep --untracked declaration scan per root builds exact module/file lists; existing priority, multi-module files, missing names, non-git shallow fallback and pinned recipe headers preserved. Focused13 tests PASS. Actual WS standalone source-index smoke, E4 `oth-ubuntu-28785-1794134751`, PASS rc0:16,427 modules in13.318s; cached lookup4microseconds; real xload bsel=input and pinned q2n2 directions40. Controller log intel2 `/tmp/codex-hbm-prov-dir-0222/index_smoke.otrun.log`. Original full provisional dry stays running unchanged; no duplicate hub dry.

Open at measured02:45:29 PST: KITPARAM q_b110/pv1 Yosys PIDs2138502/2316194 CPU99.9%, elapsed53:37/48:06, RSS404/395MB, only memory-lowering warnings. No final rc. REACH basepytest2644391 alive38:40, currentlog140bytes lastchanged02:43:22, still0%; tip/comparison timestamp01:54:52 stale. No additional broad validation. Respreader plain NE gen produced fresh2.06MB ft_bit_sites.tcl + ft_track_use.json at epoch1794134375, actual progress; neither inherited gen stopped.

## 2026-11-08 02:57 PST completed direction dry

PASS: original full provisional dry finished NE rc0 and NW rc0, unit `oth-ubuntu-3978797-1794134307` exit0. Parsed PROV_JSON child counts are NE29 and NW32 (earlier visual30/34 reports are corrected). All contract directions resolved, including xload and q2n2. No P&R or POR release; respread long hops still require review/pilot. Same controller log and E4 provdir outputs as above.

Receipt independent TOOL-ONLY READY is now hub `codex/hbm-native-receipt-tool-0222@dc73be6fd9` from main289149dea5, identical two touched files to tested/piloted a414. Use dc73 to land the class without the unadopted reach plan event; original a414 remains candidate pilot lineage.

Parent's PHY latest-source dry independently passed all5 contract masters. Confirmed current EP header parses21ports with rx_block_ready/fault_cause outputs; old source exposure caused its failure. A requested source-only PHY probe was queued before parent reported PASS, then cancelled ONLY own client3686466 via exact phy_source.py path because answer no longer needed. It was not admitted; no duplicate full dry, no other job stopped. Remaining collection: inherited q_b110/pv1 lint, REACH base/tip tests, inherited REACH last2 hub dry paths/plain gen.
