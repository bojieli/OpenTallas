# Actual GEN2e clock source bytes

`case_a_manifest.json` and `case_a_run.tcl` are copied byte-for-byte from /home/ubuntu/artifacts/hdie-d4/d4g_gen2e (08:19 fetched case_a). The manifest remains explicitly NOT_A_DIE_RESULT; these bytes prove only clock-domain assignment/period, not die qualification. The raw generated run TCL has `create_clock -name hbm -period1024.0 [get_pins hb_ckgen/pll_hbm]` at lines18089 and18132.

`contract.json` is copied from ot-epyc4 /srv/opentallas-scratch/claude/hd4g/gen2e/views/contract.json. Its full raw SHA256 exactly matches the manifest input_sha256.contract (0f6cd7b6ca4cc2fa0a71d1578d9c72d61c08755d0a3b1ef4abee50543f885523). It is the actual input contract, not a prose extraction, and carries all endpoint domains/clock entries.

`strict_l17_score_die.v` is the subsequently bound strict score-port variant fetched08:52 from the same GEN2e case. It is not represented as the original case_a netlist: source binding changed L17 score ports. Its hfd_ckgen hb_ckgen pll_hbm root and all64 PC clk connections are mechanically identical to the actual domain contract and can be checked independently. Clock assignment was not changed by that score-port bind. Preserve this label when using it as a clock-topology witness.

`source_sha256.json` pins full bytes, so a validator can bind exact raw sources instead of trusting the summarized clock_contract.json. The top-level clock contract still requires TT setup/FF hold and unchanged60/25ps uncertainties;1024ps is actual HBM operation, not a frequency relaxation.
