# WBK q2 takeover preflight

The previous q2/q2b layout attempts stopped at source packaging: tracked stn_pin_keepout.tcl was absent from the sparse source archive. This checkout materializes it, but the source remains ineligible for layout.

Unchanged q2 at WOPEN0/MUT0/FAW3 was synthesized and mapped to actual ASAP7 standard cells and the real payload macro abstract. The current mandatory census implementation reports311111 roots,2219 dynamic violations, maximum232, zero Liberty-role errors. There are16 offending input ports (w_k_rdy up to49),1170 combinational/macro roots and1033 sequential roots (up to65). Leading fanout cones are16 skid in_v signals212..232. The full raw report is retained compressed, with mapped image hash and source/helper hashes. This is a standalone preflight, not an in-gate ORFS PASS.

The first tooling attempt failed because standard library files were compressed; mapping then succeeded after explicit decompression. A missing textbook_lint import in the original small archive was corrected and only census rerun against the same mapped image using current helper bytes. Original remote failure logs and objects remain.

Layout model also rejects the inherited eight-high stacks: the macro is94.824x41.04um; row pitch41.04 leaves zero vertical channel and nonliteral43.2 origins. A literal86.4 vertical pitch with45.36um channels grows the simple4x8 outline to777.6x820.8,1.58x area. This is a capacity bound, not a placement design. Exact full-cone region assignment, multi-root clocks and source area band sizing remain required.

Next source task: partition ready/pop/skid controls into real kept local predicate/data slices, preserve every consumed value/handshake and actual write-set protocol, and bound reset/synchronizer loads including D+RESET contacts. Any added edge must enter the production fence/throughput model and die compiler. Use new opt-in modules, preserve legacy source bytes and failed evidence. Pre-gate actual mapped census must pass before any layout.
