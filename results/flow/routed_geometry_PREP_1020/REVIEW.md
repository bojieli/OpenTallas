Default-OFF geometry checkpoint proposal; no native rejudge or timing/capacity credit.

The explicit --routed-geometry profile admits exact 5_2_route.odb and6_final.odb only when the dumped native design contains clock cells. It retains the actual checkpoint name and a distinct routed stage, uses existing own-leaf/tree geometry gates, preserves all existing geometry thresholds, and retains stage equality for template comparisons. Unknown names, missing native clock trees and the default path retain their old refusal.

The profile discards any supplied GRT-log metrics and leaves the GRT capacity rule NA. A routed DB or DRC0 does not establish a same-scene native global-route capacity result. A separate exact-graph capacity packet remains necessary. Original raw FAIL/NA records are not changed.

Validation:36 existing/new geometry controls pass, including explicit default refusal, unknown stage, no clock tree, real checkpoint labels, unchanged own-leaf failure, and refusal to borrow a prior GRT0 log. No EDA process or source/case activation occurred.
