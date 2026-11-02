VSW cvB bounded hold repair review, 2026-11-01 21:10 PST

PASS-COND one normal route-retaining hold12 ECO. Viewed actual_final.png from
actual final6_final.odb, native read-only dump unit3802985-1793595501 exit0.
Actual two SRAMs have continuous halos and a clear central horizontal channel;
logic and buffers occupy W,N,S regions with no macro wall or sliver collapse.
N/S face pin-register strips remain aligned, local clock/repair cells distributed.
Current full connected Manhattan census including both actual typed SRAM Liberty
models: r2r260.66um,12871captures,0>405,0loops,0missingmodels. Actual source DRC0,
antenna0,DRV0, setupTT+54.47; only FF hold−7.06/32 endpoints fails.

Cause: worst rst_n→u_rr.sync_q0 removal requires312.23ps vs actual305.17;
worst register data path has only one AOI,293.13arrival vs298.60required (−5.47).
This is short data/reset delivery against actual propagated clocks, not a long
unstationed path. Repair delayed data endpoints under normal hold12 target,
retain original clock wires, source RTL, interface, macro placement and period.
No clock waiver or reset exception. No added cycle/model change.

Use existing shared PRD route-retaining m12, OT_HOLD_ALLOW_SETUP=0,
OT_PRD_TARGETED=1, at most1pass then fail/diagnose. Clock wire freeze is blocking;
actual DRC/antenna/RCX + fresh current051 signoff/ownroutedEQ required. ROOTclaim
approved; remaining_lanes confirmed SS20 never launched a VSW repair. Original
cvA finish and failed cvB remain untouched. This is prototype only: original
source-generation provenance limits remain and no parent view adoption is claimed.

Runtime own Intel1 codex-s81-vsw-2058/m12; helper snapshot maina0f8f0ad6,
current051 gate bundle copied from own sealed L2 source. Runner run_vsw_prd.sh.
