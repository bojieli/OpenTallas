The executed EN1 placement hook anchored zero flops

The actual GPL receipt reports zero output and zero input port flops, with 1,026 ports skipped. This is not fixed by increasing HOPS: the kit already uses eight. Executed physical/qwen_die_masters/io_flop_at_pins.tcl rejects the INV candidate in ot_of_fbonly, which requires immediate DFF. The original mapped feedback cone itself is two logic cells, so merely peeling the inverter will still fail the helper's direct feedback-to-D test.

For q[334], source mapping is FF QN → INV _1738_ → q. Feedback q feeds AND2 _3121_ A; its B is inverted registered enable. AND output feeds AO21 _3122_ B, with A1 true registered enable and A2 d[334]. AO21 Y goes to the same FF D. Enable true/false trace only buffers/inverters back to the same registered ME QN with opposite polarity. Thus D = enabled ? d : q. The runtime output-hold chain branches at q and is separate from this feedback cone.

Safe opt-in recognition criteria for the shared-flow owner:

1. Continue allowing only BUF/INV/HB on ordinary port chains. Find exactly one candidate FF behind the output-polarity chain.
2. Accept an extra output fanout only after proving an exact own-register enable mux. For this mapper, require an AND2 feeding AO21 with the documented pin functions, then one net ending only at the SAME FF D. Verify all intermediate fanouts; reject any additional consumer. Do not accept arbitrary gates based on reachability.
3. Prove that the feedback input originates at the candidate's Q polarity and the data input traces through a unique single-fanout BUF/INV/HB chain to exactly one normal input port. Prove the two enable controls trace through BUF/INV only to the same root with opposite polarity. If the root is a registered ME, verify its actual clock association; never traverse a clock or substitute a free-running behavior.
4. Recognize the input endpoint by reversing the same already-proven mux cone, not by accepting any AO21 sink.
5. Reject ambiguous candidates, multiple outputs/inputs, unknown Boolean functions, extra side fanouts, excess traversal depth, or cycles beyond the one validated feedback edge. Emit a reason and counts.
6. A paired d/q register cannot be independently fixed twice. Collect its pin pair, choose an explicit placement priority (q for the launch-bound repair), and assess both resulting pin-to-register distances. Do not let BTerm iteration order silently decide. A bit-aligned d/q pin plan is a separate structural candidate, not proof of timing closure.

No shared helper is edited in this evidence commit. The shared-flow owner must add focused positive and negative graph tests and replay the original EN1 gate with unchanged 80 fF, H100, ME semantics, clocks and waveform. The actual corrected placement and TT/FF/SS endpoint oracle must determine whether the candidate meets its boundary bounds. This diagnosis does not authorize removing output hold cells, using ICG, or claiming slot adoption.
