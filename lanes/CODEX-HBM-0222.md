# CODEX HBM takeover 2026-11-08 02:22 PST

## Current step
Cover all HBM scopes while Claude is limited. Latest counter: 69/105 hard cores, 0/81 types (229 across all dies); no die-level gate credit asserted. Collect healthy jobs before fixes. No merges, tags, plan-of-record edits, or deletion-chain changes.

## Coverage and next step
- KCLS / KITPARAM / REACH: `/root/hbm/kcls`, lane CODEX-HBM-KCLS-0222.md. PHY split parent bound monolithically + unrooted macro path blocks NE_io, NW_io, q_spb0 (+physical_v1), vsN0. Hold relaunch until structural bind fix. KITPARAM v2 a2eb941596 approved READY, collect unfinished q_b110 dry; build from branch allowed. REACH 178842a72a pending tests/dry results, no adoption.
- HARD-5 / HARD-4 / UNTRIED: `/root/hbm/hard`, lane CODEX-HBM-HARD-0222.md. intel1 /srv/opentallas-scratch2/claude/hbm-hard-5/kits/{rootctl_vD,gqi_vLF2,wsw_H7,opsb_PS2c}; rootctl port hold repair, gqi detailed place, H7 GRT setup repaired positive/hold repairing, PS2c GRT. Collect q3bc_vC2, OPSG P1b and E2 opsb output vP1. No duplicate launch.
- OPEN: `/root/hbm/open`, lane CODEX-HBM-OPEN-0222.md. qout/s3 one strict ECO, wbq_root_g0/g1, full_x, svgr_top/own, six vecd4ae family. s3 strict ECO exhausted, no second iteration; last internal -0.39 ps is clock leaf class -> redesign.
- Q2NF / RESTJ: `/root/hbm/q2nf`, lane CODEX-HBM-Q2NF-0222.md. q2nf_rest vA1 replica LEC UNPROVEN, 55368 proved / 345 differs / 6 undecided at intel1 die-hbm-89/q2nf/lec_rm. Diagnose unmatched anonymous state, no P&R until EQ. RESTJ JOINED3 not found by predecessor; locate actual latest checkpoint and resume once identified.
- HBM die/type integration / unclaimed cores / architecture: `/root/hbm` here. Existing wave/type class batch coordinated through root wave lead. PEV exp_x/qcore_r13 and OPSA rest events already counted; no rebuild for those credited cores. q_b013 PDN full-width FT strap-window class fix is merged; wave owns one fixed batch. Remaining child waits stay explicit.

## CODEX notes
Takeover collection in progress. Every failed form retains its failed record; new builds require measured structural change and actual visual review. PIN CYCLES priced in compiler/token, TT setup/FF hold at 833 ps unchanged.

## CODEX notes — 2026-11-08 02:33 PST
- s3 vG structural PLACE pilot launched E4 `codex-hbm-open-0222/s3_vG`, branch `codex/hbm-open-s3-cluster-1108@f93a5cc249`: 44 regs moved from 8um E macro strip to N logic bay, no RTL/cycle/POR change.
- n4 local-pad-select PLACE pilot launched E4 `codex-hbm-stale-0222/n4_local_vA`, branch `codex/hbm-n4-pb-local-0222@603b03287ac`: same-edge copies feed <=8 mux inputs, source invariant and mutant passed. No route until pilot image + LEC.
- PHY split class fix branch `codex/hbm-phy-0222@2fa0a31ee4`: exact physical_inst projection + private p37 asbuilt candidate, strict-bind/preflight next. No POR activation.
- Reach mixed native station receipt bug fixed `codex/hbm-reach-receipt-1108@a4143b6aa7`; native macro rows no longer incorrectly demand `stations`; actual q_su11 receipt accepted, 4 stations/0 cycles changed, faithful kit-rtl pilot admitted E4.
- q2nf final AIG diagnostic proved all 1021 replica hypotheses in one late round; missing 3 gate representatives were early-cap exhaustion, not demonstrated functional divergence. Full own LEC next, six codec solver limits remain.
- RESTJ JOINED3 FOUND intel1 `die-hbm-89/restj/build_JOINED3/kits/ot_hgi_sfu_split3_ctl_rest_1c_f057777f78e4-JOINED3D89`: NOT SIGNED TT-58.99/83, FF-179.07/5947 (157 internal, -14.44), DRV0, own LEC EQ. Structural drain-sector local decode targeted; no ECO.
- q_spb1 new routed FAIL (a722130c318e): TT+24.39, 232 non-port FF hold -56.27, TT slew1423, DRC0. Actual density/floorplan images viewed at `/tmp/codex-hbm-spb1-0222/`: 1745x1503um FT-only sparse grid, no macros; FT QN/buffer/inverter wires have582ps slew at s0 inverters. One read-only FF path probe admitted intel1 unit `oth-ubuntu-3884556-1794133702`; structural local polarity-cell grouping is being prepared, no ECO/retry.
- hnx_rp3h_xs a9 owed DPL fix pilot owned root gaps lane; no duplicate. Healthy topk/programme_store/glueNW GRT kept.
