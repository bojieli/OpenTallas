# LEP child placement follow-up: failure diagnosed before P&R

The original child geometry and review remain as history. The actual connected
endpoint model found the original bank-column layout unsuitable: the GB SRAM
bank 7 directly drives the W-face `beat_tx[508]` register over 755.7 um.
The v1 site-planning attempt retained 1,214 captures over 405 um, worst 784.43 um.
Verdict for that geometry: FAIL. No P&R was submitted.

Viewed `results/head_serdes_lep_0825/lep_child_v2/child_plan.png`. The corrected
layout keeps the ten GB SRAMs in two columns at the W pins. Nine SKI head SRAMs
sit next to them. The 36 EP SRAMs form nine local 2x2 FIFO/replay/depth blocks
on the E side. Minimum macro gap stays 14.808 um, and the centre clock/reset
channel stays open. The complete EP macro boxes fit a 394.38-um Manhattan
envelope around their common control point (466.56,260.436).

The full-width S pin band also puts the last landing chunk's low-index control
and high-index payload on opposite ends. Candidate v3 rebuilds the S pins in
a compact x2..395.44 band using the same current RTL-header/track planner;
the W pins and centre reset stay on the actual expanded outline. Pins remain
on M5/M7 in source order, at about 0.704 um pitch. No RTL or cycle change.

The register projection heuristic did not close v2 (560 captures over 405 um,
worst 789.91 um, involving movable registers). That result is not a proof that
the revised macro plan is infeasible. A graph difference-constraint solver is
now producing a connected register plan against the actual netlist. Its first
380-um planning target was infeasible; 380 is a design margin, not a release
rule. The required gate remains 405 um. Route stays held until actual placed
register reach and clock/PG review are satisfactory. No route or timing PASS
is inherited from the old outline.
