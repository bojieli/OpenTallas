# Selector revised FF placement roles (diagnostic only)

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
