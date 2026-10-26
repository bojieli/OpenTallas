Routed elemB_rb_c9 pair-skew correction (2026-10-25)
Vehicle: epyc3:/srv/opentallas-scratch2/claude/s81-head3/elem_rb/elemB_rb_c9, read-only final ODB/SPEF and golden SDC. clk source latency -120ps; 833ps, setup/hold uncertainty unchanged. No RTL, placement or constraints changed. Original failed signoff retained.
Cause: OpenSTA PathEndCheck::sourceClkDelay removes launch source insertion whereas targetClkDelay includes capture insertion. Restore launch insertion measured from the root-port clock path before computing physical pair skew.
Exhaustive related pairs173612 at each corner. TT setup/hold worst63.68/62.02ps; FF59.39/57.26ps. Both arrival/path crosschecks0.000ps, neither result bounded. Old TT setup179.65/verify120ps was a measurement error. This result only repairs the clock gate; core FF IO hold remains separately open.
Jobs via ot-run epyc324GB4threads, own dirs /srv/opentallas-scratch2/claude/codex-clock-reset/elemB_c9, units oth-ubuntu-1927507-1792921157 and oth-ubuntu-1953455-1792921273, both exit0.
Validation:6 Tcl mock regressions span -120/0/+80ps source insertion for setup/hold,29 signoff unit tests pass; routed TT/FF extraction above is the physical regression.
