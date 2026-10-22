# HC collector receipts

B0 RC3 gate3 run `ot-epyc9:/srv/opentallas-scratch/claude/ref_gate/hbm_hcq_bank_b0_rc3-20261020-033751`: mandatory in-flow native32 PASS/max32, 27702 cells/12808flops. Actual CTS FAIL `OT_HYBRID glue root clk pin-flop spread674.3ps TT`, boundary4418 of7241 sinks. GRT not run. No clock waiver, review or submission. Structural regional placement/crossing revision owed; do not retry unchanged geometry.

Bank RC and RC3 exact lockstep Verilator5.050: MUT0 HC_ENG PASS each; MUT1/MUT5 HC_ENG FAIL each, complete remote witness logs retained. RTL source inputs were frozen by original bank lane; collector has not changed them. Pending cb_rc/cb_rc3 progressing gates preserved. HCROOT childc cloner pipeline remains in source ABC stage; no census result yet.
