The optional per-type `flat_clock_forest_file` selects a complete planned native
clock forest for **exact post-place / pre-CTS cohort recovery**. It is distinct
from the H2 six-island core-family feature. Without the field, kits are unchanged.
It creates no ports and changes no data/reset connections, RTL or cycle counts.
A fresh synthesis with different instances, masters or geometry must get a new
native census; this helper does not reinterpret a stale checkpoint.

`flat_clock_plan.py` reads the complete native geometry and actual clock-root
ownership. Primary sinks are assigned to the existing primary clock inputs by
geometry/load transport with capacity1500. Forwarded roots retain their sinks.
The fixed-H option builds geometric binary regional trees, pruning only branches
without consumers; the region subdivision stops at50um cells (six layers in the
T6/T7 grid). Parallel terminal drivers split actual sink loads into groups≤32 and
spread≤40um. An arbitrary placed CTS leaf never becomes a planned driver.

Final models use the native calibrated clock-class RC from `setRC_rcx.tcl`,
R=.0214161kΩ/um and C=.113298fF/um, without an NDR discount, and an explicit80ps
root-input slew. `flat_clock_size.py` sizes only the calibrated R9 BUF8..24 pool
jointly at TT/FF, with a hard80ps output-slew constraint and a strict clock-window
objective. It uses no measured timing, pads or useful-skew offsets. Per-master
`spice_cell` factors and approved g021 AOCV charge actual noncommon tree paths;
CPPR credits only actual shared planned cells. Shared supply droop assumes this
flat native cohort is in one CORE PDN domain. Root latency-band numbers remain
INFO under the existing12.3a policy; native setup/hold signoff remains mandatory.

Actual forwarded↔primary relations remain separately visible under the existing
native landing-clock timing contract. They are never reported as80ps ordinary
related-pair PASS. The exact native SDC hash is frozen and checked at installation;
no SDC command is added or relaxed. Unknown cross-forwarded relationships or
unmodeled native root loads fail closed. Existing non-tie export buffers require
explicit modeling and are currently rejected.

A typical preparation sequence is:

```sh
python3 tools/die_plan/flat_clock_plan.py CORRECTED_NATIVE_GEOM.tsv \
  --native-sdc EXISTING_NATIVE_KIT/constraint.sdc --fixed-h \
  --libdir ACTUAL_TT_FF_LIBRARIES --out candidate.json.gz
# Use ot-run for substantial sizing work.
python3 tools/die_plan/flat_clock_size.py candidate.json.gz \
  --libdir ACTUAL_TT_FF_LIBRARIES --out sized.json.gz
```

The library directory holds INVBUF TT/FF nldm220122 `.lib.gz` and SEQ TT/FF
nldm220123 `.lib`. Candidates remain `build_allowed=false`. A proposed endpoint
packet overlay is analytical only; final qualification requires the complete
corrected, legalized ODB geometry, including existing reset/helper moves.

Read-only `flat_clock_sites.tcl` takes `ODB` and `OUT` environment variables and
exports native rows, master sizes, **all placed occupants**, and hard blockages.
Load it with `core_infra_plan.read_technology`. Call
`flat_clock_forest.legalize_drivers(candidate, technology)` to find actual empty
sites within2um of the planned centres. It moves no existing cell and refuses an
occupied neighborhood. After rendering and looking at the legal design,
`freeze_candidate(candidate, module, placements, library_dir, geometry_review)`
recomputes both corners at the exact sites and checks every root's≤20ps window,
≤80ps slew and ordinary related-pair bounds. It produces the explicit v1 forest
packet consumed by the per-type field.

Installation reuses native CI placement/tree/PG primitives. It validates the
complete STA input-root census, original native FF masters/coordinates/CLK pins,
root roles, real row sites, and every existing occupant before insertion. The
planned forest is leaf-complete: ordinary TritonCTS does not rebuild it. Exact
leaf membership, driver/clock-net ownership, native FF coordinates and frozen
input pins are checked again after the clock stage. Existing reset-pair checks
and PG audits remain active. Native G1 and review-before-route still apply.
No packet/source gate by itself authorizes a physical trial.
