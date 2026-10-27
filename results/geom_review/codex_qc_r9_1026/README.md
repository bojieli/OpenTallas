QC R9 clock-only structural trial, 2026-10-26 20:09 PDT

Viewed review.png before route. PASS-COND for this tree/stack trial: the equal logical H-tree follows the existing channels; 48 westward buffers mirror so output bars face loads. All 266 lower-left cell origins are plan-declared, including the three trunk repeaters. The 170 R8 row moves put the full cell body inside exactly one partition; the central row is below the ctl/stm seam. Per-type abstract windows are regenerated as the union over instances. Signal plan/netlist and data/reset cycles unchanged.

The track router moved some MY pin risers onto another legal track: maximum physical riser 2.325 um, so abstract-window margin is 2.6 um. This trial checks the actual routed DRC rather than declaring the proposal's 1.02-um riser estimate a gate. M8/M9 clock/shield census is clean by the existing build gate. PDN grid unchanged; no residual delay padding/trims.

16 focused R7/R8/R9 tests PASS. Route/RCX and AOCV NOT RUN at this review. No SIGNED claim, no die GRT or mesh gate claim.

Full die_trial kit generation stopped on the old candidate plan's unresolved core reset pin table. For the clock-only vehicle, existing R7 base kit grt scaffolding is copied to a new directory and overlaid with the successfully regenerated abstracts/island windows, then die_infra clockkit strips all signal nets. No reset RTL is used by this diagnostic clock-only vehicle.
