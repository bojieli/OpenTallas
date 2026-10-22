# EMB3: reject conflicting allocation contexts before publication

Source d9631325d diagnosed an early owner but still published its start/token/epoch and retained owner; any later owner could restart after sticky fault. This successor uses one shared admission predicate for every publication register. Prior fault, early gap and an existing open row refuse publication and latch/retain fault. There is no queued request, retry, credit or variable schedule. The wrapper feeds the existing row transmitter armed state back as a local static overlap veto.

`qkd_embedding_row_tx_ctx` copies the actual released row body and adds only an armed diagnostic output. The public row source remains byte-identical (source_identity.json). This is a private opt-in context-wrapper successor requiring fresh native qualification; it does not reinterpret an old CLOSED view as the new module. Price/model: MODEL.md; 0 additional flops, 1 internal diagnostic wire, ctx input +1 / row output +1, wrapper external interface unchanged, 0 added edges. Current source 207-flop ctx price is not a mapped total.

## Actual component evidence

- Initial strengthened bench on the exact old source: FAIL early owner changed publication and sticky-fault context restarted publication. Original d963 PASS witnesses remain untouched. Initial minimal repair legal four-row PASS and original four mutants caught (ep7 unit605923, controller exit0).
- The source-composition fixture uses the actual MU allocator request_valid&&request_ready admission, real grant TAG59/generation, canonical qkd_host_native_context_tx, independent qfd_host_native_context_rx, context tap and the real SRAM row transmitter body. Four allocations cover prompt tokens 7,11,11 on user0 and one user1 token4242. Each starts from an accepted real grant; the independent compute RX full61 owner equals the retained context full61 owner and the intended allocation tuple.
- Final Verilator5.050 suite (ep6 unit758142): legal case PASS; all seven separate causal mutants FAIL: repeated-owner suppression, wrong token field, missing header epoch check, missing kind check, missing sticky-fault veto, missing row-open veto, missing early-gap veto. Runner checks each positive/negative result and returns0 only for the complete suite.
- Final Icarus12 four-state legal fixture PASS (ep6 unit808758). Resets begin high and actually assert low at0.2ns; this avoids the declaration-init/no-negedge false reset used by earlier unrelated AHUB attempt1. No unknown control or payload is masked in the row comparisons.
- Every legal row checks 64 full 512-bit payloads and its scale/header, plus existing armed state remains high before every slot and clears only after the 65th slot. Four real allocator terminal acceptances follow final row drain. These are component-source dates, not a token numerical simulation.

The seven-calendar AHUB proof and gates are separate from this packet. No full attention or arithmetic claim is made here.

## Exact scope and remaining integration

Full owner61 is retained locally and independently checked at compute context RX. The existing row header carries token18+epoch16, not generation/stage/position; this packet does not widen it or claim full61 is returned in each word. Correct allocator lifetime/wrap fence and no overlapping owner reuse remain production obligations. Program-ready/image constants are a preinstalled fixture assumption, not proof of real programme installation. Join words are driven at the row's word face: actual PC/read/join calendar, physical D2D, compute E installation/final-scale consumer drain and all-row source costs remain pending composition.

An open row on the context-consume edge refuses even if the same edge sends its final record: armed clears after that edge. The compiler must place the next context later. The guard never waits for the row to become free. MIN_GAP66 is only an additional consistency floor. HOST RESULT→true accepted allocation→kind12 slot H and actual fork+2+join-last+1 F remain NULL; no adoption of the current too-early K3 context prefix, no automatic use of170−H fill budget, no token-rate or four-user-token PASS.

Reproduce the final frozen fixtures with final/run.sh and final/fourstate.sh on admitted fleet hosts; inputs are source-pinned copies. The intermediate revision2 runner correctly exited4 because its independent-owner fixture did not exercise AUTH for kind-check mutant4. That missing negative was added in the final fixture; no revision2 result is claimed as a suite PASS.
