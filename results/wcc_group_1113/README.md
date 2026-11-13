# Legacy landing writer counter groups

The private DSDV t3/t8 proofs stop before place with one74-load root counter net: a1105-bit landing pads to1152bits and72 writer chunks of16bits. The common root drives every local slot-copy register.

`OT_MESO_WCC_GROUP=16` adds one kept-hierarchy lookahead capture per16chunks. Each group captures `tc+1`; local copies capture `group+1`. After two startup edges, each local copy again holds current `tc`. Existing ring training discards the startup slots. External data and ready latency stay unchanged. Defaults remain off.

Actual `ot_dp_clk_landing` W1105/LOCAL1/DSREP8 lockstep against the pre-change source:24 nominal cases pass (off/on, rising/falling writer edge, six clock phases), four warm resets per run. Twelve wrong-lookahead mutants fail with897-898 mismatches. Root initial counter5 and five different group initial values exercise startup convergence. See summary.json; scripts live in rtl/test/meso/wcc_group.

An inline kept vector was insufficient: synthesis merged it with the root counter. The kept-hierarchy helper preserves all five2-bit stages: mapped register count6551->6561. Both small mapped designs pass reg_fanout_gate. This mapping does not reproduce the full-parent74-load failure; it proves stage survival and no local fanout regression only. The current4906-pin parent proof must pass its actual synthesis gate before placement. No sign-off or physical closure claimed.
