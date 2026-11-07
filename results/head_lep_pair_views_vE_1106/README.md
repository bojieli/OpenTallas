# HEAD LEP pair vE views

Late-stage RE-FORM of the SIGNED lep_eco7 core: clk moved from the interior M5 (388.92,246.24) to the S face M5 (397.464,0.24). Same netlist (6_final.v sha256 bf0d63a5..., byte-identical), same CTS tree. Source: epyc4 /srv/opentallas-scratch2/claude/dh76/pairclk/kit_vE, attempt a2. See FORM_NOTE.

source_signoff.json verdict SIGNED: setup_tt +68.72, hold_ff +3.68, DRV 0/0. clk pin-register mean TT 529.22, FF 434.56 (signed lep_eco7 452.9 / 366.3). clock_contract.json is exported by core_clock_contract.py --signoff.

The parent must use this detailed LEF (abstract_detail splice M6/M7, splice.json). The plain ORFS abstract fails DRT-0073. Applied by tools/s81_head/head_lep_pair_ve_delta.py.
