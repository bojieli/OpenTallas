# RED lower-cap plan fixed-body review

Personally LOOKED fixed_collision_review.png. PASS for proposed snapped BUFx8
body versus actual final3_place locked taps, self intersections and core bounds.
8269 nodes, actual master .648 x .270 um, actual row/site .054 x .270, exact
ot_ci_place nearest-row/center-site snap. Zero intersections with6954 LOCKED
CORE_WELLTAP cells, zero self intersections, zero outside core. Only the exact649
FIRM red_ck_* old seed instances are removed. The actual final3_place fixed dump
has no FIRM face FFs; the earlier preGPL fixed-face inference does not apply.

Source inputs: epyc2 codex-qc-red-fixed-1520/fixed.tsv and
codex-qc-red-power-1101/model_six/qfd_dv_s5_red2_leaf/sites.txt; Intel2
codex-qc-red-lattice8-kit-1101/slices/qfd_dv_s5_red2_leaf.json. Actual LEF master
BUFx8_ASAP7_75t_R .648x.270 verified by owner from pinned ORFS LEF. check.py
reproduces the numerical test; render.py overlays retained taps and old seeds.

This is no new placement or CTS run. Movable-body legalization, new-clock source
qualification, common frame/root0slew and actual timing remain unqualified.
No clock, source, first-capture or routing waiver is granted.
