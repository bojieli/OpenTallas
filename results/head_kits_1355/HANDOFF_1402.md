# HEAD kits handoff — explicit Claude reset 2026-10-29 14:02 PDT

Parked clean and pushed codex/head-kits-1355@46b4e8c40 (source builder787f0605c, diagnosis48f5a189b, terminal receipt46b4e8c40), from mainfb1fc7959. Own WT /srv/opentallas-scratch/claude/wt/codex-head-kits-1355. No main merge, no RTL algorithm/cycle change, no P&R on the new kits. All own jobs terminal; helper diagnostic CTS remains live. No new engineering/launches after explicit reset.

## Collected failures and concrete fix

The previous actual cropped ctl/host/mesh jobs did NOT reach LEC: PORT_BIND FAIL on ctl extra32CAstrap bits/missing5raw aliases, host extra14/missing4, mesh extra14/missing6. Generic gen.py reconstructed wrappers without HEAD's registered raw-output patch and no count-pin sites. This was a kit-source/inventory defect, not proven RTL inequality.

New tools/s81_head/head_source_cropped_kits.py reuses the established head_tile_source7_kit recipe: macro-aware head_count_strap_sites.apply, then head_start_reset_aliases.patch_rtl with exact recorded instance/Q matching. It writes a fresh own output and preserves source plan input files. No loose inventory acceptance, missing-port waiver, cycle or numerical change.

Actual corrected GEN terminal PASS exit0, collected during parking: intel2:/srv/opentallas-scratch2/claude/codex-head-kits-1355/cropped1; unitoth-ubuntu-342468-1793307595/client341563. Receipt says ctl32M5constant pins+5registeredraw aliases, host14+4, mesh14+6, all0cycles. Input exact codex-head-start-0828/hk5_source/source/source_plan.json + source_sidecar.json; pinned own wt/codex-head-kits-0822 native/tool root keeps approved automatic-isnan. Receipt committed results/head_kits_1355/gen_receipt.json. Corrected kits are at cropped1/kits/{hd_ctl,hd_host,hd_mesh}; synth/LEC/P&R NOT RUN on these corrected kits. Next: source gates on them, then actual plan/layout render review before P&R. HEAD ctl constant-fold/FSM proof work remains DIE-HEAD-30 owned.

## Other inherited results

FT census v2 and fixed-input v3 both terminal PASS on all9types: max planned RT-relay to tap146.688um; all9 boot deltas0. v3 preserves existing reset input choices and deduplicates local reset consumers when a new implicit clock reset consumer occupies the identical point. Exact output intel2:/srv/opentallas-scratch2/claude/codex-head-kits-0822/hk6_ft/plan_clockcensus_v3.json, .clock_census.json, .reset_choices.json. Parent owns batch adoption, current geometry legality/G0 and die-clock rerun. Earlier st_str actual234.02clock-reach failure remains retained; census PASS is not a routed timing result.

Current-preseed copied mesh diagnostic LEC terminal KEEP FAIL:7/16521 kept bits folded/merged/renamed plus419 compare differs. Bits are the existing EPready/GBphase-FSM class under u_la/u_lb.u_ln.u (rdy_k[3], g_pc[0].ps[5], g_pc[11].ps[3], g_pc[5].ps[4]). Next: exact qualified same-edge/FSM correspondences used by canonical LEP closure, keeping every KEEP obligation. File intel2 codex-head-kits-0822/lec_seed/mesh/lec/lec.json. Host diagnostic still no terminal lec.json; existing jobs untouched, do not duplicate. Prior hd_ctl result is already diagnosed by DIE-HEAD-29 as const-load/fsm/keep correspondence work, not silently waived.

## SerDes/LEP helper

Helper parked clean codex/head-serdes-1355@3d9dd6393; full packet handoff/codex_head_serdes_20261029_1402.md. Quarter+keep strict LEC EQUIVALENT4217/4217; actual trialPLACE exit0/GEOM59 PASS-COND. No previous CTS/GRT had been launched, so helper advanced one reviewed diagnosticCTS clone.

LIVE intel2:/srv/opentallas-scratch2/claude/codex-head-serdes-1355, unitoth-ubuntu-332115-1793307569/client330588/containercodex-head-serdes-1355-cts. Already-collected raw CTS metrics (independent headline check not done): TTsetupWNS-2.51/TNS-4.36, FFhold-2.35 pl[7]->pl[8]; setup worst e1_dv[29][1]->crc[251], so original popcount -166.73ps bottleneck is removed (164.22ps improvement). 833ps unchanged. No GRT/DRT/SIGNED claim. Leave job untouched; next collect4_cts.odb/final report and use canonical approved HEAD flow basis for GRT/hold repair, no new pipeline based only on diagnostic near miss.

LEP V1/V2 PLACE jobs do NOT exist in actual run dirs/docker inventory; some similarly named tile variants had been mistaken for them. Coupled-move5d47d7bcee8 model is0violations at378um/0cycles, but still needs a fresh actual kit/placement using those targets. No analytical rerun or fake physical pass substituted.

## Check commands

ssh intel2 'tail -10 /srv/opentallas-scratch2/claude/codex-head-kits-1355/gen.otrun.log; cat /srv/opentallas-scratch2/claude/codex-head-kits-1355/cropped1/receipt.json'
ssh intel2 'tail -10 /srv/opentallas-scratch2/claude/codex-head-serdes-1355/cts.otrun.log; tail -20 /srv/opentallas-scratch2/claude/codex-head-serdes-1355/cts.log'
ssh intel2 'cat /srv/opentallas-scratch2/claude/codex-head-kits-0822/lec_seed/mesh/lec/lec.json'

OWNER? None new. No failed verdict overwritten, no job killed, no relaxed clock/corner/uncertainty.
