# TOPK5 independent arithmetic bank0

Real32-bin arithmetic leaf, not bound into releasequarter. Eight leaves per histogram (hc/hf =>16quarter). Every bin updates in parallel;352counterbits per separately hardened bank. Runtime group-query becomes two constant slices masked by kept registered select. See results/arch/s81_topk5_1020/partition_model.json for full port/cut/area/edge sizing.

Mapped native pre-gate (actual ot_keep_regs hook):9458cells,1366.10226um2 std,509.80428um2 seq; ALLdrivers max32,OVER32=0,unknownmaster0,rawreset22. Positive miter1159checks PASS vs immutable256-bin arithmetic (saturation/clear/input stalls/random groups); query/clear mutants rejected at45/606. TestV5.050.

Checklist:
1 PASS source every input/output registered; reset source2sync+1regional stage,3startupedges priced.
2 PASS design:64.8x43.2 singlebank maxL1 geometricoutline108um<405; actual native measurement required afterplacement.
3 PASS native pre-gate:ALLdrivers max32 inclreset; explicit20resetregions, raw22, binleaf24. Kept copies actualmapped.
4 PASS structural budget: same constant add/popcount stages as oldhist; no extra combinational depth. Gate verifies timing.
5 PASS actual bank352counterbits, all fixed parallel updates; no generic runtime memory or large delay line. Wholehist cannot be presented as closed until16banks hardened/composed.
6 PASS model measured48.8pct util,aspect1.5,no macros/obstacles,fullstd band,pin faces below6/um.
7 PENDING measured:singlelocal root,source3edge reset relay,hold0.03; require actual TT/FFspread<=80.
8 PASS bank arithmetic static; gselquery+1,busy+1,resetstartup+3 explicitly charged. Parent multicast/collect edges unpriced/unbound until real layout+compiler update.

No REVIEW or submit before actualPNG and fresh native audit. Native bank B0 does not qualify the other7BANKparameters or the quarter by itself.
