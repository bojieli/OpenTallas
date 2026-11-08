# CODEX S81 RCK takeover 2026-11-08 02:22 PST

CODEX took over: serdes__t16 conservative split on codex/s81-rck-reform-0222.

## CODEX notes

Collected S81-RCK-11 unposted regrouping RTL and preserved it on own branch codex/s81-rck-reform-0222@23c0d6de65 (pushed to hub). Own work: intel1:/srv/opentallas-scratch2/claude/codex-s81-rck-0222/work. No changes to the Claude tree.

PASS inherited lockstep 12000 checks, errors 0; SHORT and TXSKEW mutants caught with 11105 and 11632 mismatches respectively. Evidence results/s81_rck_11_reform_1108. The cut relocates existing registers: ZERO new pin cycles relative to vJ; vJ's +1 wclk RM input, +2 recovered decoder, and +1 cland ready/fault remain.

FAIL vJ placement remains preserved: WNS -610 ps / 3894 endpoints at placement RC. Cause control broadcasts across a 2886x1227 outline with only 1.4% fill. Viewed intel1:s81-rck-10/probe/vJ_layout.png (local /tmp/codex-rck0222/vJ_layout.png). SMELLS: control fanout across mm, multiple logic clouds, wide empty regions, pin column landings remote from their driver. No retry or route of vJ.

RCK-11 hierarchical synth estimates RX-SYN ~125k cells, RX-BACK ~68k, TX ~72k, remaining parent ~100k. RX-SYN 215x190, RX-BACK 690x280, TX 180x155 um are initial model outlines; actual pin/macro capacity must be reviewed before PLACE. Rate matcher and coll/ft landings remain in the multi-clock parent; no unsupported multi-root core kit is assumed.

Running inherited: intel1 dpkit-serdes__t16-3220946-lec (vJ in-kit LEC, alive at collection, no final lec.json). Other old RCK containers were already stopped by RCK-11 per ruling, not stopped by Codex.

Next: make compact TX pilot spec/pins and draft plan only in own branch, render and review, generate its core kit, admitted PLACE through ot-run. Then RX-SYN and RX-BACK. Plan-of-record changes and merging remain held for Claude.

## 2026-11-08 02:36 PST

TX pilot is actually admitted: intel1 unit oth-ubuntu-4015988-1794133927, container klegacy-ot_s81_rck_tx_vA-4017019, PLACE-only, 32GB/8T. Kit /srv/opentallas-scratch2/claude/codex-s81-rck-0222/kits/ot_s81_rck_tx_vA. Log hub /home/ubuntu/codex-rck-0222-logs/tx_place.otrun.log. Pre-PLACE rendered pin contract and reviewed at results/geom_review/codex_rck_tx_0222. Source/spec commit d5ec58ab83, pushed hub. Synth currently ABC. A first background shell failed to persist and admitted nothing; corrected via a persistent exec session, no duplicate job. Local ot-run was stale (only 3 hosts); intel1 explicit target admitted correctly. Use canonical intel2 ot-run for subsequent launches.

RX-SYN compact pilot generated and pre-PLACE pin image viewed: 216x190.08um, 1453 pins, M5 at 4-track step / 25%, 555 N inputs and 897 S outputs, N clock midpoint with 4um signal gap. No macros; estimated 125k cells/39% fill. Draft source/spec/pins/review 4fa53f4832 pushed hub. Kit /srv/opentallas-scratch2/claude/codex-s81-rck-0222/kits/ot_s81_rck_rxs_vA exists but NOT launched: wait for TX PLACE pilot and actual review first.

Inherited vJ LEC still has no final result; its hyp0_failed.txt alone is not final LEC FAIL. Keep it running to its terminal result. Broader t1..t15 wave belongs to the S81 types agent; this lane owns private t16 only.

## Failure fallback analysis

Read the actual RiBM RTL while TX synth runs: NBM=3 has no budget for a two-cycle recurrence (30 iterations, a new frame every10cycles, each unit reloaded every30cycles). Therefore the earlier suggestion "2-cycle step if NBM=3 permits" is infeasible at production throughput. If compact RX-SYN still fails its recurrence, the correct structural form needs NBM=6, 60-cycle RiBM service, +30 recovered cycles added to k_*/data delay, and separate small BM hard cores to keep each <=150k cells; it needs exact lockstep against a correspondingly delayed reference and compiler/model pricing. No such RTL change has been made, and no two-cycle recurrence has been assumed in the present pilot.

## 2026-11-08 02:54 PST

TX vA FAIL_PREFLOOR: RAW face guard 1058/1059; only failure fault sticky flop self-feedback. RTL lint PASS; synth71050cells/11137.65um2, matching72k/39% estimate. No placement spent. failed_vA raw verdict/stat/lint preserved in branch results.

Fixed structurally, ZERO cycles: optional encoder PIN_FAULT=1 computes a separate kept face flop from the sticky NEXT state on the same edge; original sticky state remains internal. ot_keep_regs.tcl explicitly keeps both drivers before opt_merge. Small encoder lockstep with real valid gaps/warm reset:1994checks/0errors/7faultedges. Delay mutant caught4 errors; no-reset mutant caught60. Source/evidence332b1e8039, hub push in progress. TX vB new kit (separate from vA) generated and submitted through canonical intel2 ot-run,32GB/8T,PLACE-only. Log /home/ubuntu/codex-rck-0222-logs/tx_vB_place.otrun.log. No outer time limit on the heavy command.

RX-BACK draft725.76x280.8 generated,3 native inherited macros,1461pins,20.088/21.6um gaps,99.372um clear north routing band,M6signal/PG grant. Native dchn has interior M5clock pin; review_v2 explicitly requires inspecting its leaf access. New aligned draft slots: RXS1296,483.84; RXB1071.36,181.44; TX2574.72,466.56. RXS/RXB x_q faces align, k_* offset<=4um around clock. TX moved near E landing; existing TXL relay rows still span the long PMA bus. Parent draft HOLD: taps inside cores, all relay placement, strict bind/clock/reach/count still required. No POR edit.

## 2026-11-08 02:56 PST

TX vB actually admitted intel1 unit oth-ubuntu-602540-1794135291. Pinned source332b1e8039 now pushed hub. Core layout/pins/clock unchanged; only dedicated same-edge fault face fixes vA RAW FAIL. Canonical intel2 ot-run used.

RX-SYN class prevention in own tree: x_q=x1 also drives syndrome logic, so add optional PIN_X=1 dedicated same-edge x0->face copy (original x1 retained for internal uses); relocate the ALREADY-EXISTING outer lock/n_relock pads inside RX-SYN. This preserves every whole-column cycle while giving each core output its own launch flop. Full-column vs vJ lockstep + XFACE_DELAY/LKFACE_SHORT mutants admitted through canonical intel2 ot-run as intel1 unit oth-ubuntu-644685-1794135378,16GB/8T. Logs results/s81_rck_11_reform_1108/column_faces and /home/ubuntu/codex-rck-0222-logs/column_faces.otrun.log. Those RX-SYN source edits are not yet committed/pilot-built: proof running. No CTS/route launch.
