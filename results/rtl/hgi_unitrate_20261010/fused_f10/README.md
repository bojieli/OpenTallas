F10 (FUSED HC_PRE_NORM d 5,120 wrong values on both SU widths), hgi-unitrate 2026-10-10.
Root cause: HC_PRE_NORM's micro-sequence uses 2 d + 2 scratch words from cfg_scratch (G d, S, S2, the mixed x d); the e2e
strapped FUSED_SCRATCH = 256,064, so at d 5,120 the scratch ran to 266,306 > 262,144 (VM size): the 18-bit VM addresses
wrapped and x overwrote live VM words [0, 4,162).  Not the lmem, not WIDE.  (The unit bench's own d 5,120 vector also had
a layout overlap: pre over h[3] - fixed.)
Fix: ot_hgi_fused_record faults (fail closed) when cfg_scratch + the record's scratch need exceeds VM or SCR_WORDS.
Gate (tb_hgi_fused_unit, UN 64 / UM 16, d's lane-local lmem): run_b64.log all cases PASS incl. d 5,120 HC_PRE_NORM /
HC_POST; run_scrw.log (SCR_WORDS 9,000): the d 5,120 HC_PRE_NORM record (needs 10,242) FAULTS in 13 cycles, d <= 4,096 pass.
Compiler / e2e: reserve >= 2 d + 2 nseg words for the FUSED scratch (DS: 10,248) - sub-agent e.
