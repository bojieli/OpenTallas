# S81 J9 KV512 premask v9 actual placement — BAD

2026-11-23 15:33 PST. Exact E7 placed ODB f4388449b14b under `fam-s81-slice-r6/xga/kv512_premask_v9_0942`. I viewed `geom/auto_geom.png` 640f1ece1aa1 and the exact native `run/layout_review/place/density.png` 9871abcc40bc. Placement unit 935215 completed. Static readback unit 1847026 explicitly disabled GRT and completed with the physical FAIL verdict.

A nearly continuous lower macro bank splits the tile behind the actual west/central throat. Data and feed lanes crowd around its left and lower flanks, with 104.5% local peak density, while the upper-east area is almost empty. Pin-register p90/max is 95.19/271.95 µm with two unregistered pins. Actual worst flop reach is 1,408.81 µm. There are 1,815 collapsed relay stages and 84 groups that need stations. The scan counts 12,546 bits beyond 405 µm and 3,322 beyond 580 µm. Clock tap clk_t37 carries 16,631 sinks.

The exact long XG groups include 1,075 bits of `u_r.dl_w` to XR at 636 µm, 1,076 XR-to-`u_r.ci` bits at 756 µm, and 276 XG `u_r.vo` bits to `xtier_o0` at 1,201 µm. Preserve the existing bit-exact premask source proof. Require a changed bank/XGA/leaf-forwarding partition with locally seated added stations and a measured lower-center clock split, followed by fresh exact visual review. No route or STA is released for this form.
