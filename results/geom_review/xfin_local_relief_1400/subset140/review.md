# Smaller140-cell DPL proposal

R3 used strict native3um displacement (55sites/11rows), but native check_placement refused one remaining padding violation on wire29087. Runtime2.36s/max displacement2.6um; no accepted candidate, routing or timing. Original failedODB stays read-only.

Baseline wire29087 is BUFx12f at100.170/42.660..101.142/42.930um. Enumerating baseline-row slots within4.32um with all unselected instances fixed finds zero slots with extra1site/side padding. With no padding, only its original slot remains. The previous wider R2 search also exceeded the independent4.32um audit at this same cell; R1/R2/R3 failures are retained.

The smaller proposal holds wire29087 at its original location and omits its added padding. Only the remaining140 already-reviewed targets may move; every other instance/port/FF/clock cell remains fixed, source/nets/masters/outline/pins/cycles unchanged. Native search remains3um; absolute audit remains4.32um per axis. No coverage or capacity PASS is claimed.

Codex personally LOOKED subset140/proposal.png: the purpleX marks the newly held cell; orange arrows otherwise unchanged. Same sparse interior adjustments, no repack, new cell or clock load. This subset has not executed. ROOT review is requested for DPL-only4GB/2CPU. No GRT/STA/DRT or16-type adoption is authorized here.
