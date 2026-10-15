Native lifecycle provenance for localhost:8765

Endpoint: /api/native/coverage?design=qwen_rom (also ds_rom, ds_rom_mtp,
hbm_gen_qwen, hbm_gen_qwen_mtp, hbm_gen_ds). The token page renders its actual
operation rows, per-node mapping, missing edges, and current die-gap ownership.
Old timing/numerical/priced token records keep their original scope.

index.json is read from origin/main. Every dependency is an immutable full git
commit, repository path, and SHA256. A missing/hash-mismatched dependency fails.
The source index itself is identified by the response's source_commit. There is
no join on element registry categories, globs, CLOSED job names, or old rates.

A design supplies:
- operation_gate: the pinned tools/native_operation_coverage.py implementation.
- programs: [{id, program:{commit,path,sha256}, bindings:{commit,path,sha256}}].
  The actual operation gate is replayed against the program bytes and real
  elaboration/source files referenced by that binding manifest.
- program_inventory: a pinned JSON {programs:[{id,sha256}]}. Every original
  emitted program must appear exactly once; deleting one does not pass.
- token_graph: the pinned actual lifecycle JSON. Node deletion or changing
  topology without updating/requalifying its authoritative source fails.
- node_operations: exact token node -> [program_id:operation_id] mapping.
  Dangling nodes, missing operations, and multiply mapped operations fail.
- physical_bindings: every real component instance and operation engine must
  map to a routed leaf. The optional leaf_instance names a containing routed
  instance; a target outside that leaf hierarchy fails.
- schedule: a pinned receipt whose program_sha256 map equals the entire emitted
  inventory, exact_timeline=true, all_native_producers=true, unplanned_stalls=0,
  and runtime_backpressure=false. It is independent of numerical equality.
- external_models: explicitly named boundary exceptions with boundary_kind,
  boundary_ports, scope and supplies_internal_compute=false. Only PHY,
  inter-die/network wires and off-chip signal/memory boundaries qualify;
  digital on-chip controllers/adapters/compute remain real RTL requirements.
  The operation gate's off_chip_signal role can represent an external wire;
  its explicit exception distinguishes the inter-die/network boundary.

A physical binding contains master, slot, target_commit, route, files, contract,
die_bind, die_netlist, grt and die_sta. Each artifact field is a pinned reference.
The route receipt must link:
- canonical elaborated module SHA256 and actual RTL source SHA256 map;
- exact LEF/TT/FF artifact hashes and CLOSED TT setup>=0, FF hold>=0, DRC0;
- measured native phi_minus_R launch<=220, capture<=190, spread<=80 ps.
The contract slot must name the same master and exact artifact hash map.
The actual general die port-bind report must pass with that master instantiated,
and pin the die netlist and contract hashes. GRT must pin the same netlist,
contract and per-master physical artifacts with overflow0. Die TT/FF signoff
must pin that GRT and netlist. Missing legacy fields fail rather than inheriting
an unrelated verdict; producers must publish truthful source-bound receipts.

Current data limits:
- Qwen's 297-program/7266-operation audit is pinned, but full replayable target
  inputs/elaboration and physical mappings are absent. Its failure-only receipt
  adapter preserves every audited instruction hash/reason. It cannot produce a
  native PASS, even if a receipt says PASS. Mapping the old 505-node token graph
  onto actual rank/program operations remains explicit unproven work.
- S81's original S000..S058 instruction JSON is replayed (59 programs/2367 ops).
  The exact instruction IDs join 2367 lifecycle nodes; 363 further token nodes
  remain unmapped. The integrated target absence manifest is derived from
  S-FUNC's source-pinned native inventory; standalone arithmetic probes do not
  replace real full-layer elaboration and memory/physical bindings.
- Current HBM and MTP complete native program inventories are absent. The API
  reports that missing edge, rather than adopting the old simulator listing.
- Current 19-group die audit supplements precise reasons/owners. It never grants
  qualification and its timestamp/source pins bound its scope.

Verification uses a real Yosys-elaborated engine and memory with synthetic
physical receipts to test the join, not to claim physical closure. Positive join
plus deleted node/program, reference compute producer, stale route source,
missing memory physical binding, missing file, stale die receipt, and explicit
external-boundary mutations are checked by test_native_provenance.py.
