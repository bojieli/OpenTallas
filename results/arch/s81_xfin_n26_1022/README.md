# XFIN N26 structural native closure

N25 maps 93 real SRAMs but fails native census on twelve drivers: four divider remainder-bit capture outputs at 36/42 loads, and eight rsqrt NYC4 multiplier output reset leaves at 33 to 40 loads. This candidate keeps the two /5 combinational steps separate for the affected remainder bit and gives every copied multiplier output byte its own existing two-edge reset leaf. OT_S81DV_XFIN_N26 is opt-in, off by default. Arithmetic, release depth, port widths and observable output edges remain unchanged. The model delta is zero cycles and zero SRAMs; extra reset leaves cost 4 per NYC result copy, with each leaf driving eight resets. No graph rewrite or threshold waiver.

Run actual mapped native census first. Existing N25 full equivalence is preserved; N26 requires its own actual norm/engine equivalence plus the existing mask mutant before layout/adoption. Any synthesis helper staging failure is separate from the actual mapped census result.
