# HBM selector placed review

2026-10-29 08:32 PDT, independent Codex reviewer. AUTO-GEOM row96011423313c,
epyc2 hbm-cores-kits-4/k11/ot_hbm_idx_selector_static_sel_ca11ad493af0-_k11,
claude/hbm-cores-kits-4-1028@0b1b020433. Existing geom.tsv rendered with current
main geom_rules/geom_png; no duplicate OpenROAD run.

Personally viewed placement_only.png: two columns of six SRAMs, wide central
street, logic clusters west/east. Verdict FAIL as-is: reset launch
u_fcore.rst_core_n at (585.198,30.375) drives opposite gq[1].buf_q[1118] at
(44.388,377.325), 887.76 um. Full placed graph has 9209 captures beyond405um.
Fix reset delivery through planned local relay/island branches rather than
one E/S root flop. Preserve known deterministic offsets; any added cycles
must enter the model. HBM owner notified.

The36 unregistered pins are9 planned clock/reset pass-through interfaces in
an old dump missing typed interface lines; they do not explain this reach
FAIL. Channel projection2.394/1.18 is unconfirmed pending inherited GRT.

The inherited AUTO-GRT was mistakenly classified no-verdict while still
running: epyc2 pid2873587, ~100percent CPU, iteration26/50 at08:15. It remains
untouched. No zero-overflow or CTS/SIGNED claim. Image/json are placement-only.

Targeted structural feasibility from the same saved graph (08:37 PDT):
BFS from rst_core_n through combinational logic reaches11031 reset captures.
Their bbox is x5.13..594.486/y9.045..398.925. Exact unconstrained single-source
Manhattan minimax radius is425.817um at (248.967,201.501), above405 even before
legal-row/macro constraints. A simple source relocation cannot fix this.
The current rst_n pin is (599.952,28.44); the source FF already sits near it.
A local reset relay/distribution or structural cut is required, with cycles
priced in the model. HBM owner notified; no competing RTL edit made.
