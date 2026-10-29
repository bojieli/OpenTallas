# HEAD SerDes quarter+keep: diagnostic CTS continuation

Personally viewed results/head_serdes_1355/auto_geom.png before submitting
CTS on 2026-10-29. Uniform fill .5011, no holes or macro walls, centre clock
(108.1,97.2), W M4 input band and N M5 output band. The two lighter lobes are
lower-density cones. GRT0 overflow0, r2r232.98um/0over405, clock entry central.
Concur GEOM59 PASS-COND for diagnostic CTS of this exact placement.

The320 W inputs use the existing INTERNAL_CORE contract, not a partition-pin
exemption. Parent hd_serdes must time all320 ports, show0unconstrained inputs,
and place launching registers within150um of the child W band (internal
worstreach255.5um). No new RTL, face cycles, clock budgets or pins.

Own diagnostic clone reuses the terminal EQUIVALENT4217/4217 source/netlist
and3_place.odb at intel2 codex-head-serdes-lep-0825/quarter_keep. New run
intel2:/srv/opentallas-scratch2/claude/codex-head-serdes-1355, ot-run unit
oth-ubuntu-332115-1793307569, client330588, containercodex-head-serdes-1355-cts.
The admitted job runs only CTS with the existing pinned kit flow. Actual TT
and FF libraries confirmed in cts.log; ss is only the internal mode label.
No new flow-tag adoption, GRT, detailed route, sign-off or parent timing claim.
