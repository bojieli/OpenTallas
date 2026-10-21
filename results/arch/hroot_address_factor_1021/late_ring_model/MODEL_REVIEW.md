# One late-ring/CSA model selected by ROOT; production qualification still open

This directory is a combinational proof/model vehicle, not shipping engine RTL. SAME four-final-address projection, same five exact TT vendor libraries and Yosys0.67/image16470cea, same ABC and textbook parser4adb/scalarweights were used for frozenoriginal, CURRENT aa6 prefix baseline and ONE late-ring/CSA candidate. Full source and map logs/netlists are retained. No output mux/state/FF reconvergence, wires, slew/load or STA is represented.

| max over four addresses | scalar ps | levels |
|---|---:|---:|
| frozen original |1230.2|37|
| current prefix baseline |1201.9|35|
| late-ring/CSA |823.5|25|

Compared with CURRENT baseline, overall model improvement is31.5%; CODE1201.9->793.5,ROWS1170.2->823.5,SCALE1143.6->786.8. This does not predict the production map or recover real -810.5ps by itself. The actual production map, original real output budget and required selected-wrapper proofs remain necessary before physical admission. e5a is held. ROOT selected this one candidate for production implementation; APIPE1 remains a separate model-only alternative.

## Exact four-state mechanism and scope

The model retains the original equations s_local, s_rbase, s_raddr, k_blk, k_code and k_scal with original Verilog ternary and every original arithmetic boundary. Their final outputs are final0=base+row, final1=raddr+sec, final2=kcode+phase and final3=kscal+(phase==4?1:0). Each is itself a32-bit arithmetic +, not a ?: output merge. Verilog + with any unknown operand produces an ALL-X result; otherwise that result is entirely binary. Thus (^finalN)^(^finalN) is0 when original final is whollyknown, X when it is allX. XOR replication onto the separately computed CSA result restores that exact pessimism. The original ternary's partially-known merged operand flows into ORIGINAL arithmetic before knownness is measured. The model does not poison s_local itself and does not poison a production output conditional merge. A future production implementation must apply this per-arithmetic-alternative witness before the unchanged state/enable/output mux, not blanket-poison a muxed output.

For binary inputs, the witness is identically0 and branch distributivity/modulo32 CSA arithmetic establishes the intended equality. Unknown ring with equal merged operands is handled by the original witnesses, rather than assuming ring isbinary. No masks/don't-cares/init assumptions or simulationifdefs are used. Hardware binary synthesis may eliminate these self-XOR witnesses; the mechanism matches RTL pessimism and is not a mapped-cell cold/init theorem. Mapped aliases/diagnostics need independent qualification.

Bounded Icarus source comparisons:6328 vectors/25312 four-address comparisons PASS, including isolated X and Z injection into each331-bit input on8backgrounds plus1024random binaryvectors. This is not universal whole-state or source equivalence. Source algebra/knownness review remains distinct from this sample result. Original native/source-specific cold receipts539 remain separate; none is silently carried to new production code.

Warnings: original and candidate ABC retain combinational-network and multi-output-FA notices; candidate14helpermemory-array lowering messages retained in full maplog. No driver warning is waived. First service launch failed before source due wrong cwd; log/journal retained, corrected bounded map completed. No physical gate, parent simulation or native campaign ran here.
