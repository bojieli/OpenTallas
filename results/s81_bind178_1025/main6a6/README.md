# bind178 on CURRENT main plan (TOK-DS3, 2026-10-25 06:20 PDT) -- strict bind FAIL 12, no RTL emitted, die netlist build NOT launchable

Plan = origin/main 6a6fc12dd physical/die_plan/s81/die_plan.json (adopt178 + faultfeed 6c5365e4a; 177 types / 398 partitions,
reset.release wavefront). Tool = this branch (claude/tok-ds-bind178-1025 + origin/main merged; bind.py conflict = union of
io_roles ports and main START-broadcast port). As-built = asb/asbuilt_b178.json (unchanged). Diagnostic probe on epyc3
(/srv/opentallas-scratch2/claude/tok-ds/bind178/out_main6a6, yosys elab via the tool docker --mem 16): elab 119 modules, 0 undefined.

Result: errors 12; unbound 11,715 / tied 0 / undriven 0 / multiply 0; 398 partitions, 900 crossings, 606,165 b.
- RESOLVED by main since ec9366040: 9 fault feeders and EMPTY s_5N_x06 (faultfeed plan delta merged).
- STILL OPEN (plan, owner S81-PLAN/FTCHAN): 11 attnh fold lanes UNPLANNED 1065 b each. Main now has word_bits 2133 but beats 2
  (= ~1067 b/beat on the wire); the ruling-B full-width fold RTL needs 2133 b in one beat (beats 1). Same 11 svc pairs as before.
- STILL OPEN (tool, owner CLOCK-RESET/PART-CAP binder, codex/bind178-reset-0559 -- no commits yet):
  EMIT wavefront core reset col_h10_r0_p1__t1/u_r0.u_e0.rst_n: expected one bound leaf, found 0 (2,787 hard-core reset taps
  nested inside cap30 as-built leaves; needs hierarchical core-reset ports or manifest dissolve to plan hard cores).
No RTL emitted -> portbind not run -> integrated adopt178 S81 die netlist cannot be built. No workaround applied.
