# Qwen fault source bit geometry

Parent4209f0dbb. Candidate optin OT_SPLIT_FAULT_SOURCE_BITS=1; defaultoff. No fullGEN/gate/submission launched by this lane.

The original r7af GEN failed fault_emit.post with70newfaultwires over405um. Full originalfailure retained. The earlier dvw_st_wi P2R22/23hop failures were intermediate: both r6b/r7af repaired the word to104stages with actual worst pin-to-pin371.5um. No data-corridor successor was justified by the intermediate status.

Minimal actual source/master reproduction uses r7af's source RTL, native_static_io_bind.install_master, and the exact production tp8b_v5.pin_rects adapter extracted from that pinned file. The70collective hardfaultbits match the original failure count. A disconnected port has emitted width0, so _pin_pos's non-strict accessor falls back to the block centre(781.908,12049.548). After physical partitioning, the whole port is removed; mapping scalar fragments back to that absent wholeport likewise loses physical identity. Actual fault_code[0] isE-face(1563.72,12120.396), distinct from every other bit. Reproduced centre substitution errors852.66..890.10um. These are assigned native-source pins; no CLOSED collective view is asserted.

The candidate registers scalar fragments before constructing/fixing the source masters. Exact emitted fragment or numeric-real-bit geometry drives pre-cover placement, post capture-node placement and final strict per-bit audit. It never substitutes a port or block centroid. It preserves the real RTL port+bit identity across both physical emission naming modes, fails missing/conflicting geometry, and adds actual hard fault pin points to the pre-cover plan.

Fleet proof gold1unit1757279 exit0 verifies all70unique exact bit positions under both scalar alias and EMIT_SPLIT numeric-bit naming, plus missing/conflicting geometry negatives. The final capture check (gold1unit1765420 exit0) uses actual make_master/pin_rects input-pin quantization, not nominal face coordinates. A bounded model over all22489actualr6bGENplacedframes finds five nonoverlapping21.6um capture boxes, fanin<=16, with actual source-bit toW-faceinput-pin distances<=153.912um. Exact positions/wires retained inCAPTURE_MODEL.json. This reference includes actual data/reset occupancy; r7af fault roots are not included. It proves a concrete capture-site model, not the final full fault tree.

FullGEN adoption remains owed: all hard-source families, final fault-tree roots/edges, real clock/reset bindings, strict bind/native checks and priced cycle counts. The original70wireFAIL remains aFAIL. No timing limit or reach gate was relaxed; no branch was merged to main. Q-DIE owns a qualified structural successor after review.

## Actual DV frozen-master stage correction

The first authorized r8bfp fullsource run failed early: fragment flt_fault_code_0 missing from the selected collective master. The first fixture rebuilt masters when port_join changed; actual dv_case.apply_dv instead freezes its final physical M dictionary before fault_emit.pre. Merely changing aliases therefore did not update the selected master. This original early failure is preserved in original-r8bfp-pre-fail.log.

The correction partitions copies of the already-selected physical masters using their exact existing native pin rectangles. It installs an outer master projection without changing the originals, regenerating pin assignment from peers, or replacing future relay masters. The projection is scoped to the actual model object.

The bounded frozen-stage fixture (gold1unit1820709, exit0) reproduces the original missing-fragment error with source1c1d45f73 and then passes with the corrected source. All6980collective physical rectangles are identical before/after canonical real-bit mapping; original selected objects remain unchanged. Both alias/numeric emission modes and the capture model still pass, with max153.912um. The original source used by the causal failure check is fault_emit_old.py, pinned to1c1d45f73.

The corrected actual r8 fullsource PRE-only interception PASSed (gold1 unit1889817-1792605471, exit0). It directly calls the already-patched selected builder and verifies hook/module identity. All81 hard fault source bits across five actual frozen masters pass; all14168 physical pin rectangles are identical after canonical real-bit mapping, and the selected originals are untouched. The model has334 roots/333 tree edges; execution explicitly stops before all relay planners. ACTUAL_PRE.json retains the complete81-bit source contract, five master checks, exactflags/source and candidate SHA9fd4fb9a0ee3f54fa5a4942337fb1739b5d103550874f7081bfeb59cec1cf49e.

The first PRE driver incorrectly used die_top_lint.load_qwen(), which reimports qwen_rom_fulldie and bypassed the relay interception. It entered P2R; only its confirmed own PID1844840 was terminated immediately when diagnosed. That run is invalid as PRE evidence and its log is retained separately. preonly.py and pre_run2.sh/pre_launcher2.sh retain the corrected direct-selected recipe. No full successor was launched by this lane.

Old-source r7bf separately terminates with two fault-tree site/reach failures (flt_t_d2d_rom_g5 682.4um andg4 496.8um). These are additional qualification obligations; PREPASS does not claim the full tree works. A same-source bounded interception is retaining root/frame geometry for exact structural classification before any successor.

The bounded root snapshot and actual occupied-reference model now pass: both old residual edges become same-clock direct wires215.136/293.568um after actual-source cover placement. SeeROOT_MODEL_RECEIPT.md andROOT_MODEL.json. This qualifies the one authorized exactr6bFAULTtwin source candidate, with fullchain obligations retained.
