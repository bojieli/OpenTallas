# R6 station41 source component

Source implementation for the bounded numerical grant at `6f226591b`. This is
a new standalone module, `ot_hbm_r6_station41`, with `ENABLE=0` by default.
No production compiler, existing RTL, fixture, arithmetic primitive, gate tool,
or default source file changes. The existing LAT6 FP32 adder is instantiated
41 times with one genuine operand register stage. No behavioral FP arithmetic.

Run `python3 tools/hbm_record6_station41/generate.py` to reproduce the RTL and
source ledger. Inputs are the pinned folded-model JSON and minimum mux
inventory. The generator checks unique source lookup, all 26 fragments, all
27 global joins, the 40 private station peer sets, and exact operation count.
The upstream canonical expression and 1,228 result-lifetime checks are retained
in `model_input.json`; they are model evidence, not RTL execution evidence.

`start` is sampled at useful edge zero. Before edge one `cycle=1`; before
capture edge 64 `cycle=64`. Capture mask must be `4'hf` at 64,176,288,400, with
group 0,1,2,3 respectively, and zero at other active edges. The 512 words use
quarter*128+lane mapping. All 512 face words have held payload and validity;
only q0/q2 lanes 0..127 and q1/q3 lanes 0..31 feed the 40 stations. Each active
word's actual lane validity contributes to the capture counter. The component
counts actual node valid events, requiring 1,280 captures and 1,281 additions.

Capture is registered at 64; the first selector reads that held register at
65. This corrects the original model's same-edge capture/selection assumption
by one serial edge. The source calendar therefore predicts root consumption
at **591**, not 590. At start S a station captures the first selector, at S+1
the second selector, S+2 its real OPR, and S+3..S+8 the LAT6 pipeline. Actual
node output is visible after S+8 and sampled into the held result at S+9.
The S+9 selector consumes the real node output through an explicitly counted
live-result bypass. Node-valid, episode epoch, operation ordinal, and group
ownership checks prevent substituting an old held result. The same ownership
rule applies to the global adder and consumed-entry bypass. The deterministic
calendar never stalls. Missing operands or unexpected valid edges fault.

Every station has eight fixed operand registers and its own 12-source maximum
selector (eight words plus at most four fixed peers). The three first-stage
4:1 B muxes and the second-stage B mux are actual registers. A also has two
stages. Registered controls are genuinely used in each 16-bit segment. The
26 global entries retain payload, validity, epoch, group, base, and subtree
size exponent. Each global join reuses a consumed child's slot. The two padded
zero subtrees are the only implicit numerical sources; the generator refuses
to pad a live subtree. The global operand selectors use four registered 7:1
groups followed by one registered 4:1 selection per operand.

Input capture has 1,024 useful local enable FFs (two per word) and 32 actual
ancestors (32 descendants each). The proposal's 33 was a conservative
reservation; no unused copy is emitted to claim an artificial census. Live
bypass and ownership registers are extra costs recorded separately in the
ledger. Arithmetic mode pipeline bits from the MAX-capable source are absent
because this distinct component only implements the granted ADD operation.

Reset asserts and releases through two ordinary sampled face stages. Data
payload is not reset; all consumers qualify validity. Start must follow their
actual release. The internal sampled reset currently drives the actual valid,
enable, state, and arithmetic resets; its large fanout, the common cycle/epoch
distribution, select ancestors, fragment enables, and output boundary require
native synthesis census and subsequent structural distribution before any
physical qualification. Their existence is disclosed, not called SAFE.

Source checklist: pins have registered held input capture; dedicated root is
the actual registered arithmetic output. Reach/fanout/depth/geometry/clock are
**HOLD** without synthesis/native census. Storage is private operator words,
fixed fragment entries below 2 kb, and actual arithmetic pipeline registers;
no runtime whole-record memory or shift delay chain. Schedule has the explicit
one-edge correction above. No physical gate is part of this implementation.

MUT1 swaps input words 1 and 2 in each chunk; MUT2 selects a different available
canonical sibling where the station has multiple peers; MUT3 disables the live
node-result bypass and exposes the previous held value. They are causal source
changes awaiting actual fleet fail witnesses, not presumed PASS/FAIL results.

No simulation, elaboration, synthesis, timing, source-equivalence, arithmetic,
golden-root or physical PASS is claimed by this source packet. The parent owns
the combined fleet build and original-gold retirement bench.
