# QC six C1p HCLEC probe placements

Viewed exact layout and density PNGs for each retained Intel1 place-only kit. Five HC0 variants place most compute in a south-central lobe (roughly x200–420 and y30–440 µm), with a sparse north region, a narrow loaded north receive strip and a detached east cluster around x560–600/y120–140 µm. HC3 converges into a narrower lower-middle lobe and leaves its upper outline similarly open. No hard macro wall appears in these placement views. The CCU status and late data legs account for distinct failures.

| Place probe | Fill / empty | Pin p90 / max µm | Register max µm / count above 405 | Dominant native path |
| --- | --- | --- | --- | --- |
| East HC0 cl05696ed1 | 12.55% / 67.14% | 38.40 / 267.67 | 536.38 / 83 | XH0 lqp to n_q |
| East HC0 pv48712631 | 12.08% / 67.45% | 38.40 / 267.67 | 538.87 / 133 | XL0 q_bad to x_ctl_o |
| East HC0 pvcaa93304 | 12.05% / 67.57% | 38.40 / 267.67 | 556.74 / 144 | XL0 q_bad to x_ctl_o |
| West HC0 pvd0aa3ddc | 11.93% / 67.61% | 38.35 / 267.67 | 527.20 / 86 | XL0 q_bad to x_ctl_o |
| West HC0 pvde134a90 | 12.07% / 67.29% | 38.38 / 267.67 | 527.53 / 153 | XH0 lqp to n_q |
| West HC3 pvcca9ff41 | 10.43% / 73.30% | 8.53 / 56.72 | 702.97 / 570 | XH3 n_d to cw_n3, 515-bit group |

HC0 widths and START geometry are already being repaired in the separate HC0-GROW row. The native image-linked readback isolates the q_bad east output cohort and XH3 cw_n3 path for independent repair. HC3 also shows ten collapsed relays and one unregistered cland_rstart input. Preserve the existing HC0/HC3 release and equivalence holds.

Exact image source is Intel1 at the kits listed in the matching GEOM VERDICT rows, under each kit's run/layout_review/place directory. Native read-only OpenDB replay and individual auto_geom plots are in the same QC-HCLEC-PROBE directory under visual_1126. All are placement-only findings. No route clearance.
