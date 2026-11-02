# NW SU31 FT geometry

PASS-COND for the eight normal FT slots. Full kit remains BLOCKED by clock density/source/reset/parent joins; no P&R/STA dispatched.

Viewed NW_review.png: actual allocated FF bodies occupy the top, middle, central, left and right streets around all nine canonical obstacles. Data pin order is unchanged. L5 has eight native FF stages; all other counts stay unchanged. Drawn station chords indicate logical register-to-register connections, not physical routes; wide-bus layer/channel and clock/PDN/timing qualification remains with the coherent parent event. Red clk_t9 and clk_t14 are genuine current clock-entry body conflicts.

Exact full-body row audit covers46540 allocated internal FFs, with zero macro-body/grid/frame/global-FT overlap errors. Canonical check_ft_macro_sites independently has zero findings. The normal FT constructor gives max405.000um internal hops. All25 neighbor interfaces /26013 bit interfaces have zero pin mismatches and zero hops>405um; max404.921um. Input boundary FFs and neighbors are canonical pin-capture models, not placed physical capture sign-off.

The initial L5 local-proxy run hid25 actual outgoing seams up to405.945um; that FAIL is preserved. The final job repaired only those25 chains against exact native peer-capture points. All current four output endpoints have zero tangent difference from their own source pin, so their direct distance exactly equals the native source-pin + seam + peer-capture sum for every in-frame FF. The final audit uses the canonical SUM, not the helper proxy.

L34's389um conservative seed failed at bit940. Exact full-body occupied-row path allocation succeeds at the existing six-stage count using676 per-bit fallbacks; no added cycle/count waiver. L35 six-stage and L6b four-stage banks then passed without joint fallbacks. All old and newly allocated banks were reserved together; failures rolled back atomically. Centroid regs_um matches every actual bit-site bank.

Only authorized L5 seven-to-eight count event adds2726FF and1cycle /833ps per traversal; native ot_dp_st old7+golden1 vs new8 miter and mutant PASS on token branch a932bbf1a. Native L5 natural lane latency9→10, NE stays9. No global traversal count/token rate or installed programme dates invented. Soft FF lower bound64503 needs at least44 taps at1500/tap; physical density/reset-controls may require more. Existing20 taps are insufficient. Parent clock owner now has this exact type.

Old retained FT banks still have conservative4.32um halo-contact diagnostics, preserved in NW_native_audit.json; actual required canonical macro BODY gate is zero. New allocated banks use all9 actual obstacles with4.32um grow. No obstacle, limit, stage count or clock changed to obtain this FT-only result.
