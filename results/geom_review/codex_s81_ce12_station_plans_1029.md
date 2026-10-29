# S81 seven bound station kit plans

Personally viewed results/codex_s81_ce12_1029/station_plan_review.png.
PASS-COND for ONE placement of t8/t23/t31/t43/t44/t49/t52 only.

These are macro-free 1442.88 x 1226.88 corridors on the frozen plan. The broad
N/S bundles keep their pin order; corner-turning bundles occupy separate edge
windows. Forwarded-clock entries follow the corresponding source/destination
faces. There is no macro wall or halo constriction. Many bundles cross more
than one clock region, so actual landed registers and the priced station chains
must remain in the bound kit; these kits export that actual bound RTL rather
than trying to emit a new native observer. All seven preflight checks pass.

The picture uses bundle centreline guides, not fabricated actual routes or
stage placements. Before CTS, inspect actual FIRM stage placement, full r2r
reach, pin density, landing/source clock ownership, reset and PG continuity.
No CTS/GRT/route/sign-off approval is implied by this initial review.
