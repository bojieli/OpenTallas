# SYSFACE native predicate/publication ownership model

**MODEL ONLY. Concrete same-edge source choice: retain the exact Candidate A native gate graph, and give each of its five unsafe predicate roots five explicit native publications.** This model adds 20 real logic gates and four real inverters, no state or edges. Native area becomes 133.348680 um² from 131.307480 um² (+2.041200). Known internal TT/FF pin-cap bounds fit the modeled logic cohorts. Implementation, source equivalence after implementation, mapping retention, STA, external boundaries, physical PG/reset and parent integration remain HOLD. No RTL, implementation source, mapping/build, P&R or STA was changed or launched.

The original a42894e3f SAFE/electrical FAIL remains unchanged. Candidate A source is 76277b2cb32db263d527bb1e7c66ae91754f2ef1. Its balanced expression has **no demonstrated native depth/timing benefit**: native maximum FF-D graph depth is eight versus seven originally; full-parent TT −57.924 ps / 833.5 ps / 28 levels remains separate. The earlier semantic model's illustrative source depth and old-parent 39-load publication do not establish ownership in this newly mapped graph.

## Exact predicates and meaningful consumer ownership

These are actual mapped predicates, not assumed one-to-one source wires. model.json contains their full exact source support, native function, all five input identities where applicable, original transparent paths and every original/proposed sink. The two digest predicate roots are partial digest sub-cones, not complete source-level image matches. The third predicate carries the remaining receive-validation conditions. Native bit 841 is the actual fault state cell's QN, with the preserved source/native inversion correspondence; bit 4 is receive_slot. No independently reset or cloned fault state is introduced.

| Native root | Actual master / function | Exact input bits | Old effective loads | Proposed publications |
|---|---|---|---:|---|
|1109|NOR5xp2; !A & !B & !C & !D & !E|1089,1099,1104,1106,1108|132|pub_1109_0..4|
|1194|NOR4xp25; !A & !B & !C & !D|1130,1151,1172,1193|132|pub_1194_0..4|
|1331|NOR5xp2; !A & !B & !C & !D & !E|1199,1218,1255,1293,1330|132|pub_1331_0..4|
|1332|AND2x2; A & B|841,4|131|pub_1332_0..4|
|1333|NAND4xp25; !A \| !B \| !C \| !D|1109,1194,1331,1332|144|pub_1333_0..4|

Each publication owns an explicit list of actual instance/master/pin loads and their root-relative inversion. Consumer cohorts are sorted by their actual downstream state field and bit, derived from native FF-D connectivity. This covers tag, generation, fused capability, retained image epoch/digest, accepted/valid and fault destinations where connected. The ledger includes the five final-predicate publication inputs, rather than assigning only visible state bits. An actual sink remains one endpoint even when it influences several state fields. Source outputs remain explicit unknown-cap aliases; none is assigned an invented external load.

All 256 original transparent cells are actual INVx1_ASAP7_75t_R. The model verifies each root has at most one original inverter and no inverter cascade. It retains the original polarity graph and adds four INVx1 cells for the extra negative-root 1333 publication cohorts. Thus no double-inversion cancellation changes Z propagation. The final NAND and its inverter preserve the exact positive/negative acceptance publication, instead of treating an inverter as a new independent source. Every FF QN polarity, all 145 DFFASRHQN cells, canonical D feedback, asynchronous RESETN and literal-one SETN remain unchanged.

## Concrete source strategy that can survive mapping

A future private implementation would instantiate the **actual native combinational masters** with stable pub_<root>_<cohort> names and explicit kept ownership, preserving the rest of the native graph. The library cells must remain native black-box primitives through elaboration/ABC; the proposal does not rely on repeated Boolean equations surviving common-subexpression elimination. The exact gate functions and source/native correspondence are already pinned in a42894e3f; the new publication's source inputs are the same original native signals, not cloned state or a rewritten reset cone.

The reviewed implementation must assert actual post-elaboration instance/master/port identities and the complete graph census before claiming retention. A keep/dont_touch attribute alone is not proof: any optimizer merging cohorts, removing required state/polarity, introducing a shared high-load publication, or changing a sink assignment is a refusal. Source attributes and any flow hook needed to preserve the explicit native instances require a separate ROOT grant. This packet provides a complete structural ownership model, not that implementation or a generic RTL optimization claim.

## Full upstream fixed point and actual cell costs

Splitting all five predicates adds 80 logic input pins. Each of the 20 upstream source roots gains four effective sinks. Four are sibling predicates: 1109/1194/1331 grow132→136 and1332 grows131→135, then distribute across their own five publications. Fourteen earlier native predicate roots grow1→5. Actual receive_slot and actual fault-QN grow3→7. The next complete graph pass adds no further gate copies. full_upstream_ledger preserves every source support, old/new count, actual sink capacitance and proposed owner; all_publications covers the entire component, not only these 20 roots. No primary input or state source is cloned.

| Added actual native cell | Count | Bare-cell area um² |
|---|---:|---:|
|NOR5xp2_ASAP7_75t_R|8|0.816480|
|NOR4xp25_ASAP7_75t_R|4|0.349920|
|AND2x2_ASAP7_75t_R|4|0.349920|
|NAND4xp25_ASAP7_75t_R|4|0.349920|
|INVx1_ASAP7_75t_R|4|0.174960|
|Total|24|2.041200|

The complete modeled graph is1109 cells, including the unchanged145 FF and260 inverters. Added physical signal-input pin capacitance is41.231964 fF TT /45.754488 fF FF; this counts the80 gate inputs plus four inverter inputs. Added clock/reset/SETN sinks and added cycles are all zero. Native PG declarations increase2170→2218 (+48); source graph PG bindings are absent and physical ITerm membership is NULL. Cell area excludes placement, CTS, wiring, rails and tie distribution. No dynamic energy, timing gain or token-rate credit is inferred.

## Electrical bounds from the pinned native libraries

native_lib_records.json contains exact real TT/FF master area and pin records with hashes of the native inputs. TT is the actual canonical merged all.lib hash7110a7a75b4d2802053266c170bed511640a53d1c85ba9e43939fd4cb8dfe817. FF uses exactly the five AO211120, OA211120, SIMPLE211120, INVBUF220122 and SEQ220123 files matching the original ten-library HBM receipt. Each hash is verified before extraction. Broad platform inventory also contains other versions and FAKE libraries; these are explicitly excluded from the extraction and are not mapper/model dependencies.

Bounds use the maximum available capacitance/rise_capacitance/fall_capacitance for each real sink, conservatively, at each corner. Actual Liberty output max_capacitance supplies each limit. The model includes an inverter's real input cap on its source driver and checks the inverter's separate output load. BUF/INV traversal never creates an independent fanout root. Neither unit loads nor synthetic FFs are used. Wire capacitance is NULL.

The original four definite TT failures are retained verbatim: native1109 61.777828>23.04 fF;1194 61.738084>23.04;1331 61.468628>23.04; and INV output1334 59.874375>46.08. These original values use the original census's capacitance attribute; modeled bounds use the conservative max of all three attributes. In the proposed cohorts, maximum direct root input load is15.383552 fF TT /17.037714 fF FF, below even the23.04 fF root limit; maximum inverted-publication output load is13.569664 fF TT /14.905568 fF FF against46.08 fF. Every actual per-publication bound remains in model.json.

**This is an internal known-load model, not electrical closure.** The 677 component inputs and161 output aliases retain their actual original boundary correspondence. Parent feedback versus true external consumption, optimized shared predicates, actual per-bit driver/slew/arrival, external loads and wires remain unresolved. Aliased outputs are not assigned fabricated caps, and internal feedback is not counted again as external. All external drive/cap/arrival ownership remains HOLD; no standalone or parent STA is eligible yet.

Clock, rst_n and SETN each retain145 loads. Their conservative known input-cap sums are67.120355/72.957040 fF (TT/FF clock),107.269550/116.421805 (reset), and156.520250/168.846700 (SETN). Primary driver/tie max caps and actual upstream distribution are unknown; these are unqualified roots, not PASS. No tie cell or reset relay is invented. PG continuity, recovery/removal, native placement, local macro contacts, reach and actual routed clock spread remain unqualified.

## Arbitrary-state proof and causal-control plan before adoption

No new simulator or formal implementation run occurs in this model task. Finite generator checks verify exact five FF-library identities, the complete native graph/pin ledger, single-inverter polarity paths, full upstream fixed point,80 added gate inputs,24 added cells and preserved145 state cells. Running python3 model.py reproduces the model using the pinned prior packet and extracted native-library records.

1. Construct the future all-output next-state miter from **actual resulting native instances and exact Liberty functions**, keeping all677 input bits and145 present-state bits arbitrary; compare all161 output aliases against76277 and the original mapped Candidate A. Preserve the actual DFFASRHQN ff(IQN,IQNN), !D next state, !SETN clear, !RESETN preset, QN function and simultaneous clear/preset behavior. Reject state merges, altered clock/reset/set connections, unsupported primitives or lost source correspondence. No async2sync and no reset-reachable-only assumptions.
2. Independently prove the old/new native combinational graph under a symbolic four-value encoding0/1/X/Z with exact primitive functions and procedural capture semantics. Then assess source/native four-state correspondence separately:76277's109457 source simulation checks and a428's binary native SAT do **not** establish arbitrary four-state source/native equivalence. Unknown-value differences must fail closed; no X-as-don't-care optimization, unknown-to-zero substitution or inferred native timing semantics is accepted. Retain asynchronous assertion/clock-edge test cases separately from combinational/next-state equivalence and from analog reset recovery.
3. Exercise exact acceptance/epoch priority and arbitrary retained image/state, BEGIN/activity, slot mismatch, reserved field142 and511, digest/epoch/cap changes, head stage/token/position and reset/SETN polarity. All public effects stay on the original edge, with no independent state clone or first-edge convergence assumption.
4. Require actual causal controls against the implemented graph: invert one chosen publication's polarity; wire one cohort to a wrong predicate; omit one real digest/epoch/reserved contributor; introduce an early/sticky accepted pulse; change BEGIN priority; alter native SETN/reset polarity; and deliberately merge two cohorts into one high-load root. Functional controls need observed output counterexamples; merging requires a structural/fanout rejection even when equations remain equivalent. A control producing only a harness/import error is not a causal failure. Preserve all original logs and every refused/failed new case.

ROOT review of this concrete model is the next dependency. Any implementation/proof/mapping or physical job requires a subsequent explicit grant and measured resource inventory. No full-parent benefit or production activation follows from the finite model.
