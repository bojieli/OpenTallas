# SC2 transition/envelope research: native same-corner API PASS, activation HOLD

This is a standalone analytical and native API prototype. It changes no compiler,
RTL, production helper, existing macro view, or scene consumer. **No SC2 Liberty
is emitted.** The four `CALIBRATION_ONLY_*` libraries modify the existing legacy
`ot_sram_1r1w_32x546_m1` and a native INV solely for the discriminator below.
They are private fixtures and must never enter a production ADDITIONAL_LIBS list.

## Actual source model and an explicit transition interval

`source_identity.json` pins SC2 source `19ccd29b9`, corrected all-corner zero
CQ model `46361c2ce`, the source generator/writer/planner, and unchanged access
model SHA `564c39512720a00c2924f267b87e36c487b5bba76817142b2c5b54d346fbb988`.
S81 terminal-protection audit `ec861194a` keeps that geometry/model unchanged:
437 paths, 870 shapes, 870 vias, 1740 enclosures; its protection proof does not
qualify native parent escape, grid access, PG, or physical timing.

The actual legacy generator/writer transition formula is
`S(C) = 1.5*FO4_corner + 2.2*Rout_corner*C`, independent of clock slew.
At the largest admitted SC2 load 46.08 fF its TT/SS/FF results are respectively
73.650948 / 107.199464 / 54.327251 ps. These are exact analytical formula values,
not lower/upper transistor characterization. The planner's hypothetical writer
formula would yield 220.820365 / 260.427594 / 198.155755 ps after access, but its
`2*Elmore` broadening term does not itself prove a 10–90% waveform bound. That
old term is recorded for comparison and is not adopted as a certified upper.

This packet proposes an explicit, deliberately wide conditional waveform model:
a causal monotone exponential source step with mean `S(C)/ln(9)` followed by a
normalized nonnegative passive RC impulse response. The planner's positive-R/C
access delay upper-bounds the access impulse mean. For a nonnegative response,
Markov gives `t90 <= 10*(mean_source + mean_access)`; `t10 >= 0`, therefore
`t90-t10 <= 10*(mean_source + mean_access)`. Any nonnegative source delay shifts
both crossings and leaves their difference unchanged. This yields:

| Same corner | Conditional complete 10–90% interval, ps |
| --- | --- |
| TT | [0, 735.177266] |
| SS | [0, 918.156705] |
| FF | [0, 630.526765] |

The lower transition bound is zero and carries no positive earliest-CQ credit.
All three retain the previous conditional zero intrinsic/access CQ lower bound;
nominal positive FF/TT/SS CQ is never reused as a minimum. Related/output timing
references remain the same external 50% thresholds, slew 10–90%, derate 1. The
actual native INV library and legacy macro fixture use these same thresholds.
The SC2 load range remains 0.72..46.08 fF; the wider native fixture load range
below deliberately includes zero to cover its small real pin capacitances.

The exponential source interpretation is a new explicit analytical assumption,
not a consequence of knowing only a nominal 10–90% scalar. An arbitrary waveform
can have long tails with that same scalar. Negative impulse components, active
coupling/nonmonotonic behavior, an earlier reference offset, a different waveform
interpretation or unbounded/unpriced access capacitance must refuse this policy.
This is an actionable research model, not a demand for manufacturing qualification.

## Whole-interval native lookup and constraints

The intervals exceed the old 320 ps domain. The prototype uses an explicit common
research interval [0,1000] ps, not a clamp to [5,320]. `envelope.py` divides each
finite two-dimensional rectangle at every native table knot, including endpoints
outside the first/last indices. A bilinear function has its extrema at rectangle
vertices; the finite union therefore bounds the entire mathematical lookup,
including nonmonotone interior knots. First/last native segments extrapolate
linearly. Only output transition receives the native zero clip; negative delays
and negative check values are preserved. A documented float32 research cushion
and outward float64 rounding accompany the exact mathematical extrema; this is
not a formal floating-point certification or derate/variation proof.

Data and clock slews are independent axes for each setup/hold check, both covered
over [0,1000] ps. Their required upper values are carried in **both** min/max
role fixtures. A minimum delay role never receives a minimum hold requirement.
Reusing the old constraints for [5,320] would be unsound: extending the source's
affine check law to the proposed rectangle would require SC2 analytical setup
upper TT/SS/FF 299.078321 / 315.923687 / 292.882498 ps and hold upper
130.909486 / 141.052123 / 128.316649 ps, with original adverse access penalties.
These are explicit out-of-domain analytical extensions, not newly characterized
acceptance values. Period/pulse/cap/load/electrical requirements are not zeroed.

Native mathematical extrapolation is useful feasibility evidence. It does not
expand physical characterization merely because the native tool returns a
number. Every envelope receipt marks `physical_domain_qualified=false` and every
corner model records `production_admission=false`. A later research policy must
explicitly adopt the generator/waveform/extrapolation model and domain, or narrow
the admissible load/slew and recompute. Silent extrapolation is forbidden.

## Actual small native discriminator

Unpinned `ot-run --mem 3 --threads 1` admitted this on ep8. The actual image is
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`,
OpenROAD `26Q3-1510-g6cb3f2b704`; exact binary/header/library hashes are retained.
The read-only C++ accessor compiles against those installed headers and reads
actual scene-mapped cell/arc table models. `analyze.py` matches **168 native
lookups**, including zero input slew/load, below-first-index and beyond-last-index
queries, against the explicit bilinear rule. Eight real arc/check envelopes are
retained. Zero and 5 ps produce different native INV delays; no 5 ps clamp occurs.
Four structural/domain negatives refuse, and nonmonotone interior-minimum,
constraint-maximum, and transition-only-zero-clip witnesses pass.

The actual circuit is two legacy SRAM instances with one real `INVx1_ASAP7_75t_R`
between launch output and capture data. No routing/synthesis is needed to answer
the API question. The ideal 20 ps clock is explicit pre-CTS calibration only.
All roles use the same TT source corner. Private fixtures replace only the INV's
delay/transition table values and legacy capture constraint values with their
derived envelopes; real gate truth, pins/caps and actual arc topology remain.
Capture setup upper is 277.685433 ps, hold upper 122.411351 ps in both roles;
the INV interval is 1.889813..569.935728 ps. The INV output-transition envelope
upper 564.522796 ps fits the same common [0,1000] ps downstream-check rectangle.

| Native scene | Minimum rise arrival, ps | Maximum rise arrival, ps | Result |
| --- | ---: | ---: | --- |
| Untouched same-corner TT | 340.561157 | 340.669434 | API reference |
| Correct TT envelope roles | 329.833038 | 897.954590 | Expected roles and numerical values PASS |
| Deliberately swapped roles | 897.878906 | 329.908722 | Observed wrong identities, REFUSED |
| Missing explicit max role | No library load | No library load | Preflight REFUSED |

The swapped run deliberately bypasses the refusing preflight solely to prove
that native min/max mappings change; its timing result is not accepted. Native
capture setup/hold mappings are inspected on both sides as well as the data arc.
An initial missing-LEF error is recorded in the tool transcript. Long-stdout
serialization and Python module-shadowing diagnostics are retained as files;
corrected terminal probes pass. No job remains live.

## Coherent next implementation boundary

This closes feasibility for an explicit analytical interval plus whole-domain
native NLDM envelope technique on one actual dependent cell and capture endpoint.
It does not implement an interval STA engine or qualify every cell/path. The
hashed 33-consumer inventory is copied unchanged in `CONSUMERS.json`; none is
patched. Before production adoption, one approved model/geometry/behavior/domain
identity must cover all role writers, standard-cell and macro timing checks,
clock/data propagation, threshold conversion, real loads/wire RC, synth/pre-CTS,
CTS/repair, exports/re-STA/verdict and every parent SDC/consumer. Every downstream
arc/check needs an envelope over its actual whole interval; widen/refuse when a
propagated interval escapes the approved domain. Non-NLDM/unsupported axes,
variation/derates, missing/swapped roles, unapproved extrapolation, stale source
or an unsupported consumer must refuse, with no single-table fallback.

Original source behavior and finite throughput, geometry/native access, physical
clock and parent timing still require their existing research validation. No
SC2 route retry, parent adoption, production Liberty, or shared helper activation
is authorized here. Full remote source/fixture packet is retained at
`ot-epyc8:/srv/opentallas-scratch/claude/sc2-transition-envelope-1019`.
