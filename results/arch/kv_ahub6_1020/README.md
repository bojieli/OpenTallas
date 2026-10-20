# AHUB6 measured redesign admission, 2026-10-20

The original g4 gates remain active and are not approved. Their source revision is
6feabc28437514b815f6954cbf2351335a50ad77. No gate result is fabricated here.

Read-only clock replay completed on ot-epyc9, unit oth-ubuntu-655021-1792476664,
from g4a 4_1_cts.odb. The copied per-flop TT census proves the late tail:

| Core-clock component | Flops | TT arrival ps |
| --- | ---: | ---: |
| u_rx | 33 | 607.96–800.17 |
| u_ry | 68 | 631.56–841.58 |
| u_core | 2535 | 562.93–594.85 |
| u_io | 386 | 563.03–600.70 |

All 101 late relay flops are missing from the core fence prefix table. The
LP region record explicitly assigns u_rx and u_ry to c. The reciprocal child
flop reference adds 238.7 ps to its 298.47 ps raw pin arrival, giving 537.17 ps.
The remaining core soft mass spans 37.77 ps; fixing fence membership alone
would address the observed clock tail, but does not satisfy native admission.

Native replay on the exact mapped 1_2_yosys.v completed on ot-epyc9 unit
oth-ubuntu-3896271-1792481779 using the original snapshot textbook_lint parser,
collapsing BUF/INV trees and excluding clocks/constants. native_over32.json
contains ALL 265 driver violations, not a thresholded top-eight summary.
Worst: u_io.start 549, u_core.start_b 293, u_io.em_w 292,
u_core.u_rr.rst_n[1] 168, rst_n[4] 128. Most remaining violations are
landing-writer rq roots (CHUNK_BITS=8), with 56 loads per writer chunk.

## Structural successor requirements

1. Include u_rx/u_ry and every LP-record-owned soft child in its regional fence;
   compare fence ownership against measured mapped sequential instances.
2. Split landing chunks from eight to two data bits, regenerate ALL reset-leaf
   counts/slices and valid-vector dimensions; preserve D4/K2 and all edges.
   A writer contains data and epoch/reset consumers, so CHUNK4 is insufficient.
3. Replicate command-start and export enables as kept, uniquely parameterized
   same-edge copies, distributing consumers in groups at most 16 bits to allow
   mapped enable logic. Do not add an unpriced start stage.
4. Replace the five broad core reset roots with same-depth local leaves;
   reset_n[1]/[4] are actual violations, never README waivers.
5. Partition zseen clears and decode consumers, then remeasure ALL mapped
   combinational roots, not only flop drivers. Anonymous roots currently reach67.
6. Run native census BEFORE a layout gate, and prove behavioral PASS plus mutant
   witnesses using Verilator5.050. No successor is admitted until all violations
   are resolved. No new kit gate or route was launched by this evidence packet.

SAFE checklist: pins/reach/depth/storage/schedule inherit g3 only as hypotheses;
fanout FAIL measured265, clock FAIL measured304.4 ps child-inclusive spread,
floorplan ownership FAIL measured101 missing soft flops. Reset fanout FAIL.
A full kit review and current measured evidence remain mandatory.
