Original auto_geom.png and targets.png personally VIEWED 2026-10-29. Candidate adds no cells/cycles, macros unchanged. Payload/ad1 stages now distributed in horizontal/vertical macro corridors; largest point cluster160flops fits in nearby rows. Parent xq/xoq banks remain firm. One existing START source still spans W ring controls and E export (>405um); red line is FAIL structural, exportcopy source under repair. Verdict PASS-COND for placement-only diagnostic; no P&R route/STA or freeze permitted. Postlegalization fullgraph census plus clock assignment remain required. PDN unchanged, routed congestion not measured.

Result-stage successor (2026-10-29): result_bank_estimate.png personally VIEWED.
Fresh GPL/DPL leaves10captures res_row/res_bits to internal held o_row/o_bits,
which GPL moved to E/y640. The complete49-bit held-result family moves to510,717
in the upper crossbar, outside B's lower-right corner. Upstream and downstream
vectors stay short through the central/upper channels. All physical pins/outlines
and RTL cycles stay unchanged. New mapped graph estimate0captures>405,max401.19.
PASS-COND for DPL-only source-hook rebuild; independent actual geometry review and
fresh clock assignment still required before route.

2026-10-29 new source-copy trial: copy_estimate.png personally VIEWED. The new FF sits at E/lower-channel corner700,372 (outside the A3 outline), predecessor route follows the central and lower channels. SF/S0central354,500; S1/raw368,440; originalS2central354,710; existingEfaceFF702,495 remains18um from its unchanged pin. New synthesized graph estimate has0captures>405,max401.19um (not a built gate). Macro/PG/island geometry unchanged. PASS-COND for fresh global placement only; post-legalization census/independent review and fresh clock assignment remain required before route.
