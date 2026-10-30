# Corrected H2 six-site model: FAIL, no physical build

The previous four-auto-island model remains preserved. Source f73b32dc5d4 uses
the same H2FIX6 family, placed census, libraries and UF3 fit with the corrected
explicit 2-by-3 topology. All six requested centres survive in the record. Maze
snaps are 0.036–0.144um; native body sites have not qualified, because conversion
correctly refuses the model. This run used no timing measurements as tuning input.

Final same-master model: TT395.54/window47.74ps, FF296.54/window41.35ps;
19747 sinks,1856 cells,13 stages. Existing checks fail the TT/FF20ps model-window
policy and one41.84um flop-leaf spread (Tpqqa at100.44,212.76). The converter
reports unequal-count model target failure at TT. All leg detours remain within
1.10x. No thresholds, clock contract, RTL cycles or physical view were changed.

I viewed the rendered plan: the six island circles occupy the two intended
columns and three macro streets; the centre clock entry is retained. Long level3
reaches remain (Tqqw236.52um); repeaters per level are1,2,3,1, giving13stages.
The correction establishes the six-site model, not latency closure or native
clock qualification. S81 owner retains the failure for structural diagnosis.
