# Qcore actual RF write-cone successor

R15a final route TT -226.31 ps, FF +7.74 ps, DRC0. The failing same-core_clk path starts at sector7 collective address copy bit1 and ends at bank4/half0/row3 bit14. Raw STA and model preserve exact clocks and incremental delays. Baseline SHA7dbe0bd9 matches the consumed gate manifest; this source candidate does not reuse its physical qualification.

Real COL sector/row decode moves before the existing writer capture, registering one-hot row hits at the same edge. Storage still commits k+1, collective writes override all lane writes, reads/status keep existing edges. No SRAM/storage replica or calendar change. Raw address+valid24FF per sector becomes16 row-hit FF (-8), with resettable4->16, so whole-parent reset binding still requires qualification.

First native FAIL16/max34 on COL data select. A byte-wrapper alone let ABC absorb the OR into mux bits: native2 FAIL16/max84 on rowhit registers. Final separate kept OR4 children in data bytes and control path yielded actual sector7 native PASS10939 roots/max32/0violations. All raw reports retained, no threshold exemption.

The source1 existing qcore lockstep passed9104checks/312scalars/5918validreads, fault_lags0. Exact finalsource3 functional run passed9104/scalars312/5918validreads/fault_lags0, and actual COL word-source MUT128 was rejected. PRETREE-enabled parent native/reset/placement/finalroute remain unqualified. No layout gate, submit, main adoption, or source alias.

Fullparent1 source3 native failed only two reset landing roots36/39 loads; actual functional/control/data roots were <=32. Source4 exposes each of16 row-hit reset flops persector as a distinct internal reset port, retaining topinterface, edge and existing strict32 splitter. Exact source4 existinglockstep PASS9104/scalars312/validreads5918/fault_lags0; actual MUT128 rejected27938errors. Fullparent2 census/layout remains pending.
