# QC cbx_q10 stage-SDC timing diagnostic

I inspected the retained V2 cbx_q10 placed layout. Four hard macros surround a clear horizontal and vertical channel. The worst measured path is a local latch-to-macro leg at a channel edge. The detailed placement report measures 1.49 ps of wire on that leg. The large timing change on reload comes from the clock model.

Exact 3_place.odb replay with its original written 3_place.sdc measures TT −380.66 ps against −659.86 ps with the golden constraint.sdc in the same pre-CTS observer. The endpoint, wire, clock period and uncertainties agree between the two reads. The capture ideal latency is −568.10 ps in the actual stage, −1122.10 ps with the prematurely applied planned window. The corrected figure remains a placement advisory; post-CTS and route timing use the propagated physical clocks.

Reviewed image: epyc2, /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V2/items/cbx_q10__cl89936551_h/gen/cbx_q10__cl89936551_h/run/layout_review/place/layout.png. Detailed replay references are intel2 /srv/opentallas-scratch2/claude/fam-qc-cb-r2/v2_cf0b_{exact,checkpoint}_reload.log.

Verdict: PASS for an informational replay of the placed checkpoint with its matching stage constraints. 
