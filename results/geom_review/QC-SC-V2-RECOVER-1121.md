# QC sle_sc_v2 attempt 2 recovery review
- Viewed the exact retained placement image `epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V1/items/sle_sc_v2/attempt_2/geom/auto_geom.png`. Central macro has channels around both sides and no visible pin wall across the outline. Dense West faces and the 1.29 mm far clock-sink estimate need a real CTS read; PDN evidence comes from the retained completed floorplan.
- The failed TT stop used the pre-CTS propagated-clock probe from before `eda19506a55`. Reuse the placement only in a fresh copy with the corrected pre-CTS measurement. Verdict: CTS-only diagnostic to measure the clock issue; do not route until looking at the corrected CTS evidence.

