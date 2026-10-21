# PC sr11a terminal route failure

Exact original gate source is frozen in source_snapshot.json; full canonical gate_result.json is retained separately from scratch_verdict_summary.json. Original remote run: ot-pve1:/srv/opentallas-scratch/claude/ref_gate/qkd_kvs_pc_sr11a-20261021-094449. Outer execution completed GATE_SCRIPT_RC=0/GATE_DONE; canonical verdict FAIL because trial global route returned GATE_GRT_RC=2.

The terminal GRT failure is GRT-0183 on net _006462_: the 3D maze router ran out of legal paths during incremental repair_design_helper. It saved 5_1_grt.grt183_resume.odb and removed 50 hook shapes, then global_route.tcl line175 exited. Original grt.log.gz preserves the exact error and logs. Initial total overflow0 and M3 usage44.04% do not qualify routing or timing. Actual hck boundary spread TT19.9ps/FF19.1ps is a clock-only measurement, with insertion483.4/391.7ps guidance retained; no final timing PASS is claimed.

No unchanged retry, submit, merge or geometry approval. sr11b remains independently active. All original warnings and source binding are retained.
