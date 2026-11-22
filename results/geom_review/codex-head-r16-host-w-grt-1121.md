# HEAD r16 west host GRT review · 2026-11-21 16:37 PST

Viewed exact failed GRT density and congestion images for AP `83022e003308` at `epyc9:/srv/opentallas-scratch2/claude/ot-jobs/hd_host_w-route-renewed-glider-2142210-1795256884/work/run/layout_review/grt/`. Peak utilization 103%, 7,139 gcells over 90%, peak local density 0.859 along the north shelf. Inter-row congestion is visible between the center and eastern SRAM columns. The run stopped structurally after GRT-0116, with first-attempt per-layer overflow 160 and existing bounded recovery threshold 500.

Iteration 20's detailed report has 193 overflow units, 184 within x400–480 and y300–320 µm, chiefly lane local payload and serializer data. The final detailed report narrowed to 7 capacity-zero markers in six tap groups: `clk_t6/18/19/27/47/60`. These sit adjacent to the narrow M7 tap escapes at reserved sites. Separately, the canonical west-face `coll_o0` beat bank still has signed-off-view locality work in progress.

Verdict structural stop. Recheck local M7 escape tracks against the actual reserved-site geometry and current gcell capacity tool once a locality-corrected candidate exists.
