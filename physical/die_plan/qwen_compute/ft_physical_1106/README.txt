Explicit VMR/CRH physical FT interface; ROOT-authorized narrow shared integration.

Opt-in hard_cores[].physical_ft = {proof, proof_sha256, unconsumed_outputs};
existing native_port_adapter = {merge:{}, cycles:0,
 tie:{ft_ck_i:"1'b0",ft_rst_i:"1'b0"}}. Exactly two supported masters:
qfd_dv_s8x_vmr and qfd_dv_s8_crh_rp1. No global pin exemption, pin deletion,
LEF/lib/OBS rewrite, clock/reset/data timing exception or source-stage change.

Qualified actual captured routed netlists, signoff, routed LEC, FT declarations,
characterized FT interface, primitive Liberty and exact views are self-contained
under vmr/ and crh/. Graph is re-proved from actual netlist consumers and primitive
Boolean functions; port names never classify a path as unused. Each actual FT
clock cone is one BUFx16f ot_isl_ckft, reset cone one BUFx4f ot_isl_rstft,
with no other core port/state/load and no shared signals. Tests inject a core
clock consumer and compound expression; both fail. Selected view hashes and
canonical core pin content must match captured qualified source (1509/998pins).
Retained core timing pins may not reference FT inputs.

The full physical ABI adds exactly four declared scalar FT ports to the physical
blackbox header, preserving the original logical header and existing parameter
identity processing. All input ties must be literal zero in both metadata and
actual selected native instance; FT outputs are explicitly unconsumed and any
connection fails. The complete actual LEF/Lib/OBS bytes remain unchanged. GEN
archives its exact FT source evidence and per-instance accounting with the kit.
Standalone prov_view uses its explicit --src matched helper cohort, never an
ambient PYTHONPATH; invalid physical FT metadata cannot fall back to a contract.
All absent-opt-in generation behavior remains unchanged.

Actual SU2/SUc source/header smoke E5 dedicated scratch2, unit
oth-ubuntu-1483481-1793984201 exit0: five actual native instances, every old
port connection unchanged, ten zero inputs added, ten outputs explicitly
unconsumed, cycles0. Both generated physical headers compile with iverilog;
nonzero-input and consumed-output mutants caught. Both actual full physical
view checks PASS with every core pin retained plus the declared four FT pins.
Detailed actual.json and core_metadata.json are retained; original native capsule
and failed provider checks remain unchanged. Twelve focused actual-proof tests
PASS (before relocation into this portable package); actual source-cohort full
view/header checks are separately captured.

This source and physical interface are READY FOR ROOT REVIEW. Normal physical
GEN and CTS/P&R remain held until that review, per root instruction. No parent
or child qualification is promoted by this integration; the independent SU8
legacy model remains explicitly provisional in the separate pilot packet.
