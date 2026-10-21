# Qwen fault source bit geometry

Parent4209f0dbb. Candidate optin OT_SPLIT_FAULT_SOURCE_BITS=1; defaultoff. No fullGEN/gate/submission launched by this lane.

The original r7af GEN failed fault_emit.post with70newfaultwires over405um. Full originalfailure retained. The earlier dvw_st_wi P2R22/23hop failures were intermediate: both r6b/r7af repaired the word to104stages with actual worst pin-to-pin371.5um. No data-corridor successor was justified by the intermediate status.

Minimal actual source/master reproduction uses r7af's source RTL, native_static_io_bind.install_master, and the exact production tp8b_v5.pin_rects adapter extracted from that pinned file. The70collective hardfaultbits match the original failure count. A disconnected port has emitted width0, so _pin_pos's non-strict accessor falls back to the block centre(781.908,12049.548). After physical partitioning, the whole port is removed; mapping scalar fragments back to that absent wholeport likewise loses physical identity. Actual fault_code[0] isE-face(1563.72,12120.396), distinct from every other bit. Reproduced centre substitution errors852.66..890.10um. These are assigned native-source pins; no CLOSED collective view is asserted.

The candidate registers scalar fragments before constructing/fixing the source masters. Exact emitted fragment or numeric-real-bit geometry drives pre-cover placement, post capture-node placement and final strict per-bit audit. It never substitutes a port or block centroid. It preserves the real RTL port+bit identity across both physical emission naming modes, fails missing/conflicting geometry, and adds actual hard fault pin points to the pre-cover plan.

Fleet proof gold1unit1757279 exit0 verifies all70unique exact bit positions under both scalar alias and EMIT_SPLIT numeric-bit naming, plus missing/conflicting geometry negatives. A bounded model over all22489actualr6bGENplacedframes finds five nonoverlapping21.6um capture boxes, fanin<=16, with actual source-bit toW-faceinput-pin distances<=153.9um. Exact positions/wires retained inCAPTURE_MODEL.json. This reference includes actual data/reset occupancy; r7af fault roots are not included. It proves a concrete capture-site model, not the final full fault tree.

FullGEN adoption remains owed: all hard-source families, final fault-tree roots/edges, real clock/reset bindings, strict bind/native checks and priced cycle counts. The original70wireFAIL remains aFAIL. No timing limit or reach gate was relaxed; no branch was merged to main. Q-DIE owns a qualified structural successor after review.
