# Static stream packer source proof

This candidate changes only the own-X packer behind STATIC_PACKER=1 in a separately named stream module. The original file is unchanged and the variant defaults to its original implementation. The analytical model was written before generation/build. No added clock edge, relay change, backpressure or arithmetic reordering.

Actual Verilator5.050 comparison passes10,000edges for default and static configurations: all exposed outputs plus the complete internal next bitmap/data/error signals are exact, including arbitrary lane subsets, duplicate addresses, abandoned beats, pass-through conflicts, resets and continuous eight-lane full packs. Mutants2(RNE truncation),21(wrong duplicate priority),22(missing duplicate fault) fail with committed witnesses. This is a mechanism/throughput proof; full E/W production9 integration remains open.

Actual generic synthesis:71203->36842 cells; own payload stage60->21 generic levels. Worst stage28 is fault. xopen still drives65 cells; shared relay/completion/table selects and BF16 distribution remain high fanout. Total internal nets over32 increases57->137 because factored lane data now has64 destinations. Generic gates are not mapped timing and no physical closure is claimed. Reset integration remains seam_source-owned. No gate is authorized by this packet.

Source hashes and netlist hashes are committed; full netlists/builds remain at ot-epyc6/8:/srv/opentallas-scratch/claude/qwen-stream-static-1019/src/out. Bench unit187203 and census unit1789092 completed successfully. Actual mapped census, kept local same-edge control/producer copies, reset/clock/native timing, geometry/reach/PG are still required before physical admission.
