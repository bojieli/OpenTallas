# GEN-CLASS-1 lane handoff (refreshed 2026-11-12 ~07:0x PST)

## 1 Scope
Generator / legalize / preflight CLASS fixes (successor of CLAND-CLASS-1 + STREET-RULE-1). Done + APPROVED: CLAND-SLEW-1,
LAND-OVERRIDE-STALE, legalize role match + FIXED-FACE flag. Open (COORD ~07:0x): (1) SIDECAR-COVERAGE preflight,
(2) PLAN-SRC-MACRO preflight, (3) classify HEAD-95 hd_spn_wshim_tx slew violators when sent.

## 2 Worktree
intel2:/srv/opentallas-scratch2/claude/wt/gen-class-1 (git object store = hub mirror, remote "hub").
Current branch claude/preflight-sidecar-macro-1112 = hub/main d767dc851b7, NO changes yet.
Pushed branches (all on hub): claude/land-override-stale-1112@cef99b3203, claude/cland-slew-1112b@33e70e1695
(ignore claude/cland-slew-1112@3375e6375c, truncated message), claude/street-fixedface-1112@a07f957bc5 (on top of
street-rule-1112@3cca0a68ed). Scratch: intel2 /srv/opentallas-scratch2/claude/gen-class-1/ (plans/, msg*.txt, patches).
Tests run with /srv/opentallas-scratch2/claude/rm-ai-1031/venv/bin/python -m pytest -p no:warnings
--basetemp=/srv/opentallas-scratch2/claude/gen-class-1/pt (no xdist).

## 3 Running jobs
None on the fleet. (Only a read-only find for S00 logs from localhost; no need to re-run.)

## 4 Watchers
None.

## 5 Results not yet posted
None. Affected list for CLAND-SLEW-1: ~/coord/lanes/gen-class-1/cland-slew-1-affected.tsv (HEAD 23, S81 227, QC 114,
KV 54, HBM 0); COORD: no blanket re-sign, unsigned types pick it up at next kit.

## 6 Next steps
a. SIDECAR-COVERAGE: KW-FIX-46 already has a LIVE kit_wave launch probe (skip reason SIDECAR_STALE,
   test_kit_wave_sidecar_preflight.py, runtime kit_wave md5 99312e5a91a3; check whether it is in git).
   Add the generator-side fail-closed check: where gen loads --clock-landing sidecar (grep "clock_landing" in
   tools/die_plan/gen*.py / clock_landings.py), compare sidecar collector types vs plan partition types BEFORE gen_rtl,
   raise "SIDECAR_STALE: sidecar <path> lacks N plan part types: ..." ; add kit_wave FAILURE class pattern; test.
   Rule: if KW-FIX-46's probe is not in git, also land it (coordinate with KW-FIX-46, do not duplicate).
b. PLAN-SRC-MACRO: HBM S00 (DIE-HBM-101) plan macros at u_fcore.u_core.u_l/u_s absent in src_hbm_main_9446d18f5d.
   kit_preflight.py has macro_instances (vs bound netlist); make the check run at kit preflight for every die, name
   the instance and the src, + test. Find S00 receipt first (ask DIE-HBM-101 for path if not found).
c. When HEAD-95 posts wshim_tx violator names: classify (ring dsel = CLAND-SLEW-1; else name net family).
d. Post READY per item to lanes/COORD-REVIEW-QUEUE.md via coord-commit.sh.

## 7 Open READY/ASK
All 3 earlier READYs approved by COORD (merge lane ROOT-MERGE-60, queue 07:0x). Waiting on HEAD-95 violator names.

## 8 Gotchas
- ssh heredocs mangle quotes: scp python patch scripts / message files and run them; commit with git commit -F file.
- Never git in /home/ubuntu/OpenTallas on intel2/localhost. ~/coord only via coord-commit.sh.
- ot-run: no colons in paths, intel2 cannot ot-run to itself (use epyc8/epyc9); docker verilator needs HOME=/w CCACHE_DISABLE=1.
- epyc4 kw45 src trees are self-symlinks (ELOOP): avoid epyc4.
- 3 tests fail on main too: band_reserve band_spread_steps, landing_pin_sites qc52, gen_phys_bump_ports refuse_mismatch.
