# CODEX HBM bounded parent trial

Updated 2026-11-06; latest resumed PLACE and station diagnosis. Owner: Codex hbm_parent, in coordination with HBM die owner.

Current concrete vehicle: q_spb2/NW_spb2, two actual signed ot_hbm_svc_sm_xcal_rel_t macros, current d44v36 type and retained native m79f body. No whole-die or parent closure claim.

- Source plans: intel2 `/srv/opentallas-scratch2/claude/codex-hbm-wave/d44v36/die_plan.json`; native bind epyc2 `hbm-bind-9/g_t11m79f` (strict-bind retained corrected bodies). Exact source and full original snapshots retained.
- Own tools: intel2 and epyc2 `/srv/opentallas-scratch2/claude/wt/codex-hbm-parent-1106` (codex/hbm-parent-1106 / codex/hbm-parent-run-1106).
- Own artifacts: `/srv/opentallas-scratch2/claude/codex-hbm-parent-1106/` on intel2/epyc2; staged kit/views on epyc5/epyc6.
- Submitted PLACE job: intel2 client PID 3582567, `~/codex-hbm-parent-1106/place.otrun.log`. Kit `.../xcal_gen_fixed/q_spb2`, ot-run priority die, 24GB/8threads/20GBdisk. It initially waited because epyc2 had81GB free minus70GB existing die reservations; same self-contained inputs now staged to epyc5/6 for automatic re-placement, no other job cancelled.

## Results and diagnosed failures

1. q_su21 first candidate: current type equals retained m79f type exactly. However native leaf is flattened ot_hnx_su_plain4__lid9_rst3 with MLAT4 lane_pinreg, while plan expects16 p17 lane1 children, signed at MLAT5. Attached real views yielded ZERO lane1 macros and would flatten1.37M logic cells. Do not route this false join. HBM owner/root informed; source composition repair remains open.
2. Real lane1 and xcal signed runs lacked LEF exports. Read-only OpenROAD abstract extraction from their actual signed6_final.odb plus canonical autopilot export now produces complete=true views with actual pins and both TT/FF libraries. No original signed run edited. Lane1 view remains available for later corrected SU composition; xcal view used now.
3. Current full plan's old same-face FT declarations blocked schema generation. Die owner supplied explicit tested turnaround support; bounded xcal plan retains3 turnarounds with exact same windows/stations/pins. Two obsolete slots L117x2/L138x2 removed only in bounded plan, owner-confirmed zero full-plan ports and zero native RTL mentions. Canonical cleanup remains die-owner work.
4. Native wrapper source basename collision (SU case): two different ot_hdc_prefix.sv files define disjoint suffixed/unsuffixed modules. Private kit_dedupe byte-preserving filename aliases unblock source assembly only when module sets are disjoint and no relative includes exist; actual bytes asserted unchanged. Shared kit_assembly owner has details.
5. xcal physical abstract ABI: signed hardmacro has no elaboration parameters, while native instances pass DD256/PAW11/PREL1/XSLOT1. Minimal hierarchy probe demonstrated missing-XSLOT error. Those values match the signed face-shell's u_fcore exactly; only redundant parameter lists stripped at two private physical macro instances. Record `xcal_fixed_parameters.json`. No new cycles, arithmetic, ports or constraints changed. Existing signed shell +1in/+1out timing contract still needs full native schedule/model reconciliation for release; TOK notified.
6. Physical kit generation PASS:6RTL files, two real xcal macros, no unbound buses, no spare output tie-offs. L83_i has71 known unread spare input bits retained in generated dead-input metadata.

## Review and model

Actual `xcal_review/die_cores.png` viewed. Two241.92x224.64 macros have34.56um north channel and362.88um inter-macro gap; no macro wall/overlap. Native registered chains/turnarounds retained, clock entries exact, actual LEF and timing views paired. Verdict PASS-COND for diagnostic SYNTH/PLACE. Review in kit `results/geom_review/REVIEW.md`, image copied there. Parent own route ceiling M7, actual PLACE_DENSITY .40, original833ps clock and released timing policy unchanged. Plan footprint1745.28x1503.36um, planned27778logic cells; no array replication in this trial. First stop PLACE, then actual-placement review before CTS/GRT/STA. Sign-off, parent integration and token qualification not yet run.

## Next

Collect PLACE admission/result, diagnose any source/placement failure; inspect actual placement, then continue bounded clock/GRT and real-child timing joins. Preserve all originals and failed diagnostics. No blocking owner question.

## Current milestone (supersedes original submitted-job paragraph)

First actual SYNTH completed: 69,585 standard cells + two real xcal macros; macro area108690um2, standard area11657um2. Initial PORT_BIND failed solely because isolated extraction omitted actual native rst_o_0. Original failed run preserved. Added exact original reset.in_sites and keep_outs[1]; retained-netlist checks PASS:12505/12505 pins, FACE_GUARD12482bits/fails{}, REG_FANOUT33627regs/over64=0. All6RTL files unchanged, so resumed from synthesis.

Current PLACE-only job: intel2 client222381, log ~/codex-hbm-parent-1106/place_rstport2.otrun.log; epyc6 unit oth-ubuntu-1429122-1793955200; kit xcal_gen_rstport/q_spb2. Detailed placement reached, zero overlap/site/row/region violations. Resizer585buffers, area130357um2/5%. Never route current source: native lacks planned core/face stations.

Fresh inactive kit_istations probe FAIL L83_i bound3>planned2. Tool processes duplicate bus rows and faults against its own earlier insertion; metadata also stale: L83 native28desc/control bits versus plan99 and cfg_data256 row; L87 native68bits versus cfg_data256 row. HBM owner owns exact native field map and coherent bus/depth/geometry repair; shared prep driver will stop on mandatory station failure. Whole-bus candidates L75 173bits/8stages, L83 28bits/3, L87 68bits/2 still need endpoint geometry and cycle alignment before use. Probe/log xcal_kit_rtl_ist_probe and xcal_ist_probe.log on epyc2.

Fresh inactive kit_rsync probe on isolated plan changes original relayed reset entry/release9 into root sync/release10. Therefore preserve original native reset tree/contract or rebuild only with original full-plan parent context; never blindly regenerate isolated reset. Probe xcal_kit_rtl_reset_probe retained. Original rst_o_0 source remains native registered output.

TOK booked conditional HBM-40: signed child face shell adds+1 rising input/+1 rising output versus raw native child (+2 command/response), negative lockup0, boot reset+2. Native does not yet consume shell; no functional/token closure claim. Shared kit assembly helper verified exact source-byte-sealed two-child parameter contract, replacing private adaptation for future kits.
