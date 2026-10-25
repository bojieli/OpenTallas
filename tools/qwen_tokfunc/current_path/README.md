Literal current Qwen path adapter

carve_pair.py composes an exact QC W5 projection/transport carve with an entire native KV bound top at their declared 583-bit PHY bump ports. It retains 16 W5 bf/bn/tn/tf cluster partitions (64 A0 tiles), all 14 W5 slice roles, coll_f4, native59, glue, tt_ctlm and the real UCIe PHY, plus declared lane transits. It never substitutes a functional service endpoint.

All unfinished environmental inputs remain explicit. A caller must supply real ROM/program images, bootstrap traffic and a schedule generated for the pinned plan/source. Reset and START prefix ages come from bind_reset.json; one shared START drives both dies. This tool does not select a START cycle, replay a Q fixture as projection, prove token completion or close physical gates.

Usage: python3 tools/qwen_tokfunc/current_path/carve_pair.py --qc-top BOUND/rtl/qwen_compute_bound_top.sv --qc-plan PLAN/die_plan.json --kv-top KVBOUND/rtl/qwen_kvsys_bound_top.sv --out NEW_DIRECTORY

The focused test_carve_ports.py checks exported PHY outputs and that same-named partition modules from different bound roots cannot poison the parser cache. Actual paired elaboration and token simulation are still required.

Complete-vehicle mode

Pass --whole-qc to retain the entire QC bound top as u_qc, paired with the entire native KV top as u_kv. This preserves all FE/FW transports and all actual projection/receiver cores. ROM IDs come from each actual top-level tile strap plus its source-identified slot; all 768 distinct IDs are required. The W5 carve mode covers four clusters and only part of the projection; it is a debug cut.

The recorded input is intel2:/srv/opentallas-scratch2/claude/tok-qw/s8exp/stgdie/fx/L0_mat_qkv.npz, position8191/token24/layer0, SHA256 1eacb299857342e340347bb0c28781e24e3d6103e1d7c1d436244ecedf011969. Its x is the recorded PC0 activation; w int8[768,4096], BF16 row scales and post-PC1 gold_y must retain their distinct roles. Gold may only check actual outputs. The older xt1_inputs normalized embedding activation is not this fixture.

Build planning: use hierarchical Verilator compilation with both actual die tops retained as hierarchy blocks, initially 384GB/16threads. The existing native KV160 backend alone took 44m57s and yielded a674MB binary; a prior 200GB/32thread configuration OOMed. The combined QC377/KV160 vehicle adds768 actual A0 tiles and therefore needs a new measured build profile; the384GB figure is an initial resource request, not a measured combined peak or runtime promise. Stage/elaborate first and preserve source/plan snapshots.

Current source-only checks: actual QC ROM identities0..767 are complete; current QC reset metadata is accepted; a legacy KV top lacking exported PHY lines is rejected before pair emission. Paired elaboration and complete token simulation remain open until current native KV and canonical QC binds emit.
