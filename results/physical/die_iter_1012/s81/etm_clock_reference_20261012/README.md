# S81 ETM clock-reference regression

The probe uses the source-pinned routed dsfd_cfifo ETM from71395c948 and an ideal registered peer. It tests cfifo launch xa[86] and capture ri[67], with unchanged setup85ps and hold50ps uncertainty. No die closure claim follows from this small probe.

`*_physical` removes only min/max_clock_tree_path blocks from the ETM, preserving every I/O timing table and using the physical balanced pin targets. `*_earlylate` uses the original ETM with STA reference compensation (`set_clock_latency -min/-max`), preserving those physical targets in the kit record. Both paths match at FF/TT/SS to0.001ps. `old.log` isolates the false hold failure from applying physical balance directly to normalized ETM arcs.

Reproduction files here are the generated Tcl, Verilog and peer Liberty. CFIFO Liberty source paths and SHA256 hashes are in summary.json; regenerate the physical reference by deleting only timing() blocks whose timing_type is min/max_clock_tree_path. Tests ran through ot-heavy --mem4 on ot-epyc4 and openroad/orfs:asap7lock. The immutable original routed views are unchanged.

The fixed die kit emits compensated STA latency separately from its physical target record. Synthetic120ps receiver delays require --planning-hold-pads; they have no physical implementation and cannot qualify closure. Abutting registered links with insufficient measured FF minimum delay remain open.
