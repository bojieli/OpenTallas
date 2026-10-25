Literal current Qwen path adapter

carve_pair.py composes an exact QC W5 projection/transport carve with an entire native KV bound top at their declared 583-bit PHY bump ports. It retains 16 W5 bf/bn/tn/tf cluster partitions (64 A0 tiles), all 14 W5 slice roles, coll_f4, native59, glue, tt_ctlm and the real UCIe PHY, plus declared lane transits. It never substitutes a functional service endpoint.

All unfinished environmental inputs remain explicit. A caller must supply real ROM/program images, bootstrap traffic and a schedule generated for the pinned plan/source. Reset and START prefix ages come from bind_reset.json; one shared START drives both dies. This tool does not select a START cycle, replay a Q fixture as projection, prove token completion or close physical gates.

Usage: python3 tools/qwen_tokfunc/current_path/carve_pair.py --qc-top BOUND/rtl/qwen_compute_bound_top.sv --qc-plan PLAN/die_plan.json --kv-top KVBOUND/rtl/qwen_kvsys_bound_top.sv --out NEW_DIRECTORY

The focused test_carve_ports.py checks exported PHY outputs and that same-named partition modules from different bound roots cannot poison the parser cache. Actual paired elaboration and token simulation are still required.
