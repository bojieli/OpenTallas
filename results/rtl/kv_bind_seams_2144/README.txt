Candidate only. No physical route or token qualification.

Inherited v12 verify: FAIL, 2552344 compared, 2552339 matched, 5 mismatches,
289 Verilator lint errors. Root causes: reset PLL qualifier missing from
connectivity transport model; raw pad analog descriptor normalization;
real composed head/ASTK RTL not entered in module_index (prefer cannot add it).
Old failure evidence remains at epyc1:path-kv-bind/b12/verify_report.json.

Minimal seam candidate: 20533 added landing pad flops, maximum 16 cycles,
only unique hub_C/hub_Wi/sys_c partitions. Source-relative RX at56, TX55,
root and embedding join service54 (zero skew). Compiler consumes actual
bus_groups; no rate credit before recompile.

Full R8 leaf/type proposal needs 74471 FF, max62 added cycles, and fails
four replicated types. Exact sites/instances/lane depths are recorded in
r8_seams_2144/full_r8_conflicts.json. Global max-padding cannot converge
because type-equal-pad constraints create a positive cycle; source/plan
recut or explicit different masters is required before all-R8 release.

29 focused r8/compose/reset-identity tests PASS. Repo-relative manifest gate PASS.
