# CODEX LEP / LAND tstart handoff — explicit reset park 2026-10-29 02:04 PDT

Parent explicitly delivered ROOT PARK NOW. No new work/jobs/merges after this signal. All live jobs left running, no kills. Last read02:04:31.

## Sources / ready branches

Clean review branch `codex/head-lepwe-ready-1029`, pushed/clean tip `fc2bcb2b01c8d98c0c35217cda29254aff7ff160`, local WT `/srv/opentallas-scratch/claude/wt/codex-head-lepwe-ready` based maina7168d188. Do not merge the broad source branch below.
-6286469d2: exact zero-cycle LEP decoded writer a91 RTL + complete die-local kit driver and source proofs. Small lockstep/full-cycle simulation, formal positive+wrong-slot mutant, faceguard2140, portbind0 PASS. Shared RTL needs root review; no physical signoff.
-5abbbf922/7702c74cf: original actual G1FAIL and revised macro/register plan proposal packet.
-37fffe9dc: reviewed plan6 using actual pre-GPL master dimensions + guarded0.54um width reservation; all28161FF legal plan. Macro sites/outline/clock/RTL/cycles unchanged. Planning max390.69um,0above405; private390miss0.69 recorded honestly.
-b697f731b: exact seeded FSM diagnosis+scripts+hints+receipt.
-2ab39d868: shared lec.py optimization to seed explicit untrusted FSM cube/cons metadata before discovery. Ordinary refinement still proves/drops every obligation; existing normal post-correspond apply_hints retained.17tests PASS, including normal ABC correct-seed positive, wrong encoding dropped with functional DIFF, reachable state3 excluded constraint dropped with functional DIFF. Root shared review/merge required. Does not accept LEP kit or waive12EP/KEEP4.
-fc2bcb2b0: terminal own full-kit failure receipt.

Broad branch `codex/head-lepwe-1029` tipccfbac251 at `/srv/opentallas-scratch/claude/wt/codex-head-lepwe`, pushed. Contains broad Claude ancestors, DO NOT MERGE. Runtime helpers use remote own WT `/srv/opentallas-scratch2/claude/wt/codex-head-lepwe` pinned3bc84d406; do not delete while trial/refinement uses it.

LAND tstart branch `codex/head-tstart-1029`, pushed tip4a1d7945d, localWT `/srv/opentallas-scratch/claude/wt/codex-head-tstart`:
7b05ef0d7 canonical c0fb helper replaces only external START declaration in existing LAND3 composed copy: old362(363sidecar-aware)errors→0errors,346uses/stages,16openoutputs; no recompose.
6e708fed4 exact18RTLbyte hashes old/amended and parent live gen all identical.
4a1d7945d future reproducer uses explicit --repo-root plus adjacent compressed plan/sidecar, not deleted parent WT. Parent says LAND3 source/artifacts already merged and TT/FF jobs terminal. Results `results/head_tstart_codex_1029` need review receipt integration if not already done.

## Live jobs — intel2 (real host tolerant-swine)

R=/srv/opentallas-scratch2/claude/codex-head-lepwe. Inside intel2 ot-run host alias must be localhost, not intel2 (DNS failure preserved).

1. Actual reviewed placement trial6 LIVE. Client3880824; ot-run unit oth-ubuntu-3881683-1793262419; docker codex-lepwe-trial6-place. `R/trial_v6/place.log`, `R/trial6_place.otrun.log`. Last GPL9230,overflow0.5631,HPWL1.85m, repeated routability inflation cycles; not converged yet. Uses same existing synth/pre-GPL3_2checkpoint, no synth repetition. Fixed28161plannedFFs,19smallmacro permutation, original55sites. No route/GRT/STA. Actual G1 must pass and be viewed before any route.
Watcher PID3907527 `bash R/after_trial6_geom.sh` remains LIVE. Waits exact docker; only if place succeeds runs actual geom under ot-run8GB2. Results will be `R/geom_v6/auto_geom.{json,png}`, watcher log `R/geom_after_trial6.log`. Render/view actual PNG and diagnose every rule before route. Trial4 failed beforeGPL exact master guard (220ordinary drive-size changes); plan6 corrected actual preGPL names/master sizes and guarded reservation. Logs retained.

2. Limited seeded old-AIG correspondence diagnostic LIVE. Client927033; unit oth-ubuntu-927746-1793264057; docker codex-lepwe-fsm-refine; script `R/fsm_seed_refine.py`, output `R/fsm_seed_refine`, launcher `R/fsm_seed_refine.otrun.log`. Uses old baseline AIGs READONLY, existing proved hypotheses plus correct untrusted state bridge,2adding rounds. Last02:04 rawbase0/1 and hyp0 proof artifacts present (normalization completed; it is now actual refinement). Final receipt/proof/correspond logs expected. Not kit signoff. No duplicated synth. It redoes canonical alias initialization so startup took~9min; no kill.

Read checks:
`ssh -o ControlPath=none intel2 'tail -12 /srv/opentallas-scratch2/claude/codex-head-lepwe/trial_v6/place.log; tail -10 /srv/opentallas-scratch2/claude/codex-head-lepwe/fsm_seed_refine.otrun.log; ls -lt /srv/opentallas-scratch2/claude/codex-head-lepwe/fsm_seed_refine | head'`
`ssh -o ControlPath=none intel2 'docker ps --format "{{.Names}}"; cat /srv/opentallas-scratch2/claude/codex-head-lepwe/geom_v6/auto_geom.json'`

## Terminal results / remaining failures

Original actual new-source geometry `R/geom/auto_geom.{json,png}`: G1FAIL,109129cells/28161FFs,15.1%fill,55regularSRAMsites,0macrooverlap. Registered max508.68um,67captures>405;7collapsed relaychains.36gearbox mwd→beat_tx paths,19NKslot/controlpaths,7b_pay/replay,5reset. channelH0.731/V0.748. Pin_unreg556 is existing geom checker missing independently proven four-slot D4bank model; do not waive true pin distances. PreCTS bare clock reach400.86 is not routed clock failure. No route run. Actual image personally reviewed and failed before revised plan.

Own full-kit LEC now terminal FAIL at `R/kits/ot_s81hd_lep_pair_kit/lec/lec.json`. Runtime unit1306144-1793256771 exits3 FAIL_PREFLOOR. Faceguard2140/2140,portbind0missing/extra PASS.6965.2s total,t_corr6881.7,t_prove12.5.49073comparepoints,48983proved,90differs,0undecided. KEEP4 missing names,12EP hard comparisons. Receipt gz in ready branch. No source signoff.
Old Claude baseline full LEC also terminal KEEP FAIL at `/srv/opentallas-scratch2/claude/head-kits-3/diag/ot_s81hd_lep_pair_diag/lec/lec.json`:7571.8s,t_corr7434.1,t_prove11;48673cp,48583proved,90differs,0undecided. Same KEEP4/12EP. Never changed Claude WT/source/run.

Wrong automatic FSM map repeatedly selects gold state2→zero-hot and invalid state3→bit1. Actual mapped DFF metadata supports correct hunt0→bit0,1→bit2,2→bit1 (reset001,D1=hunt_n[1],D2=hunt_n[0]). Exact diagnostic `R/fsm_seed_diag/receipt.json` and proof.log: all3cube obligations and valid-state constraint PROVED;48664/48676obligations proved,12differs,0undecided. Thus78dependent gearbox failures resolved by valid bridge. Remaining12 are EP fault,ok_f,pnak,pv and K_ok q copies. Do not infer hunt causation merely from cone support: state constraint gates all outputs, so hunt appears in every cone. A proposed locked equality was NOT established or applied. Need diagnose actual EP replica/reset relations using live limited refinement result.

KEEP4 physical traces are four distinct FFs:
rdy_k[3]→INV→u_ep.in_ready FF;
g_pc[0].ps[5]→INV/BUF→g_pc[0].g_b[0].a0 FF;
g_pc[11].ps[3]→INV/BUF→g_pc[11].g_b[280].a2 FF;
g_pc[5].ps[4]→INV→g_pc[5].g_b[140].a1 FF.
Three a0/a1/a2 names not independently kept in gold.keep. Gold wiring alias JSON covers rdy/in_ready; three ps/data relations need inductive correspondence. Must use one-to-one assignment across ALL kept demands, no retention waiver, no false claim these FFs disappeared. No RTL preservation edits made; physical plan source remains exact a91decodedwriter.

Shared HA model already main: official local ASAP7 SIMPLE TT library CON=!A+!B,SN=A*B+!A*!B; output-pin-aware faceguard handles HAxp5, rejects unknown pin. Exact synthesized pair faceguard2140/2140PASS including556D4bits. Main checker64testsPASS at source-ready time.

No OWNER? item added. No blocker dialogs. Parent owns aggregate CODEX.md/LAND-HEAD bookkeeping.
