Prepared after ROOT instruction, 2026-11-01 20:46 PST. Each replacement is HELD
until corresponding foreign variant is terminal; at most two alternatives per
kit. Current native baselines L4S1 and XRT1P3M110 have zero slweco_* components,
so the L2 collision is a demonstrated risk on reused-chain baselines, not an
inevitable failure of these first stages. No foreign script or job was changed.

Epyc2 own source bundles at codex-s81-nearmiss-2036/held/l4_C1,l4_C3,xrt1_W10,xrt1_W6:
original generated eco_hs.tcl retained beside corrected eco_hs_unique.tcl;
independent exact-named output and kit path; runtime eco2/ant/defcmp copied;
original stage2 sizing script retained, not auto-dispatched. L4 uses36slew pins,
segment60, candidate sizing targets10/30; XRT1 uses94pins, segments100/60.

The enclosed commands are exact stage1 replacements, not launch authorization
for duplicate work, not geometry approval and not a claimed timing fix. Any
terminal failure must first be diagnosed, actual geometry reviewed, then launch
only if exact-identity correction addresses its cause. No new cycles or RTL.
