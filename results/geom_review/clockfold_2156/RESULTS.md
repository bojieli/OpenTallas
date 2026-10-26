Physical clock fold/depth experiments, 2026-10-25

Opt-in source dbde0a022 builds actual last-mile out/back waypoints and disables invisible STA padding. Full QC plan54a1aeb5: fold0 has73771 clock cells,10.094m actual wire, stage counts83..93 because core keepout slides add repeaters. Model STA FAIL: related-pair501.761/416.134ps TT/FF, insertion4881.22..5712.05 /3869.68..4564.86ps, slew73.84/69.44ps. The actual legalized geometry has26.41..32.08mm root-to-tap paths. This full candidate was NOT routed or adopted.

normalize_clock_depth.py then inserted8024 physical BUFx24 cells on distinct free native sites (area3509.6976µm², max island7.857µm), making every active root-to-tap path93 stages. No data cycle or hidden wire was added. Model improves pair to418.270/352.058ps but still FAILS; insertion5027.81..5772.90 /3991.27..4621.74ps. Not routed/adopted. Next structural correction is fixed-length per-level contours with core-free waypoints, preserving both clock depth and actual wire geometry; do not re-enable invisible SPEF pads.

The separate actual local pair mechanism in ../clock_pair_2156 PASSES. Full-die electrical closure remains open.
