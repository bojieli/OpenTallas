# WBK read-valid and native fanout repairs

Source 451867fe3 uses the same kept payload-selector copy for both the FIFO payload mux and its read-valid selection. This repairs the real empty-slot read found when the former independent selector copies differ in the structural CDC proof. It changes no interface edge.

Its actual canonical generation passed at 20:33:50 PT in 3020.94 seconds, with a peak RSS of 4856992 KiB. Three production positives passed, and all nine required causal mutants were rejected. The per-PP counterexample passed with nine grants, including four A and three B completions. The pooled-counter M11 was rejected. Actual logs and source hashes are preserved here.

The actual mapped synthesis netlist subsequently failed the canonical native census: maximum 49 dynamic loads, 512 violations, and no role errors. The two classes are 192 release-counter bits at 40 to 49 loads and 320 capture-toggle bits at 35 to 37 loads. The exact mapped netlist hash, canonical helper hash and live TT/FF library set are recorded under native_451. The direct census ran under normal fleet admission on EP5, using the immutable completed mapped netlist from the original EP9 native scope. The original scope remains intact while its floorplan loader processes the clock constraints. No netlist, threshold or waiver was changed.

Repair source 630245fe5 gives each release copy four subtractors and gives each capture fragment a same-edge toggle copy. Each fragment uses its own identical copy for both payload and valid selection, preserving the prior structural storage proof. HBM reset leaves now serve two slices each to bound the extra copies. Reset tree depth and all interface ages remain unchanged. Its current canonical generation and native chain is session 80339; the existing behavioral and causal suite is session 39450. These results are pending.

Next: collect the repaired source generation, native census, three positive cases and nine causal rejections. Physical MAIN and fallback require actual native maximum 32 or less and the functional evidence before admission. Physical timing, area, external calendar and die adoption remain open.
