# Private SYSFACE native publication source

**Private source and native preservation proofs PASS; source/native four-state equivalence FAIL; parent and physical adoption HOLD.** The exact 8f1962c1a model is implemented as 1109 explicit native instances. Five predicate roots each have five owned publications. This adds 20 native gates, four native INV cells and 2.041200 um² bare-cell area, with zero state or schedule edges. No production source, flow hooks, ABC, implementation synthesis, P&R, parent STA or producer integration was changed or run.

`private_source_proof.tar.gz` contains the frozen native source, full inputs/model, all generated miters, raw proof logs, exact tool/image/library receipts, initial refusals, causal output witnesses and final census support. `summary.json` provides results and output-level witnesses. The uncompressed working evidence is `/home/ubuntu/artifacts/qw-sysface-publication-source-1019`; all remote jobs are terminal.

## Exact source, elaboration and upstream ownership

The starting graph is actual Candidate A from a42894e3f, corresponding to source 76277b2cb32db263d527bb1e7c66ae91754f2ef1. TT merged native Liberty is SHA256 7110a7a75b4d2802053266c170bed511640a53d1c85ba9e43939fd4cb8dfe817. Every used master output function, FF record and PG declaration is independently checked against that actual Liberty and the native semantics packet; unsupported functions or FF changes refuse. No generic cell model is substituted.

`initial/publication_native.sv` contains actual native master names and explicit named ports, with kept publication identities and exact terminal ownership. Native primitives are black boxes during source elaboration; their real functions are used separately in the proofs. All 145 original DFFASRHQN identities, canonical state correspondence, CLK, RESETN, literal-one SETN, QN polarity, and output aliases are preserved. All original inverter identities are retained and four new cohort inverters are added. No double-inversion cancellation changes Z propagation.

Yosys reads the source and writes its actual elaborated native JSON. The checker requires all 1109 instance/master/port identities and every connection to match under a bijection of net IDs. Literal escaped dollar identifiers acquire a representation backslash in Yosys JSON; the checker normalizes only that known representation when the exact original identity exists. The original refusal is preserved. There is no optimizer, ABC or mapping pass and no inferred retention claim based on attributes alone.

The final full graph census includes primary inputs, literals, all state roots and all logic roots, traversing every INV transparently. Every known logic publication has at most 32 actual nontransparent terminal loads. It independently counts the actual 80 additional gate inputs and four additional INV inputs. The complete model upstream fixed point and all sink ownership remain in the bundle. A deliberately merged cohort drives 64 terminals at pub_1109_0 and is structurally rejected even though the Boolean equations are unchanged.

## All-output binary and symbolic four-value proofs

All 677 data input bits, binary rst_n and all 145 present-state bits are arbitrary. No reset-reachability, valid-transaction or initial-state assumptions narrow the binary proof. Clock is a transition label, not a data predicate. Two SAT miters compare all 161 resulting output bits, including the derived 16-bit host epoch:

- Exact Candidate A source next-state versus implemented native equations: PASS.
- Original native graph versus implemented native equations: PASS.

The native FF is taken literally from its Liberty: ff(IQN,IQNN), next_state !D, clocked_on CLK, clear !SETN, preset !RESETN, simultaneous clear/preset variables L/L, and QN function IQN. The sampled binary equations preserve the asynchronous control values. They do not claim analog recovery/removal or arbitrary unknown-reset event equivalence.

A separate symbolic SAT miter encodes every scalar as 00=0, 01=1, 10=X, 11=Z. Exact Liberty primitive expressions use the complete four-value NOT/AND/OR/XOR truth functions; X and Z remain explicit symbolic values and are never coerced or treated as don’t-care. It proves equality of all 145 actual FF D terminals and all 161 current native output aliases: **PASS**. This establishes old-native/new-native combinational preservation for arbitrary four-value inputs and state encodings. The identical FF types, event relations and asynchronous control pins are independently retained structurally, so no invented sequential native X model is needed. No async2sync is used.

## Actual causal controls and existing source/native X mismatch

Seven mutations change actual native implementation terminals and yield real all-output SAT counterexamples: one cohort polarity, wrong predicate, omitted digest contributor, early acceptance pulse, ignored BEGIN, missing reset and altered SETN. Both 161-bit old/new output vectors, changed output names and all witness inputs are retained. Merely returning nonzero or producing an import error does not count. The separate merged-cohort control fails the structural 32-load rule at 64 loads.

**Source/native four-state equivalence is demonstrably false.** Host Icarus11 executes the exact prior source next-state text and exact native Liberty equations. With all retained state and other inputs zero and rst_n=1, receive_slot=X or Z, or rx_v=X or Z, produces source fault=1 while native fault=X (result bit16). Four actual output witnesses are retained. No unknown is masked and no native or source semantics is repaired. These are sampled combinational/next-state witnesses, separate from asynchronous event timing.

The prior 76277 source-only sequential evidence retains its original 109457 actual four-state checks, including asynchronous reset assertions and X/Z reset events. That prior source/source scope is unchanged; it never established native/source four-state equivalence. Native/source asynchronous X histories and analog reset qualification remain unproved. Native publication preservation does not grant source/native X equivalence.

## Measured execution and remaining holds

All simulation/formal work used automatic unpinned ot-run admission: one CPU, 4 GB memory and 2 GB disk reservation. Actual placement used ot-epyc6/7/8; no host was pinned. Initial source/native binary SAT took 0.67 s /63616 KiB peak RSS; old/new native binary SAT 0.97 s /86676 KiB; symbolic four-value SAT 51.22 s /1593772 KiB. Exact raw per-stage resource and host receipts are included. The native image is actually inspected per run; Yosys binary SHA and version are recorded. A diagnostic initially found Icarus absent inside that image and remained explicitly UNRESOLVED until host Icarus11 ran with its own executable hashes. The initial extended host census could not replace a Docker-owned output; the same finite census then passed inside the original container. All refusals are retained.

Each of raw clock, reset and SETN still drives 145 sinks; upstream distribution and real driver limits are unqualified. Logical native PG declarations total 2218, while actual physical bindings are NULL. External load, per-bit driver/slew/arrival, wire capacitance, reset landing/first use, placement/reach, TT/FF timing and routed clock spread remain HOLD. No timing improvement or token-rate benefit is inferred. The old parent TT −57.924 ps /833.5 ps /28-level failure and original a428 unsafe/electrical failures remain immutable. This packet is private structural source and scoped preservation evidence, not an adoption, submission or closure result.
