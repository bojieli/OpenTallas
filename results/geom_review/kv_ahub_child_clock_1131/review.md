# AHUB retained child clock evidence

Exact requested retained views do not contain the data needed to expand AHUB child clocks. This is a physical-data and API gap, not a new failure of the original child SIGNED passes. No child pass was removed and no CAD job or shared tool edit was made.

Checked recursively on intel1: `/srv/opentallas-scratch2/claude/signed-keep/wt/s81-r25-lec/physical/ref_tile/ot_nhb_zh_m5` (27 files) and `qkh_recip_ref` (31 files). Neither tree has symlinks, routed ODB, SPEF, gate netlist, DEF, ILM or a per-endpoint clock-arrival sidecar. Both retain LEF, SS/TT/FF ETM libraries, export scripts/logs, abstract/insertion summaries and source/specification files. Reciprocal also retains a gate_result; its clock evidence is aggregate only. Its thousands of `path` fields belong to the source-binding manifest, not STA paths.

`insertion.json` records real aggregate counts/ranges for 8342 ZH and 8994 reciprocal clock sinks. These measurements have no per-FF identities or clock paths. ETM max_clock_tree_path values and aggregate means/ranges cannot substitute for expanded launch/capture pairs. Export scripts name the previously reported closure-loop `6_final.odb`/`6_final.spef` inputs; they do not retain those inputs.

Current `tools/die_plan/signoff.py:clock_model_coverage` explicitly detects composed ETMs and performs no expansion, returning UNEXPANDED_CHILD_ETM / NOT RUN. Its only inputs are selected libraries, instantiated endpoint master names and optional hashes; it accepts no expanded child endpoint sidecar. `consumed_clock_model_coverage` maps loaded library receipts into this detector. Supplying aggregate insertion.json data cannot close this API gap.

To close exact parent evidence requires recovering source-real routed child timing data or a validated per-endpoint child clock model, plus an explicit consumer that composes those endpoints with each actual parent instance/root and corner. Existing exact child SIGNED passes remain protected. No broad archive sweep or rebuild was attempted.
