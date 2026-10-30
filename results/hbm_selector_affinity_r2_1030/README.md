# Selector revised FF placement roles (diagnostic only)

## Active revision: roles6 / role_model_v3

The original broad regions and roles5 are superseded. Fresh kits were generated
from approved clock-feedthrough main `304e8a41733`, with unchanged complete RTL
and macro-view inventories versus the completed 301,964-instance synthesis.
Roles5's SRAM rows collided with eight inherited clock/reset islands. The active
emitted rows are Y=9.708, 62.220, 166.188, 234.204, 286.860, 373.548 um, in each
macro column. Minimum macro channel is 11.448 um (required 10.8), island clearance
4.716 um (halo 4.32), and the bottom halo ends at 5.388 um versus core bottom
4.32. There are no south functional ports or boundary-capture FFs under that
narrow bottom strip. Actual PG/clock/cell fit remains a placement gate.

The active model includes each native in_r register's two direct consumers:
SRAM WD and all own-quarter histogram FFs. All quarter state uses the reduced-Y
WD-safe body; threshold/tie copies stay near the common controller. Relay bays
are entirely outside quarter bodies, root, first-reset box, macro halos and
clock/reset islands. Quarter unions exclude root; root excludes threshold boxes.
This avoids an unsupported assumption about overlapping INCLUSIVE groups.
Exact distinct-region overlap count is zero. Quarter union areas are
9069.926/7166.362/8286.106/6550.502 um², root 5076.173 um², each threshold/reset
box 74.650 um². Bays hold at most 16 FFs. Actual master/fixed-cell capacity must
pass below 80% before GPL.

Active bounds: worst registered station-box leg 394.872 um, histogram→threshold
311.04 um, SRAM RD→quarter FF 265.614 um, direct same-quarter SRAM RD→WD 339.744
um; no modeled leg over 405 um and no halo/island collision. Mapped FF role
census remains 20,728 FFs with zero unclassified native FFs. Both normal
preflight v3 receipts pass with zero issues. `selector_roles6_disjoint.png` was
personally viewed. This remains an estimate and review-before-PLACE receipt;
actual FF and memory endpoint geometry is required before CTS/route.

Native LEC was still solving when this milestone was saved. The lane-local
reuse mechanism is adapted from the established HBM core helper and checks
complete RTL inventory/digests, RTL_FILES, top/parameters/defines, complete macro
views, original EQUIVALENT receipt, gold/gate scripts+AIGs and both synthesis
netlist hashes. A private runner changes only the LEC call to this checker,
with a full native proof fallback; unproved fallback fails closed. All other
lint, face, port, SELRANGE, mode, placement and geometry gates remain. No physical
run has started, and source default LOCAL_CTRL=0 is unchanged.

The first v3 finalization stopped because kit_preflight intentionally opens its
output receipt exclusively and the v2 filename already existed. Unique v3
receipt names fixed that driver error, preserving the earlier receipts.

The following initial planning history is retained to explain the revisions.

This replaces the broad quarter-prefix guide before any placement. The old guide
made six W-input-to-capture legs unavoidably longer than 405 um (worst lower bound
517.464 um). It also constrained combinational cells with each broad prefix.

The replacement constrains existing sequential cells only, in one pass:

* quarter histograms and core selected-line FFs use SRAM-facing inner ribbons;
* op/pass/addr capture copies use individually modeled stations between their
  actual input face and all quarter consumers;
* op copies include every meaningful SRAM WD endpoint and memory control pin;
* buffer, fill, rv/rop and other gq control FFs use shorter-Y ribbons covering
  their direct combinational SRAM WD cones;
* quarter threshold copies and tie budgets remain near the common controller,
  because their D inputs depend on all four histogram quarters;
* existing native input/output registers receive separate relay stations;
* reset first and second stages have distinct roles and source/consumer bounds.

The exact macro-inclusive model bounds the worst station box leg at 403.512 um,
histogram-to-threshold-copy at 316.44 um, SRAM RD-to-quarter-FF at 261.414 um,
and buffer/control-ribbon-to-meaningful-WD at 395 um. This is a constructive
placement estimate, not an actual-placement, timing, or signoff result.
No new FF or functional/calendar cycle is added by this placement revision.
The inherited physical kit has boundary input/output stages; these are explicitly
existing stages, not free native-model latency changes.

An initial hypothesis that W op input to NE SRAM WD was about 892 um was
**incorrect**: the top macro's upper 176 WD bits are constant padding; all 80
meaningful WD bits of that macro are on its inner edge. Including the actual LEF
coordinates for every meaningful bit gives the bound above with current pins.
No pin relocation is requested from that disproven hypothesis.

Mapped synthesis census: 20,728 FFs, zero unclassified native FFs. All 56 local
control copies, eight quarter reset FFs, and 64 threshold copy FFs survive.
`rst_sync[1]` is named `u_fcore.rst_core_n` in the mapped netlist (distinct FF,
same first-stage D and raw async reset). Only unused global addr_r[6:7] disappear;
all eight bits of each local addr copy survive. Mandatory role checks enforce
control and reset names; a guide fails at >=80% movable-plus-fixed capacity.

Both source-corrected synthesis variants map to 301,964 instances (301,952 std,
12 SRAM), std area 35,560.8 um²; native netlist equivalence was still in progress
when this planning receipt was written. Do not place until equivalence is proved,
the approved clock feedthrough source is included in a fresh kit, and its actual
placement capacity/face offsets are checked. Do not CTS/route until actual full
FF and macro endpoint geometry has passed review.

Run `model_roles.py KIT OUT` with `ingest_estimate.py` beside it; run
`audit_roles.py KIT OUT` against the mapped netlist. `render_roles.py` renders the
planned geometry. `selector_roles_guide.tcl` consumes the generated role data and
replaces the original diagnostic guide. The active synthesis kits have not been
mutated with this revision.
