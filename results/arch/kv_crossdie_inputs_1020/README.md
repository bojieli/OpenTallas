# Proposed explicit compute pair contract — source only

Historical GEN9 source75171867d omits layer_compile.py's mandatory --compute-die-v. Original d9o/q/p cases remain untouched; their diagnostic pathfinding continues, with relay-check failure preserved.

The proposed helper requires OT_COMPUTE_PAIR_MANIFEST whenever it compiles a schedule. It removes the historical generic table default and passes the selected die, table and full compute source commit together. The manifest pins both files by SHA256 and states the table's original die path, permitting exact verified copies onto fleet hosts. Complete problem-free compute netlist-walk provenance and matching source commit are required. Revalidation after compilation refuses concurrent input drift. Existing explicitly supplied OT_RELAY_SCHEDULE behavior remains unchanged.

Selected by the Qwen owner: dv2f20g4g, source b9bf998e4e6e11f9bd94959fc632f9d34ffc250c. Both referenced files exist locally and their hashes were checked. Remote identical copies: ot-epyc6:/srv/opentallas-scratch/claude/mu-die-qw/dv2f20g4g/out/case/{die.v,relay_stages.json}. Update manifest paths only after checking those exact hashes. The exported netlist table is the compute input, not compute_compiled.json.

This compute snapshot is PHYSICALLY UNQUALIFIED: native receiver missing, MODEL_ONLY R0 and declared source/view stand-ins. Its manifest scope is diagnostic and the helper refuses it without OT_BIND_DIAGNOSTIC=1. Identity validation establishes no native, physical, cross-die transaction, schedule or release qualification. Root review and a future coherent input selection remain required. No old run was repaired and no calendar/compiler run was launched with the proposed helper.

Validation: actual pair identity plus six causal refusals (die hash, table hash, commit, die origin, scope, diagnostic-to-strict). Shell syntax passes. No full cross-die compiler/gate test performed. A release_candidate scope declares intended use only; full qualification remains the caller/owner's independent obligation.
