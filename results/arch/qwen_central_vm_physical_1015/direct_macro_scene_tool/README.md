The MY bank parent stopped before routing because the old direct-macro assertion
compared the first-linked TT network master against the actual FF hold scene.
This is a tool binding failure; no timing, congestion or physical closure result
is inferred from that stop.

The narrow fix observes successful native `sta::define_scene_cmd` calls, retains
both actual min/max library lists, resolves their actual loaded library objects
by exact library name or read filename, and requires exactly one matching macro
master in each list with the source-bound expected corner. Repeated SDC reads
install one observer. A scene defined before observation is refused. Redefinition
updates the observed lists. No scene, library, clock or timing arc is changed.
The observer is installed only for explicitly annotated direct SRAM entries.

Actual OpenROAD 26Q3-1510-g6cb3f2b704 image regression ran on ot-pve1 via ot-run
with 2 GB and one thread. Multi-scene positive reproduces a first-linked TT
network master and an FF BC scene. Both that case and repeated SDC installation
pass. Seven negative cases reject: wrong requested corner, actual wrong scene
library, missing/stale library, unobserved scene, redefined scene, mixed min/max
corners, and duplicate same-master libraries. `multi/receipt.json` records source
and actual Liberty hashes; all generated Tcl and actual logs are retained.

The existing actual-Liberty three-corner test also passes TT/FF/SS positive,
wrong-source, wrong-corner and full-integrated probes. It proves unequal positive
fixture RC wire delays are balanced without altering SRAM clock-to-Q arcs.
These RC fixtures are software regression evidence, not routed bank evidence.
Four local admission/source mutant tests pass.
