# Programme store r14 safe design review

Prior failed r13_cl is preserved: TT -60.21 ps / FF hold -102.73 ps / DRC0.
1 Pins: PASS existing registered host inputs/outputs; reset two-stage landing.
2 Reach: PASS unchanged fixed relay plan, longest register leg <=405 um; new comparison partials remain at the status combine point.
3 Fanout: PASS mapped native census max18, zero violations, exact source92294601d (native_summary.json); comparison data bits drive <=7 comparisons.
4 Depth: FIXED ordinal agreement split into registered 8-bit comparison partials and sticky-update stage.
5 Storage: PASS unchanged 11 closed SRAM leaf children; no runtime-indexed new storage.
6 Floorplan: PASS unchanged 43.2-lattice hard children, continuous std-cell channels, aspect1080/950.4=1.14, full-face pins.
7 Clock: FIXED child clock leaves isolated from parent relay-flop bins; child insertion243.9ps included, hold margin0.03; actual TT/FF measured spread pending.
8 Schedule: PASS static; comparison stage consumes one former fault pad, so D10/status8 and all external edges unchanged, opt-in FAULT_PIPE1 (default0). Lockstep bench must validate every edge and reset/fault modes.

No coordinator approval assumed. Critical prefix requires PNG+native-census review after gate.
