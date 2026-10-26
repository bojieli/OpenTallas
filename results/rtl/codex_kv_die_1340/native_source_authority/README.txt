S6C source authority correction, captured c652/5dd composition

Preserved terminal failure: ep5 unit3230539 exit1 refused the active assembly's wire-shadow GRP_H definition instead of accepting the selected registered native source. Facts/window/physical were NOTRUN.

The opt-in S6C emitter now omits only the two GRP wire-shadow declarations. It still emits the six other tile modules byte-identically. Non-S6C emission is byte-identical. Real group tile placement, connections, ports and BINDINGS remain intact. sources() includes both actual native source files. The checked-in active assembly is source-only re-emission from its eight original module_text records, using the actual patched rtl_text function with those records; no all_tiles geometry rebuild or full GEN occurred.

The active-readset guard rejects native S6C redeclarations even when parser preference would select the genuine file. Existing missing-file, one-declaration and selected-index-path checks remain strict. Both actual strict-check passes explicitly receive the real native files after the generated assembly. Source tests index actual native structural bodies, default parameters and ports, and retain the resulting native hierarchy map. The existing native implementation and closure views are not edited or requalified here. Standard-cell/memory hierarchy dependencies are recorded, not waived.

Publisher must apply ONLY the three tool hunks in source_patch.diff plus the updated generated artifact and evidence. kv_static_die.py comes from captured c652 and differs extensively from current main: do not overwrite main with this complete old generator file. manifest.json pins all changed paths and original/native source hashes. No registered logic, gate wrapper, parameters, ports, clock/reset edges or schedule ages are changed.

This packet does not establish whole-die strict bind, actual-pin safety facts, STA, physical materialization of the 109-bit CTL, native PHY clock references, coherent73 ages or release closure. No fullGEN or physical continuation has been launched. Unit3230539 remains a failed required stage; its original objects are preserved.
