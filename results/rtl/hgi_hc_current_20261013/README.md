Current SYS HC production measurement

The existing source-pinned c4 SYS bench includes the production DeepSeek D5120 scalar HC_MIX_POST case (case 15). It measures 540 record-to-retirement cycles against the unchanged 540-cycle budget, ratio 1.000. No new build or vectors were needed. Full exactness and MP/POST/XL negative controls remain pending in the existing closure job; this record is provisional and does not assert qualification or physical closure.

The source manifest verifies the runtime source files against commit 550082537. The measurement covers the scalar 24-mix tail (sigmoid/exp/Sinkhorn), not residual vector FUSED.HC_POST, full HC_MIX, or HC_MIX_ROWS.
