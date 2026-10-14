This bounds a default-off packing candidate, not a placed tile. The MILP uses
all five bank rows, eight lane slices, node, eight final TX leaves, two RQR
leaves, a 47.52 x 324 control sizing shape and an unmeasured 47.52 x 216 cache
placeholder. Every pair has a 20.088 um channel, with 20.088 um outer margins.
The 362.88 x 1425.6 outline is infeasible under these exact assumptions.
Symmetry constraints merely order identical leaves by y; they do not remove
any unlabeled fixed-shape layout. R0/MX/MY/R180 preserve dimensions.

This does not bound shapes that have not been measured, altered margins,
shared/assigned pin channels, or a new legal rotated-view contract. Current
closed views and die timing/transform code do not authorize R90/R270; those
rotations are excluded. No pin assignment or timing feasibility is implied.

A narrower control alone is insufficient for this stated shape set. The next
request is a source/clock-bound cache footprint and a channel/face-aware
packing review, followed by an explicit slot request if no constructive fit
exists. Reticle/pitch limits remain unchanged; this result grants no exception.
