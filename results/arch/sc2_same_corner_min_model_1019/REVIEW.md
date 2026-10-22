# SC2 same-corner minimum model: conditional zero bound, production blocked

This packet proposes TT-MIN and SS-MIN and corrects FF-MIN for ROOT review only. It changes no
Liberty, compiler, helper, RTL, reader, route or production activation. It
borrows no FF data. The exact source is SC2 prototype `19ccd29b9`, generated
master `ot_sram_1r1w_512x128_m4_r2c2_p192_sc2`; MODEL.json pins its generated
JSON. Native API probe `3eb9da2a9` is reused; no simulation/build/probe ran.

## Derivation and limits

The existing `sram_gen.py:timing_model` sums control, decode, wordline,
bitline, mux, sense, output and load terms. All are nonnegative in the stated
analytical model. The SC2 planner adds passive positive-R/C clock and output
access delays. Dropping **every** such term yields an intrinsic CQ lower
bound of **0 ps at TT and independently 0 ps at SS**, with **0 ps added
clock access and 0 ps added output access**. This deliberately gives up
positive earliest-launch credit. It is not the TT/SS nominal CQ table and
not a cross-PVT FF substitution.

This is a lower bound on the additive analytical model, conditional on its
edge reference being the external rising clock at the Liberty 50% threshold
and the output crossing using the same convention. The synchronous source
has only a posedge read/output update and disabled-read hold; no transparent
readthrough, asynchronous data arc, generated clock, or forwarded-clock
output is modeled. The lower bound does not cover an implementation with
a negative internal-clock reference offset, asynchronous/feedthrough arc,
nonmonotonic waveform or an earlier output-threshold crossing. RTL event
causality alone cannot characterize analog 50% timing. Such an implementation
requires a proven signed reference-offset lower bound or must refuse this
policy. No transistor minimum characterization is claimed.

The planner's existing `min_cq_ps_lower_bound` is assigned directly from
`base.clk_to_q_ps`. Its TT 415.195299 ps and SS 524.072474 ps are nominal
FO4/Elmore analytical delays, not demonstrated earliest intrinsic bounds.
The calibration uses a DFF CQ lookup at 20 ps slew and four-inverter load;
it does not derive a minimum across the memory's slew/load domain. Those
positive numbers are **not approved TT/SS MIN**. The same defect applies to FF 346.043664 ps: it is also a nominal analytical
base and **unqualified as MIN**. ROOT explicitly superseded the earlier FF
conservative-minimum claim; the immutable old packet remains historical.
FF-MIN now requires the same conditional zero policy or must refuse; a
positive FF lower bound remains unknown.

## Constraints remain upper requirements

Minimum propagation and maximum constraint requirement are independent.
Every role keeps same-corner real clock cap, input cap, output loading,
setup, hold, minimum period, pulse widths and electrical restrictions. No
constraint is zeroed. Setup analysis needs latest launch/data **and earliest
capture clock**; hold needs earliest launch/data **and latest capture clock**.
Resizer, export, min-period/pulse checks and generated-clock/reference readers
can query either side within a nominal setup scene. Ideal-clock pre-CTS
runs must identify their ideal approximation; they cannot replace final
propagated native clock analysis.

The original writer has, for constrained-data slew d and related-clock slew c:

- setup = base_setup + 0.25(d-5) - 0.10(c-5)
- hold = base_hold - 0.25(d-5) + 0.10(c-5)

Within both slew domains [5,320] ps, global upper corrections are +78.75 ps
for setup and +31.5 ps for hold. MODEL.json conservatively adds these to the
SC2 model's already charged clock/input lead requirements. This drops any
beneficial cancellation and charges the independent extrema. Constant upper
constraints across that domain are an analytical safe proposal; copying only
the low-slew scalar requirement is insufficient.

| Same corner | CQ lower | Setup upper | Hold upper | Period upper | Pulse upper |
| --- | ---: | ---: | ---: | ---: | ---: |
| TT | 0 | 128.578321 | 61.659486 | 424.030130 | 169.472793 |
| SS | 0 | 145.423687 | 71.802123 | 534.079476 | 212.589479 |
| FF | 0 | 122.382498 | 59.066649 | 355.908530 | 143.002089 |

All values are ps. TT clock/input access upper bounds remain 8.559227 /
13.012915 ps; SS 10.228103 / 16.645043 ps. These are analytical bounds, not
new timing acceptance. No extrapolation below 5 ps or above 320 ps slew,
or outside 0.72..46.08 fF load, is qualified. Period/pulse retain the model's
full adverse access penalties rather than inheriting zero MIN propagation.
If an actual characterization has different constraint conventions, nonlinear
slew dependence or recovery/removal arcs, these formulas do not certify it.

## Slew is a remaining blocking dependency

Zero CQ is **not** zero output transition. A minimum transition estimate is
not generally conservative for every downstream delay/constraint table;
nonmonotone tables and clock slew also matter. Conversely using the MAX
transition for MIN timing does not prove an earliest bound. The current model
only supplies a nominal intrinsic/upper transition component; it does not
certify a full transition interval at every clock slew and output load.
MODEL.json therefore records output-slew upper as unknown and does not
invent a native Liberty transition table. The conditional lower envelope
starts at zero transition, outside the existing 5 ps lower domain, so a native
reader must refuse until a valid transition interval or explicit downstream
arc/constraint extrema method covers it. Clamping to 5 ps silently is forbidden.

A future implementation must either prove supported native interval analysis,
or generate and validate conservative envelopes for **every dependent** data
and clock arc/check over the complete admissible transition interval. Ordinary
NLDM min/max role binding alone proves library selection, not this bound.
The prior API probe is sufficient for selection and is not repeated here.

## One coherent implementation scope

CONSUMERS.json carries all **33** exact hashed readers/writers from
`3eb9da2a9`, plus external ORFS read_liberty/scene setup and every parent SDC.
None is patched. A future ROOT-approved implementation must cover generator,
per-role writer, synth/pre-CTS, CTS/route setup and hold repair, native probes,
clock insertion/references, export/ETM, re-STA, final verdict and parent use
as one coherent scope. The approved complete manifest, tool/image identity,
source/model/behavior/geometry, slew/load domain and actual sceneArc mapping
must travel together. Missing/swapped/aliased corner or bound, unqualified
transition, stale receipt, or unsupported external reader must refuse before
SC2 is loaded. Standard-cell libraries also require the correct same-corner
roles; no FF clock path may stand in for TT/SS. Legacy masters remain unchanged.

The generated LEF's access leads/via enclosure obstruction protection is under
separate S81 review. S81 confirms broad interior M4/M5 OBS exist; an
undeclared 48 nm terminal-approach neck and exact per-path/via residuals are
being checked. No missing-interior-OBS defect is asserted here. This packet pins the old source and does not certify that
geometry. Any corrected geometry/model identity invalidates these exact
receipts until bounds and constraints are recomputed against it. Native
contact/PG/OBS/escape, physical clock, array behavior/throughput, parent fit
and same-corner scalar/transition validation all remain open.

ROOT decision requested: accept this conditional zero intrinsic/access policy
as the next analytical model, with positive CQ and transition bounds unknown,
or request actual minimum characterization. **No SC2 Liberty generation or
shared helper activation follows automatically from this packet.**
