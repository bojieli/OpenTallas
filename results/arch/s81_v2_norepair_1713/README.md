# V2 fixed no-repair SRAM view

This is a new fixed-configuration master. The old 2-row/2-column spare hardware and outline remain; the repair selectors are permanently zero inside the behavioral view. It removes 32 repair input bits per store without claiming area or cycle savings.

Regular pin rectangles, pin table and TT/FF regular timing blocks compare identically to the original master after normalizing the module name. The viewed planning overlay is in results/geom_review/kits1713/v2_norepair.png. The model miter compares 12000 reads, including 3381 same-address operations and 8628 masked writes. Both wrong-mask and wrong-read-address controls are caught. No physical SIGNED result is claimed.

Reproduce the miter with Verilator 5.050, the original and new behavioral .v files, tb_fixed_repair.sv, --binary --timing -O1 --top-module tb_fixed_repair -GMUT=0 (then 1 and 2). Expected baseline PASS, controls FAIL. The detailed counts are in view_audit.json and m0/m1/m2.log.

The source-only delta changes 136 type entries / 150 placed macros, removing 4800 planned input pins with identical outlines and locations. The actual bind has 160 VP stores / 5120 repair bits: ten macros in the five KV leaf families still need honest physical decomposition declarations. The manifest_patch() output is a proposal for the parent batched manifest; it is not automatically applied. Require a fresh strict bind proving 160 replacements and unchanged unrelated proof counts, new affected parent kits, and physical qualification of this new master. Old signoff cannot transfer.

G0 of the delta against the canonical plan context: PASS, 0 errors, 1273 warnings, 171 types / 398 partitions. Initial scratch-context check failed solely because relative census files were unavailable; the canonical-context check is the reported result.
