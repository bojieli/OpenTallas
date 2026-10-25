# LEC lane (logic equivalence check RTL vs synthesised netlist) -- started 2026-10-24 22:06 PDT

Goal: industry-standard LEC (Conformal/Formality method) on every kit before P&R; catches frontend bugs like the
10-24 csa31 yosys-slang drop (claude/s81-kits-1024r@ab4ad9f68). Branch claude/lec-gate-1024, worktree ~/wt/lec-1024r.

2026-10-24 22:06 PDT LEC: design = gold RTL via the OTHER yosys frontend (slang<->read_verilog), proc/flatten/memory_map only;
  gate = netlist + ASAP7 TT liberty functions; flops keyed by register bit (rename -wire, QN polarity normalised);
  black boxes stubbed identically (pins = compare points / shared inputs); register correspondence (constant flops,
  merged/renamed flops by signature, proved as one inductive set); ABC &fraig + &sat -a per compare point.
2026-10-24 22:06 PDT LEC: toy csa31 kit (slang): NOT EQUIVALENT y[24..30] (RTL regs removed although live); prototype OK.
  Running eng_rr_e pre-fix / csa31-only-fix synth (ot-run spilled to intel1, data /srv/opentallas-scratch2/claude/lec/eng).
