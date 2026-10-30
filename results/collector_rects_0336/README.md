# QC collector physical site correction (source component READY)

Six corrected FW kits reach the end of ring packing and fail at collector rst_n_t2. In the measured sle_fw_v3 example, the existing collector box [153.36,500.04,157.68,504.36] lies inside the corrected rd_ei ring band [142.56,486.768,194.4,575.52]. The ring fills first.

`landing_contract.group_rects_um` is a default-OFF physical override for exact existing collector/raw-copy group prefixes. It rejects unknown, ambiguous, unsupported, nonfinite, unordered or out-of-outline specifications. An explicitly overridden optional group must also exist in the actual mapped design; otherwise the native hook fails before placement. Ring rectangles continue to use the existing band metadata. No RTL is changed.

All 119 actual plan45 types produce byte-identical Tcl with the field absent. Sixteen focused tests pass, including actual Tcl execution rejecting absent and similarly named mapped groups.

The candidate moves the complete measured cohort—u_cland_collect_rst_n_t2, u_cland_collect_rst_rl_3 and u_cland_reset_rst_n_t2—to one shared 9.72um square centred at (129.6,502.2), outside every landing ring. Native 3_2 ODB measurement finds 17 cells, 2.59524um² actual area and 6.561um² combined unchanged .4 reservation, versus 94.4784um² shared box area. It does not move the reset-tree relay nodes, taps, public pins or parent outline, and changes no RTL/state/data/boot cycles. Conservative declared-box bounds cover affected incoming local status, collector parent/child edges, raw copies and clock entries: reset/status <=374.76um; clock <=39.96um. The diagram was personally viewed.

The sizing and hop model is not actual G1 or a route approval. Fixed/TAP/FT obstacles and native site packing remain to be measured on the isolated PLACE-only candidate after source peer review. Other five terminal kits remain preserved and require their own current mapped sizing before adoption.

Native input: intel1/epyc2 copied snapshot `/srv/opentallas-scratch2/claude/codex-qc-kits-0336/gen_union/sle_fw_v3/sle_fw_v3/run/results/asap7/dp_sle_fw_v3/base/3_2_place_iop.odb`. `actual_cells.tsv` records mapped widths/heights/reserved widths in DBU. `budget.json`, `delta.json` and `collector_model.png` describe the isolated physical proposal; `default_identity.json` records the full default-output comparison.
