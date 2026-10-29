CLK-TOOL-8 recovered continuation, 2026-10-29 08:28 PDT.

Tool source: predecessor claude/clk-tool-8-1029-local@7e92b4abd, on a592c118f.
New opt-in stack.edge_balance: dme_alt maps to --clock-edge-alt (inv2 only).
The generic DME chooses branch polarity to centre the subtree edge sum, with
true-polarity sink nodes; the region FEED chooses polarity top-down. All legs
are parity-priced in DME and laid out with the same parity. Default remains off.
No arithmetic, schedule cycles, count-alignment settings or frozen plan changed.

Collected predecessor terminal diagnostic HEAD hk4 clock (not release hk5):
intel2:/srv/opentallas-scratch2/claude/clk-tool-8/head_alt.
GRT combo TT/FF both EXIT0, 5029 clock instances and 735 taps.
Both-edge routed duty, SPICE scaled: TT 48.19--52.03%, FF 47.90--53.09%;
0/735 outside45--55 per corner,0 MPW-estimate failures,0 inverted taps.
Raw rise in-region spread TT105.85/FF92.82ps; scaled110.99/97.94ps.
This is a diagnostic tool proof; no die freeze, CA, real-view STA or SIGNED claim.
The previously frozen HEAD remains its recorded inv/150 form.

compare_defaults.py compares source at a592c118f to this branch: a real
minimal DME tree + exported netlist byte-identical; kit argv identical on15
non-mesh configurations spanning all5dies. Runtime region-map lookups are
replaced with the same fixed list on both sides for this argv-only comparison.

Inherited tests1 finished212pass/15skip/1fail: failure is absent sparse
results/die_qc21_1028/inv2_stage_cal_trial13b.json, not a numerical failure.
Inherited corrected tests2 finished215PASS/18SKIP in511.49s.
Focused current edge/default cases15PASS in11.72s.
No new P&R or STA launched by this continuation.
