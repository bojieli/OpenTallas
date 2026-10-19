# Minimum actual two-PC controller equivalence

Source460a48585, Verilator5.050. Actual dsfd_ctrl_rg2 with real SRAM opt-in, one PC active and one idle, compared cycle by cycle with byte-pinned ot_s81ph_ctrl_pcr source05689febd. Golden module name and mutation flags changed only; data/control logic retained. Clocks832/1024ps; periodic PHY refusal, response beats and write-done pulses, 96requests perphase, middle reset. Comparison covers actual top-level RD packing, request payload/valid, credit, response payload/valid and write-done. Regional chained status is not compared in this component; full32PC bench remains its witness.

Positive2798stream/2274PHYchecks,192accepts/152refusals,323responses/206write-done. Three real source mutants caught: refusal-drop at20.993ns, actual top-level RD swap at21.217ns, PHY-payload pack at16.897ns. Raw nonzero simulator exits and first mismatch logs recorded. Full32PC clock-crossing latency, real PHY behavior, physical SRAM collision/escape and closure remain separate obligations.

First prototype had two requests issued before reset/live and failed coverage with94accepts; it is not RTL failure or a mutant witness. Runner initially used unavailable remote rg; fixed to grep before qualifying these results. No timing/RTL contract was relaxed.
