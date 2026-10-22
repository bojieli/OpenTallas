# Exact PV replica zero padding

Source helper 6279dd8fa proves only the high zero positions emitted by the hashed PV trunk generator. It verifies each source row, actual replica master/output slices, and same-bit zero ancestry through inserted physical repair replicas. Live low bits, command/reset copies, delay tails and public metadata receive no permission.

On source219049242d, the canonical strict receipt changes unread bits from162853 to45789, exactly117064. All73 open output types and4 unconnected inputs remain FAIL; there are no ties, undriven bits, multiple drivers, width errors or unresolved/ambiguous children. The5356 remaining PV bits are separately inventoried and are not covered by this contract. Full receipt and pad hashes are in baseline_summary.json.

GEN4 source593176b58 uses qkd_pvw_die_tb. Admission requires the exact hashed kv_bootage.py and generated qkd_pvw_die_t_ba.sv, alongside the original trunk hashes. An independent fleet check confirmed pvw_variant(original source) equals the actual successor byte for byte. It changes the control interface/age and leaves the standard-replica station rows unchanged. The actual GEN4 R2 netlist derives the same117064 bits; this is a padding derivation, without a die closure claim. An unknown successor or any changed source refuses admission.

Fourteen focused tests cover source mutation, successor forgery, replica output identity, inserted repair ancestry, dynamic/nonzero pads, unexpected live ties, global output permissions, live consumers, unknown expressions and stale die receipts. tests.log records the run.
