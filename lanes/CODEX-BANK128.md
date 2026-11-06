# CODEX bank128 continuation — 2026-11-06

CODEX took over bank128 SRAM write-face work on `codex/hbm-bank128-wface-1106`, own epyc6 tree `/srv/opentallas-scratch2/claude/wt/codex-hbm-bank128-wface-1106`. Current tip `e88b457a38` pushed to intel2 hub; source/kit commit `fcf7190a4f`.

## CODEX notes

Implemented default-off `OT_HC128_WFACE`: write_data[511:0], write_addr[9:0], weight_we0, weight_we1, x_write are one 525-bit +1-edge programming cohort. Read/arithmetic latency unchanged. Actual first-module/SRAM-cut lockstep passed27000checks/3000cycles with reset and RAW collisions; data, enable and address mutants all caught. Arithmetic leaves are unchanged and stubbed in this mechanism proof; this is not full projection qualification. TOK HBM-37 and hbm_projection own explicit +1 last-write/first-read/go guard; native projection compiler lowering was previously absent.

Both new physical forms use actual config util0.40, M6, single-root CTS, no density taps. A keeps original RTL; B enables the write stage and guides its registers beside north write pins. Review found inherited X-to-W0 halo gap1.032um, so X moved down11.76um for both candidates, giving12.792um clear channels each side. Draft FAIL image retained; revised image viewed PASS-COND under `results/geom_review/codex_bank128_wface_1106`. Parent M6 obstruction/resource reservation, final physical sign-off/LEC and compiler composition remain mandatory before adoption.

Jobs: all three ADMITTED on intel2 (ot-run logical `localhost`),48GB16threads each. Canon A client2891638/unit`oth-ubuntu-2895666-1793952331`, canon B client2891639/unit`oth-ubuntu-2895661-1793952331`; logs `/home/ubuntu/coord/tmp/codex-bank128-launch/{A3,B3}.log`. Weight_E B client2873269/unit`oth-ubuntu-2876320-1793952287`, log `weightE_B.log`. Kits mirrored at `/srv/opentallas-scratch2/claude/codex-bank128-wface/kits/ot_hbm_hc_bank128_pair_core_7d149b37532c-_shallow_vA`, `...7d149b37532c-_wface_vB`, `...9bf80cdae38d-_wface_vB`. Collect intel2 actual run data, not source epyc6 copies. Measured prior DRT17.87GiB plus concurrent LEC justifies48GB. My original unstarted clients2640829/30 and2679786/87 were canceled by exactPID to repair stale historical input metadata and stage inputs on admitted hub; no progressing jobs were restarted.

Weight_E B generated PASS hashb549fad338678913: actual512data pins remain north,13write-address/enable pins east. Separate disjoint guides follow those faces; actual image viewed PASS-COND. Canon B hashba3cba7395e1a9f7, canon A7dfd5bc2be21db10.

Legacy collection: old weight_E vB now terminal NOT SIGNED TT-272.82/23endpoints, FF-29.33/348, slew647/320, DRC5; direct-write/clock design failures handled by new forms. Canon vC is still DRT with50violations. All old runs and failures preserved.

Next: collect admission/synthesis/LEC, inspect actual placement and CTS, then routed sign-off; weight_E safe form is also running; compare first routed winner then re-sign on released flow with current parent context. All inherited vA/vB/vC/ECO jobs preserved. No new OWNER? item.
