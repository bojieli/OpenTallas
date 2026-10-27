# HEAD-RTL-3 2026-10-26 (s81_head RTL completeness on main f795e41b9a)

All numbers CHECKED (tools run in this lane on epyc1, Verilator 5.050).

## Content providers (tools/s81_head/head_module_check.py)
- canonical physical/die_plan/s81_head/die_plan.json: FAIL, 4 missing (hd_mesh, hd_lep0N, hd_ctl, hd_host): canonical_module_check.json
- candidate = head_provider_plan_delta.py (ctl/host/LEP/mesh + rtl delta, the composition Codex merged): PASS 0 missing, 0 unresolved: candidate_module_check.json, candidate.json

## Strict die port-bind (new tools/s81_head/head_die_portbind.py, repo-relative filelist)
- candidate (cand/): gen.py rtl --rtl-root leaf bind rc 0; DIE_PORT_BIND PASS: 16 masters, 326 instances, unbound 0, stub 0, input_unconnected 0, input_tied 0, undriven_net_bits 0, multi_driven 0, unread_net_bits 0, output_open 0, unresolved_children 0; spare_out_bits 1660 = ONLY reset/START wavefront outs rst_o_k/start_o_k left open per instance (reset_tree.py union-of-sites pins), declared per instance in cand/pads.json.
- canonical (canon/): port-bind also PASS (830 wavefront spare outs) although 4 providers are missing: the canonical wrappers instantiate themselves as u_core and die_port_bind indexes them as real masters. Hence the wrapper gates on the module check too.
- First raw run (ANSI header): 293 UNPARSED (clk/clk_t*/clk_c*/arst_n; die_port_bind reads top ports from body declarations only) + 36 OUTPUT_OPEN masters (the wavefront outs) + 2 unresolved children (sparse checkout lacked physical/asap7_memory_macros). All three were artefacts of the check, not of the RTL.

## hd_mesh forced-CRC replay test (RULING HEAD-RTL 19:35)
- mesh_replay_v1: the original windows (4 / 10 consecutive beats) gave crc_err X=1 Y=0, retx_flits 0: replay was NOT exercised in both directions (the new counter check FAILs it, NOCRC mutant otherwise invisible).
- mesh_replay_v2: one corrupted beat every 16 cycles over 200 cycles per direction: Y lane b crc_err 4, X replays 4, 25 retransmitted flits; then copy B at Y lost 6 records (395/401), 16 data errors, Y in-band ep_fault bit 10 (copy-slot OVERWRITE) set. REAL FINDING: after a replay the lane delivers the backlog back-to-back (li_r credit = li_v registered, CORE_CRED 8), but the endpoint's per-copy hold slot drains one word per 2 edges, so a replay burst overwrites copy B. Detected (sticky fault), not silent. The X->Y direction (imp[1] window) still showed X crc_err 0.
- mutants: 1-4 FAIL as before; 5 OT_DSROM_LINK_MUT_NOREPLAY FAIL (copy B 373/401); 6 OT_DSROM_LINK_MUT_NOCRC FAIL (25 data errors).
