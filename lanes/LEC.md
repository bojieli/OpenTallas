# LEC lane (logic equivalence check RTL vs synthesised netlist) -- started 2026-10-24 22:06 PDT

Goal: industry-standard LEC (Conformal/Formality method) on every kit before P&R; catches frontend bugs like the
10-24 csa31 yosys-slang drop (claude/s81-kits-1024r@ab4ad9f68). Branch claude/lec-gate-1024, worktree ~/wt/lec-1024r.

2026-10-24 22:06 PDT LEC: design = gold RTL via the OTHER yosys frontend (slang<->read_verilog), proc/flatten/memory_map only;
  gate = netlist + ASAP7 TT liberty functions; flops keyed by register bit (rename -wire, QN polarity normalised);
  black boxes stubbed identically (pins = compare points / shared inputs); register correspondence (constant flops,
  merged/renamed flops by signature, proved as one inductive set); ABC &fraig + &sat -a per compare point.
2026-10-24 22:06 PDT LEC: toy csa31 kit (slang): NOT EQUIVALENT y[24..30] (RTL regs removed although live); prototype OK.
  Running eng_rr_e pre-fix / csa31-only-fix synth (ot-run spilled to intel1, data /srv/opentallas-scratch2/claude/lec/eng).
2026-10-24 23:01 PDT LEC: signed views so far EQUIVALENT: hrow (38 s), vq (89 s), stations t12/15/16/17/20/21 (2-4 s each, reuse), t5 (15 s), hcpost_lane_pr (61 s); fixture csa31 pre=NOT EQUIVALENT y[24..30] / fix=EQUIVALENT.
  correspondence now handles renamed/merged/constant regs, matched-flop merges, slang-vs-read_verilog unpacked-array layouts, genblk scopes. l5f/LLd/cfg7/kv3/eng in progress.
2026-10-25 00:54 PDT LEC: fixes since 23:01: gold peepopt (eng_rr_e gold 31M->263k cells, 77->1.2 GB); RTL X = don't care (ternary X rail, Conformal default) in compare + correspondence; relayout only on clear gains (false flips gave l5f/kv3 false NEQ); stride + array pairing of constant-looking bits; SAT/undef split by simulation. l4r, LLfd/LLfu/NNfd/NNfu, l5f now EQUIVALENT. Final full sweep of all signed views running (epyc1/epyc2/intel1); eng pre/fix running.
