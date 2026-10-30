# HH per-bit station allocation review

Image: `codex_hbm_hh_perbit.png`. Personally viewed 2026-10-30.

The root crop shows five narrow stage clouds for each direction in the open
horizontal street. Bank clouds follow the bottom and east outer corridors;
none crosses the pictured hardcore-plus-halo rectangles. The resulting bit
distribution follows the actual wide pin windows rather than clustering the
entire bus at a window centroid. Allocation preserves both station counts and
all epoch bits. The independent per-bit seam scan finds zero mismatched pin
positions and a maximum 399.577 um seam hop. The maximum internal hop is
401.76 um against the unchanged 405 um rule, with limited margin.

**PASS-COND: plan allocation geometry only.** This is not an actual native
all-stage FIRM placement or route approval. Clock/reset/START, PG, full native
cell/row/obstacle/capacity checks and physical gates remain open. Reuse the
shared all-stage placement-file mechanism when the current typed kit exists.
