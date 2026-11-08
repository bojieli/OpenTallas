# Root SU1 numerical transport — active 15:51 takeover

Ownership transferred explicitly from watch_qc to root. Own I1 source /srv/opentallas-scratch2/claude/codex-qc-su1-numeric-1551, branch codex/qc-su1-numeric-1551, exact66 base, latest c44625a67ac. Borrowed shared Git objects protected by m5; no hub source/compute staging.

Actual captured lrly + safe2(MA3/EXTRA0/KV_WR_PIPE1) + three real SFUs, 760 inputs/248 outputs. Original captured files unchanged. Private core has original EXTRA0 branch and prior private ML12 mechanism when EXTRA4. Verilator-only removal of44 redundant scalar[0] selects changes no values. Source changes are diagnostic only, no signed module/default/interface/POR/P&R replacement.

Run2 actual unit259541-1794096938, source de09e7fc10e, result I1 sibling -run2/run.log; committed result_scope/run2_result under tools/qwen_dv/su1_numeric_1551. Correct WROM4 compensation: zero request differences at+4, zero result/write differences at+9;288 result words across5classes,64VM/96KV writes. WROM0/WROM2/unchangedML8 controls catch48/24/392 data differences.64-edge warm reset has zero output leaks; comparison flush200edges explicitly retained.

Run4 unit810384-1794097872, source7cdc0c2cac8, result sibling -run4/run.log. Actual NaN operands in requested memories and independent global BF16 broadcast produce40 real scheduled fault pulses. Correct candidate still zero request/data differences; fault uniquely matches+9edges (all other lag0..16 nonzero, lag8/10 each80 differences), zero warm leaks. Baseline BYP golden had zero coverage because DST0 means no write. Run5 corrects to actual VM DST1 for that independent golden; latest source c44625a67ac, controller intel2 codex-su1-numeric-1551-r5.service dispatches I1 normal24GB4T/disk8, no-spill. No passing independent-baseline result claimed yet.

Failures preserved: run1 frontend rejected redundant captured scalar selects, before simulation; run3 frontend syntax error from adjacent generated end/if tokens, before simulation; both fixed only in private test vehicle. Each run output distinct, no verdict overwritten.

Conditional calendar: external VM1/CROM4 reply and independently advancing tagged WROM are diagnostic, not qualified production provider timing. Actual captured suvm drives WROM from lane0 request ONLY and puts WROM in one-edge gbr; lane4 does not export its WROM request. Never derive shared WROM from delayed candidate request. Production join needs actual provider implementation/calendar. Direct rst_n wiring of captured head preserved; h_rst_n is not silently substituted.

Model: command/answer ingress2, four request egress2, other egress3, selective WROM4. Added transport state3188bits per lane/12752four lanes incl valid bits, plus prior ML12~565/head (~2260), reset/clock implementation overhead separate. Request+4/result+9/scheduled-fault+9 supported only under measured diagnostic cohort. No uniform unrelated external-fault shift claimed.

NEXT: collect run5 independent golden. If it fails, diagnose actual full-child/provider baseline instead of claiming whole-child EQ. Then source/provider join and implementation model before a physical form. No whole-die simulation or new source adoption.
