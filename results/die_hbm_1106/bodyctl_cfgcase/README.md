# Optional BODY issuer CFG case replacement

Current CTS leading path is step[1] to issuer_cfg[3] (−49.93 ps). Only the combinational D expression feeding the existing 37-bit register changes under OT_Q3CTL_CFG_CASE. Its original clk_program edge, asynchronous reset, and zero reset value remain unchanged. All existing recipes retain their values. New __mul4rt_rcp1_cfgcase is default off; added cycles 0.

Universal SAT compares the actual flattened 24-assignment D cone against the 53-case expression for all 1615 unconstrained step/row/assembly/metadata/draining bits. PASS; output-bit-16 mutant fails. No reachable-state, fill, or reset assumption is needed. Instance maps these five original signals directly; guard-off token identity asserted.

Same ASAP7 TT ABC speed mapping / 1-unit output load: baseline2495 cells /351.70 ps; candidate1483 cells /224.66 ps (−127.04 ps). Isolated cone measurements only. No P&R activation; exact whole-kit LEC remains required before physical adoption. RCP1 prior whole-core LEC does not cover this new option.
