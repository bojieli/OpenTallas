# Actual mapped all-driver census, composed SAFE PC controller (LH-BW collection 10-19 11:40)
Floorplan/synthesis only, no CTS. summary.json lists per map the >32-load roots split reset/nonreset.
- map4 49 roots (43 reset + 6 nonreset, max 48), map5 53 (43+10, max 45), map6 (source 1cc470d0d/0b823619b) 48 (43+5, max 42).
- Verdict FAIL against SAFE item 3 in every map; map6 full fanout_gt32.json and predicate_mapped_audit.json (FAIL) in ../map6_rejected.
