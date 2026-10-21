# S8 local source-role guards — candidate, native qualification pending

Source base: `363295685`. This candidate addresses MAIN native roots `_335317_`/`_335322_` (RP guard, 526/1053 loads) and `_339454_`/`_345670_`/`_345718_` (FDN publication/command guards, 69/81/33 loads). It introduces real kept combinational AND and ternary cells and partitions their consumers; all existing registered state, capture edges, reset behavior and procedural priority remain unchanged.

RP uses three two-input partial products and 69 distinct final guards, each equivalent to `rp_arm && dd_q[519] && dd_q[518]`. Each partial product drives 23 guards. Data is partitioned into 64 sixteen-bit ternaries, address into three eight-bit ternaries, and kind into one two-bit ternary. The original scalar control equations use guard64. The original inputs each drive 25 predicate inputs before their other existing consumers. These are source-model counts, not measured native counts.

FDN separately guards command tag, watermark and counter fields, plus outgoing tag/metadata ternaries. The original 547-bit outgoing ternary is decomposed with exact field provenance; identical branch bits are direct aliases. All conditional selectors retain Verilog four-state ternary merge. Counter and watermark arithmetic widths remain 16 bits; counter load-before-increment priority remains intact.

Persistence: `gen_slice8_rp_source.py` owns FDN generation; its extracted `fdn()` entry regenerates the checked-in file byte-for-byte. RP is its existing hand-maintained source, not an output of that generator. Helpers have private module names and actual equations, with no black boxes or constraints.

Executed light model: `python3 results/arch/q_s8_local_guards_1021/model.py` checks 64 four-state guard triples, 3072 ternary comparisons, 64 header associations, 16 procedural-priority pairs, all 547 field provenance positions, partition coverage, unchanged register declarations, and source hashes. Generator byte identity and `git diff --check` pass. This is a mechanism/field model, not executed full registered RTL equivalence. Actual fixture equivalence and combined native qualification belong to cb16. ABC preservation and actual fanout must be measured before adoption.

Remaining coverage is explicit: three math OAI roots (35/36/35 loads), TAP roots (separate cb16 repair), and fallback physical rs_s/rs_n/l9_i valid inputs (57/64 loads) are not repaired by this patch. Hold combined native until those source remedies are ready. No physical, timing, clock or release qualification is claimed.
