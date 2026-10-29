# Codex coverage handoff — 2026-10-29 14:02 PDT

Explicit Claude reset received from root. Coverage and both helpers stopped new engineering, launches and merges immediately. No live job was killed or restarted. Root was finishing the results-only dd547f4db/aab2c7d91 merge while parking.

## All-lane coverage

`lanes/CODEX-COVERAGE-1355.md` indexes all **206 work lane files**, including the newly added DIE-HEAD-28/29/30, HBM-KITS-17/18/19, QC provider and number lanes. It is linked from `lanes/CODEX.md`. Each row records takeover owner, latest source state, recorded run pointers and next/failure. Recorded historical run pointers are explicitly not assertions of current live jobs. Five die owners, tokens and shared flow owned their current remaining work; coverage helpers handled auxiliary collection and live independent reviews.

## Results / branches

- **Current S81 collector mutant:** `codex/support-1355@dd547f4db`, clean and pushed, results-only on actual source fix `9b39beae2`. Meaningful face-capture bypass mutant caught **255 errors in 576 checks**, executable exit1; wrapper requires that failure. Registered ready/fault/drop shifts from expected3 cycles to2; direct status remains2. Existing baseline is576/0. Source fix was independently reviewed by root/S81, not duplicated here.
- **Current SPB V3 geometry review:** `codex/geom-1357@aab2c7d91`, clean/pushed, results-only. Actual ODB pin dump and rendered image viewed:512 RX pins over3 M7 rows (171/171/170), y634.944/565.824/496.704, local escape depth4..36.64um, pitch0.192. PASS-COND for modeled PHY pin-table adoption only. Prior GRT0/pin-access0 is the owner's gate evidence. The full coupon has surrogate FFs inside the EP abstract; no full core/die placement, clock, PG, timing or sign-off claim. HBM owner received the verdict before reset.
- **Old S81 core-FREE source/gen waves collected:** all four jobs terminal exit0; all61 bound source exports PASS,49 kit generation PASS,12 generation FAIL (all actual SerDes u_phy reservation lacking native macro view). Current S81 source/band resize supersedes the old 3ad9fd700ad kits, so **none were promoted or routed**. Current S81 owner confirmed this disposition and owns the real PHY source/shape failure.
- **Auxiliary infrastructure:** AP13:54:08 tick exit0. Three HBM AP holds (aeb0fad45e8f/f40932da6645/15df583662e5) were diagnosed as a real old canary clock-insertion failure: FF pin mean385.194ps vs202.5±40, GRT overflow0/hold−3.89. The current parser already classifies it; an old08:38 JSON predates that classifier. Shared FLOW owns the canary/physical fix; no duplicate Tcl/parser fix or rerun launched.
- SIGNOFF, spare/type/test/old LEC waves remain historical or assigned to current die owners. No blind lost-DB rerun, stale source adoption or new gate. The earlier DMA16 geometry/source preparation is **not current plan adoption** after d16k qcore/location changes; HBM must regenerate against its current source/plan.
- An additional historical `test_kvsys_source_clocks` collection error was checked before reset. **Current central checkout passes all3 tests.** The thin diagnostic worktree lacked root tools/qwen_die_element_lib.py; no code defect, import edit or commit was made. Unchanged local branch `codex/kvclock-import-1355` points to already-published base fb1fc79593b, worktree `/srv/opentallas-scratch/claude/wt/codex-kvclock-import-1355`; no unique source or WIP. FLOW notified not to reopen the old error.

## Jobs / check paths

No live jobs remain from this coverage subtree.

- CST mutant: localhost `/srv/opentallas-scratch/claude/codex-support-1355/otrun.log`; unit359032-1793307617 terminal0. Evidence committed on dd547f4db; use that commit's file list for its exact receipt path.
- SPB review read job: epyc2 `/srv/opentallas-scratch2/claude/codex-geom-1357`, unit1158816-1793307498 terminal0. Committed dump/image/verdict `results/geom_review/codex_spb_v3_1357` on aab2c7d91.
- Old source/gen logs: intel2 `/srv/opentallas-scratch2/claude/codex-support-s81-0840/logs/*.json` and wave0..3.otrun.log, all terminal. These are source evidence, not current placed kits.
- Old canary: intel2 flow-canary/runs/hbm_7a77f0bc6_1029_070601_404787 (recorded basename; shared FLOW has the exact run path). Inspect hold/postcts logs for385.194ps insertion failure; do not restart blindly.

## Next steps and open failures

1. Resume current die-owner tasks listed in the206-lane index. Preserve frozen plans; current fixes are source/plan-specific.
2. Use actual collector source9b39beae2 plus the meaningful mutant evidence; current S81 owner continues t23 canary and t31/t44 regeneration, with +1 status cycle accounted for. Do not route old49 kits.
3. HBM owner integrates the reviewed SPB V3 pin table into its current plan view, retains modeled-PHY scope, and continues real bind/GRT/clock work. Full coupon surrogate-placement caveat remains explicit.
4. Shared FLOW resolves the actual HBM canary clock structure/insertion failure; no parser issue remains to fix. Current AP healthy does not turn that failed canary into PASS.
5. Prior selector reset candidate42f0d6913 is unchanged/unadopted; formal `$check` handling, parent reset/START contract and physical gates remain open with HBM. No obsolete proof or P&R launched during this cover.

OWNER? None new. Existing per-die owner questions remain with their current lanes; no blocking dialog opened and no rule/clock/contract decision made by coverage.
