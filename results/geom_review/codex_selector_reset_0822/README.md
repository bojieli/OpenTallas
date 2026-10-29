# Selector synchronous local reset candidate

This default-off RTL candidate replaces one die-wide internal reset fanout
with a deterministic three-flop tree after the existing two boundary stages.
It adds **two boot delivery cycles**, three FFs and no runtime data/op cycle.
The enabled boundary samples the parent-delivered synchronous reset normally;
there is no added async CDC synchronizer or false-path request.

Actual old placed graph has11031 reset capture targets and a single-source
minimum possible Manhattan reach425.817um, so source movement alone cannot
meet405. Proposed common/W/E relay sites lie in the central horizontal street
between SRAM rows. Grouped reset leaves cover q0/q1 west and q2/q3 east; the
controller uses west. The current shared selected_v[2] singleton needs its
new physical quarter-2 capture placed with the E group. Geometry is an estimate
from the old source, not qualification of a new placed netlist.

LOCAL_RESET=0 retains original async shell/default behavior. LOCAL_RESET=1
requires the HBM owner to publish a timed synchronous delivered-input reset
contract and the added boot/START offsets before adoption. Hold asserted for
64 edges as required by the parent rule. No operations may issue during reset
or before reset delivery completes. Warm-reset tests quiesce the op pipeline
before assertion; arbitrary live-operation reset is not claimed equivalent.

Validation so far: exact2-cycle relay check152 edges, seeded stuck-E mutant
caught107 times. Actual four-quarter selector program compares original
source6bbd6a022, new default-off, and new enabled form using canonical SRAM
and compact tree, three cold/warm boot programs:567 compared cycles,24 valid
selected-output cycles, zero differences; enabled stuck-E mutation caught516
times. This is a full-shape source lockstep, not a whole-source formal LEC
claim. No P&R or SIGNED claim.

The first focused width lint exposed two pre-existing integer STRUCT generate
conditions and a new boolean-to-integer MUT override. These were corrected
to explicit comparisons/32-bit constants. The initial full lint log was not
retained; this diagnosis preserves its three reported errors. Subsequent
WIDTH/SELRANGE lint passes. All other physical/adoption gates remain open.
