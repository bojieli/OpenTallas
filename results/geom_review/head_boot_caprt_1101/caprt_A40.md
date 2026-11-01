# cap_rt A40 CTS independent review — 2026-11-01

Picture viewed: `/home/ubuntu/coord/tmp/caprt1101/A40_cts.png` (S81 cap_rtA40 CTS).

PASS-COND for GRT prototype only. One central horizontal macro has continuous logic channels above/below and passages at both ends. Cell density is distributed through the two main bands rather than a dense macro-edge wall; face pins run across N/S edges and boundary registers are close to their pins. The nearest local clock driver is within 19.82 um of its worst sink despite the 248.96-um distance to the top root. No visual macro overlap or isolated cell island; the open strip below the macro remains wide enough for continuation. Supplied r2r census has maximum232.58um and no over-reach paths; supplied pin-register p90 is7.76um/max53.09um, fill0.3089, H/V channel demand0.511/0.283 and maximum column demand0.545. These numerical metrics are from the proposing lane, not independently recomputed.

GRT has NOT RUN. Its existing AUTOFAIL/NA grt verdict stays intact. Proceed to actual GRT and assess congestion, timing and PDN there; this picture does not establish routed timing, DRC, PDN continuity or SIGNED status.
