# HEAD r16 mesh GRT recovery review · 2026-11-21 16:04 PST

In inherited AP job `1bda1a004005`, reviewed the exact first GRT attempt's congestion and density images under `epyc2:/srv/opentallas-scratch2/claude/ot-jobs/hd_mesh-route-dear-crayfish-2377242-1795257094/work/run/layout_review/grt/{congestion,density}.png`. The 30-iteration attempt dropped NDR on `clk_t62` and returned GRT-0116 at total overflow 178 (M3 24, M5 132, M7 22). Failed ODB and attempt log are retained.

The later recovery congestion report has 38 detailed markers concentrated along the north boundary at y≈1225 µm, mainly `coll_oa` with some `coll_ia`. The rendered review also shows two west hotspots near (9.4, 656.9) and (13.96, 728.2) µm, upper-middle inter-row density and tap marks at (86.52, 910.61) and (380.30, 953.81). It reported a peak 106% and 13,175 gcells above 90%. The north A bundle is distinct from the west B beat-bank locality target.

The job took its existing bounded residual recovery after reporting overflow 50 in two coarse bins against cap 500. The recovery retained its stall-resume checkpoint and is in FF hold repair. No new route is released by this review. Assess the actual recovery guides and residual locations when the attempt completes.
