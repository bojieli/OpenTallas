SU-C restoration candidate, not adopted

Canonical825 declares eight children but carries no physical LEF/libs. gen_phys skips them, so the prior473444/464986/464067 counts flatten those children and lose clk_c0..7. Existing frontend already activates exact-master Liberty cuts before deferred native RTL; no generic hook is needed.

This source event applies existing approved Decision13 synchronous boundary-reset relay edits, unchanged two-edge release, and the existing bit-exact VMR shared write-input recipe. Legacy recipes drop edits now present in canonical source. The64-edge reset source-cone lockstep passes; wrong-depth and subcycle-short-reset controls are caught. Full child correctness remains the original signed child proof plus an exact source/parameter/ABI identity check, not this cone test.

Recovered VMRf4kfinal and CRHf4g signed views are staged under cores/su/signed_restore_1101, not attached to a physical plan. Both are MIF0. Dedicated die-owned typed FT ports/arcs are recorded in plan_of_record/cores/su/signed/*die_owned_ft.json; actual physical traversal must be restored, not tied/added unused in functional RTL.

PROG s8b and latestffh10r are MIF1, while canonical parent is MIF0. Counted BTABP8eco is also MIF1. These remain nativeMIF0 pending matching views or a priced exact source event. SU8K0 archive recovery is pending; legacy pre-K0 is not a substitute. No RED decomposition or route is authorized before actual folded residual count.
