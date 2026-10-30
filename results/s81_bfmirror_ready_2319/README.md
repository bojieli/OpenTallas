BFroots-only reset repair, recovered on main after both zero-clear reverts.

The encoded n_c/w_c state holds during reset. Mirror registers reload onehot(source) and qx_gt(onehot(source)) during reset; normal walker logic and arithmetic remain byte-identical. Added cycles = 0. The rejected zero-clear form is never re-applied.

Actual corrected source kit: intel2:/srv/opentallas-scratch2/claude/s81ck/kits/dsfd_bf_front_roots_rc2. Native synthesis LEC EQUIVALENT 27701/27701, zero differs/undecided (unit1326760-1793337685). Full existing col_h9 frame bench12/12PASS. Smallest actual BF source-process coupon4shapes NSEG1/2/8/32 ×12000cycles,1412resetedges each PASS; rejected zero-clear mutant caught6405..6834edges. Scope is the updated mirror mechanism; full frame bench covers complementary arithmetic/transport. No new P&R or SIGNED claim.

This standalone commit intentionally changes ONLY BFroots. ROM corrected-source kit equivalence is still pending separately on codex/s81-mirror-2250; do not merge that joint candidate until its own ROM gate qualifies.
