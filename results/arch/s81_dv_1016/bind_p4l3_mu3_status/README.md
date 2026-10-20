# S81 MU successor: reset-view identity and endpoint status

Base mu2 6050bfac9 remains the running pilot of record. This isolated successor pins CLOSED po2 landing 562 (record 23d9cbb8c) and 512 (306a99997) with two reset landing stages, matching 276/276l/70. The strict landing-reset comparison reads the actual closure source kit and passes for all seven used landing masters. The nine landing-reset unit tests pass.

MU endpoint sticky faults at s_0S/s_0N/s_7S/s_7N now connect to the explicit endpoint_fault status vector, alongside the existing land_fault boundary. Mapping is recorded in bind_case.json and status_bind_check.json. This closes the previously unconnected endpoint outputs and retains per-endpoint attribution. It does not claim a hardened physical status-collection network: no existing die-wide status fold was implemented in mu2, and routing/relay qualification remains owed.

Validation: real-plan netlist emission plus generated-connection assertions PASS (four distinct fault bits, landing-reset PASS). Full strict port bind exceeded the local 120-second command bound and remains pending on the fleet; no strict-bind PASS is claimed. This is not a new die GEN or a sign-off result. Do not merge token-lineage dv_bind from TOK/LINECOL/MUREPLAY/MUWIN.
