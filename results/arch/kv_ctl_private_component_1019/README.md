# CTL private functional component

Source grant only: 2c8fa49b3 + 4612f5967. Pre-edit manifest 5781bff96 precedes RTL e486f9e6a. Functional source is exactly c5fbbded9; integration branch begins at efae17de2. This is not the selected 5f2ce19bc writer/programme ABI. No root binding or native graph adoption is implied.

The two private modules retain their original parameters plus ENABLE=0. The programme has no functional edits. ENABLE=1 changes only the writer SRAM read CE from raw start_p to the exact accepted-start predicate including reset_pin_n. SRAM=0 remains the original default. No table shape, mask, output, captured identity, reset, fault priority or edge was changed. Static reverse-diff recovers the originals byte for byte.

The original behavioral 128x256 memory source is used with OT_MEM_NO_INIT. Its single-clock registered read-before-write and per-bit write mask are functional simulation behavior, not a new dual-clock OLD contract. Actual primitive simultaneous-access write integrity and physical access remain HOLD. Dense original macros are not certified safe.

Source inspection identifies the noninterference obligation: only ld consumes writer rt0..rts. An accepted start issues the row read while setting ld; the following edge consumes the prior registered result. A rejected read cannot create ld. A second illegal start during active/ld still must preserve the prior accepted read result at the consuming edge; nonblocking read capture is material. Fault remains sticky, and reset discards ld and requires a complete ordered boot and seal before another accepted use. These are source obligations for the bench, not a completed equivalence proof.

The independent minimum bench must compare every public output on every edge for original versus ENABLE=0 and ENABLE=1. It must preserve the raw collision/rejected-start fault witness, cold boot, pending final write, reset during write/read/ld, full reboot, ordered full stage/token execution, invalid boot/epoch/digest and simultaneous cfg/start priorities. Four-state old contents and causal late-read, wrong-row, mask/word and invalid-start mutants are required. No simulation verdict is claimed yet.

Resource plan is 8GB RAM, two threads, 20GB disk on unpinned ot-run, admitted against measured fleet capacity. No synthesis, physical job, 602-copy forest, compiler/helper change or whole build is authorized. Additional target edges are zero; actual SU/MU calendar and parent binding remain NULL.
