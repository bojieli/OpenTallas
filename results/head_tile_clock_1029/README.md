HEAD tile clock reassignment, 2026-10-29, planning before build.

Actual data placement passed 0/27665 captures beyond405um,max400.95um.
Fresh actual entry clk dump unit519295 includes25749 register-clock sinks
(including the retained START export copy); forwarded ring clocks stay separate.

The inherited unpadded reg_spine planner produced37groups but actual projected
radius392.1um. Its kmeans centroid projection and minimum-group merging occur
before final nearest-tap assignment, so the original nominal100um cap did not
hold. The new opt-in projected_radius_um closes the ACTUAL assigned radius by
adding a tap at the farthest legal sink and reassigning;45groups now max97.225um.
Small outliers can own singleton groups. This preserves existing physical trunk
and tap coordinates; no topology or cell defaults change without the option.
Two regressions cover sparse projected outliers and impossible keepout sinks;
7focusedtestsPASS.

Old tap-ID pad counts are discarded. The prebuild pad model uses matched h17
routed physical trunk-node prefixes and a nonnegative local-tree delay fit vs
stub length, log2(sink count), radius. It subtracts old physical BUFx4 delay from
calibration and fits NEW groups. BUFx4 physical rise-stage delays22.270TT and
16.293FF come from the qualified model_corr SPICE chain32minuschain4 slope;
no BUFx24 factor is applied to BUFx4.332newpads jointly target525TT/425.25FF.
Predicted group means512.97..544.76TT/406.66..432.04FF. Calibration residuals
25.8TT/20.7FF and FF prefix0.81 approximation are explicit. Groups1..2601sinks,
maxtrunk→tap365um. Largest group extrapolates beyond prior2022sinks; local CTS
buffering and actual loads/slew require measurement. No clock trimming after
build is planned. Existing matched macro early-tap physical paths/stagesA6/B4
are retained and require actual core-pin remeasurement.

clock_assignment.png VIEWED. Independent new-clock review requested after
independent data-geometry approval1f2412352. Diagnostic CTS/GRT only after
review; no freeze or signoff claim. Built external STARTpin→centralS0 input
transport timing must be measured for CA, not inferred from0RTLcycles.

PARKED at explicit Claude-reset instruction. No CTS/GRT launched.
HR0 was an inherited illegal ideal site inside upper-right core at660,690.
Moved planned HR0 to legal upper crossbar660,717; local wire-delta model records
this change. Latest replan has333pads (earlier332 beforeHR0move); group predicted
ranges unchanged, maxradius97.225um. New reg_spine.py/reg_spine.json are staged
only in the remote lane parent directory, NOT installed into tile/ yet.

OPEN CONCRETE FAILURE before build: the inherited horizontal-left pad packing
puts26 individual planned pad positions inside macros or outside core rows.
Affected tap IDs4(central channel),14(B side),37(W edge),38/43(E edge).
Tapdrivers/trunk now outside macros, but PAD CHAINS need legal orientation or
vertical packing. Proposed next action: scoped opt-in per-tap pad direction/axis
in reg_spine writer/Tcl, preserving cell count/clock topology. Rightward chains
fit4/14/37; vertical chains likely needed38/43 where horizontal width is tight.
Do not launch CTS until legal pad-source plan and fresh independent G1.
Serdes independent clock view was conditional on legal actual trunk/tap sites;
this new pad check has NOT passed. All data-stage geometry remains unchanged.
