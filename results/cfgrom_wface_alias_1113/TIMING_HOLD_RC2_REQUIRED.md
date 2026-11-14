TIMING HOLD — Claude reset safe park, 2026-11-13

Do not use the current TT Liberty or generator output for STA/adoption. Geometry, distinct alias and registered-ROM lockstep remain valid. Root S81 and frame bit helper have been notified. No RC2 build or new experiment was launched.

Two analytic corrections remain:
1. views.write_liberty models cell delay as clk_to_q + out_r*(load-0.72). The new extra-wire intrinsic intercept must include added series resistance times0.72fF. The current5.6088646ps number omits that anchor term.
2. The42.168um Manhattan return comprises38.040um horizontal M4 plus4.128um vertical routing. Using only M4 for the vertical leg is not a demonstrated conservative bound. Frozen ASAP7lock setRC.tcl gives M3 R=.031287kohm/um,C=.155554fF/um; M4 R=.0180365,C=.178475; V3 R=.0172kohm per via. A plausible two-layer return needs twoV3s. These values were read directly from the pinned image; tech LEF has no separate via resistance.

Next: choose and document a conservative two-layer RC/energy/slew envelope (including reference-load anchor) using the existing compiler analytical contract. Preserve original FF earliest timing so unchanged pins gain no false hold credit. Generate into a FRESH immutable RC2 directory, retain current candidate/receipts, and deliver replacement TT/FF/provider pointers explicitly. Do not overwrite published views or carry their old timing. Behavior is unchanged, so reuse exact alias RTL proof after verifying generated behavioral bodies stay identical; actual parent STA remains a future gate.

Source5e0bfa195f is an unused private provider packet, not a source/POR selection. Native frame alias instantiation and fresh ELAB/source graph are still owned by frame lane. No SS allowed.
