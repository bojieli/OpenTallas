WIP: S81 station exact two-child source form
=========================================
No plan, recipe, view, hold release or physical activation is included.

The exact B51 logical source was elaborated and cut into whole FT/landing
instances. Independent lockstep compares every output:106060884 known bit
comparisons, two reset/phase cases; boundary bit mutant caught. The miter
couples unreset writer-counter initial state explicitly; it is not boot proof.
See lockstep.json. Six graph mutants are in mutants.json.

The physical successor uses the retained placed mapped source plus the actual
CTS source-root census. All53074 sequential cells have exactly one traced
input root, all inversion parities0.39153 local-clock bindings change from the
pre-CTS logical clk to their actual CTS root; data/reset pins do not change.
There are86 actual roots. Whole-stage ownership remains intact even when a
stage's physical bits span roots. Raw logical children must not be hardened:
doing so would collapse those physical root assignments.

At cut630.72um, native graph conservation proves:
 west97491 functional cells/28053FF; east75011/24595FF;
 parent16467 functional cells/426FF; total188969cells/53074FF unchanged.
Every original cell/connection/master/parameter and initial value is checked.
Keep metadata preserves unused native reset/clock cells against submod's
opt_clean. The first pruning attempt was rejected, not adopted.
Clean child ABI has44/40 clock ports and11017/11079 scalar signal pins.
Scalar naming is an interface representation: each whole register stage still
belongs to exactly one physical child, with all data/epoch bits together.

Source tools:
 tools/die_plan/station_native_clock_capture.py validates placed/CTS instance,
 master family, pin and root identity and captures actual root bindings.
 tools/die_plan/station_hierarchy_split.py prepares the cut and proves exact
 graph conservation. It never approves routing or manufactures timing frames.
 native_groups.py --work-dir WORK uses native FF footprints.
 keep_source.py --work-dir WORK/mapped retains exact source state inventory.
 clean_abi.py --work-dir WORK/mapped names scalar signals for the core SDK.

Retained actual inputs/results (dedicated filesystem):
 intel1:/srv/opentallas-scratch2/claude/codex-s81-split-1106
 Files native_B51_{place,cts}.odb, native_parent.v, native_captured.json,
 native_{ff_clocks,cts_roots}.tsv, mapped/{native_bound,kept_source,split,
 split_clean}.json, mapped/{clock_capture,keep_receipt,conservation,
 conservation_clean,abi_map}.json. Generated HDL and full sources stay there.
 Source kit was own retired B51, source closure and conditional FREG proof
 preserved; no live kit was edited.

NEXT PHYSICAL WORK (still owed):
 1. Fit complete register/landing footprints inside two abutting child lots
    with a parent seam and outer access strips; render and inspect the result.
 2. Native multi_root core SDK specs must retain all actual clock roots,
    related1:1 phase0 nominal relation, exact measured per-root early/late tap
    windows, masks and parent-related pair obligations. Current SDK has no
    direct tap_window import. Never assume common250/202.5 input budgets are
    equivalent or add an ignored field. No source-clock collapse.
 3. Generate/harden children through existing core recipe/spec frontend only
    after that interface and image review; actual final functional cell counts
    must remain<=150000, excluding physical-only taps/filler. Source counts
    are not post-route qualification. Utilization<=0.45.
 4. Compose and qualify real parent FF hold/related pairs, then batch family
    release. No existing hold has been removed by this work.
