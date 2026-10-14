# HBM SM real-child compaction exploration, 2026-10-13

Status: unsubmitted structural candidate and explicitly partial routing probes.
No die contract, real closed view, compute count, target, price, or throughput
claim changed. The original v13 die runs and live SMH r16 routes are unchanged.

The source-pinned tile boundary elaboration retains all twelve published hard
children. After removing synthesis-only `keep_hierarchy` for this census, each
tile also contains 995 parent sequential Q bits and an ICG. These 995 bits must
remain implemented. Across sixteen tiles this is 15,920 state bits per SM; the
parent is not a wires-only wrapper. The raw Yosys JSON and logs preserve this
inventory. Hard interiors remain blackboxes; this is wiring, not arithmetic
qualification.

The original 630.72 x 1080 candidate had 1,031 EG and 4,603 WG direct hard-child
bit paths longer than 500 um. The original WG changed individual orientations
without reflecting whole-layout positions. Actual LEF access points exposed both
that problem and distant TCL/TCT placements.

The new candidate is 630.72 x 1084.32 um, with all twelve closed child rectangles
retained at their actual dimensions. TCL/TCT and BDC placements follow actual XS
output locations; WG reflects the entire EG layout. Every retained hard-child
signal/clock/reset endpoint (35,218 bits per variant) finds a real LEF pin.
There are no rectangle overlaps or outside children. The audit covers 13,769
directed hard-child bit pairs, with zero paths above 500 um and a worst length
of 465.354 um in both variants. Twelve PTW-to-XS paths still fail the nominal
ETM residual pair calculation at the fixed 833.3 ps clock and cross-level
150 ps skew plus 60 ps uncertainty. No threshold was relaxed.

This is not full pin/timing closure. Each tile has 7,662 distinct hard endpoint
nets with no second hard endpoint, and 2,461 parent-logic connection endpoints
without a physical view. Boundary pins, own logic, reset, clock delivery, hold,
full ETM load tables and PG mirroring remain open. The optimistic two-layer
horizontal-then-vertical model has worst 100 um window utilization 1.040 EG /
1.050 WG despite worst straight-cut utilization below 0.60. It omits parent nets
and real PG/obstruction capacity; it can identify a bad chosen route, but is not
an impossibility proof or a passing routing gate.

Propagating these outlines into all 35 direct children gives a native SM frame
6013.44 x 2272.32 um, 437.263 mm2 for 32 SMs. All non-tile closed direct children,
names, views and sizes are preserved. MaxRects packs these frames plus all large
non-SM rectangles from the original generator inventory inside the unchanged
32984.288 x 25980.528 um reticle at 8.64, 21.6 and (area-order search) 43.2 um
halos, with zero overlaps/outside rectangles. The 21.6 um search leaves 73.11 mm2
of free union area; existing relay rectangles occupy 33.508 mm2. Relay groups
preserve each measured master/count/dimension, but their legal placements and
hops are not proved. The legacy non-SM rectangles include interim reservations;
all actual native non-SM children and unresolved PHY/service/HC regions must be
bound before any complete die fit claim. A skeleton packing is not placeholder
fit credit. No architecture limit has been proved.

Two k=1 OpenROAD GRT probes route only the exact hard-to-hard projection: twelve
real macros / six masters / 13,763 bit nets / 27,532 endpoints, no fabricated
placeholder pin. They omit all 995 parent state bits and all boundary routes,
clocks and resets, and cannot qualify the parent or die. Inputs have been staged
on EPYC4 and AGIdock; ot-run chose AGIdock for the corrected runs. The initial
probe netlist had unsanitized hierarchical instance identifiers and stopped
before placement; small failure logs are preserved in diagnostic_failures.
The corrected candidate maps each source component_child name to a legal,
unique hard_eg_N / hard_wg_N instance identifier.

Reproduction:

```
python3 tools/hbm_sm_compaction_1013.py prepare --source f6ee9d6d1
# Run generated eg.ys / wg.ys under ot-run on a staged work directory.
python3 tools/hbm_sm_compaction_1013.py collect --work <staged-directory>
python3 tools/hbm_sm_real_pin_audit_1013.py --work <json-directory> \
  --geometry results/arch/hbm_native_1013/sm_compaction/real_pin_geometry_candidate.json \
  --out <report.json>
python3 tools/hbm_sm_global_pack_1013.py --inventory <global_inventory.json> \
  --component results/arch/hbm_native_1013/sm/component.json \
  --tile results/arch/hbm_native_1013/sm_compaction/real_pin_geometry_candidate.json \
  --out <packing-directory>
python3 tools/hbm_sm_compaction_1013.py grt_projection
python3 -m pytest -q tools/test_hbm_sm_compaction_1013.py
```

Run computational stages only through ot-run. Generated full projection JSON,
case LEFs/netlists and boundary extraction scripts are reproducible inputs, not
archived routes. Commit only small manifests, raw boundary elaborations and
geometry/model results. The next step is to collect the two real-pin GRT probes,
classify their 2-D hotspots, then physically partition/harden the retained parent
logic and plan its clock entries before a full-parent route or final pin file.
