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
