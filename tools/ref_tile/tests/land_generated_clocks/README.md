# LAND generated-clock schema proposal

`tools/ref_tile/land_generated_clocks.py` is an opt-in, standalone typed schema
and emitter. No existing gate hook, `multiple_cts_roots` guard, CE uncertainty,
source clock, path exception or CTS admission rule changes. This is a ROOT
review proposal and cannot qualify LAND or admit its CTS job.

The schema requires all exact RTL sources, top, parameters and defines; hashes
for the behavioral certificate and waveform witness; a separate behavioral
source-binding artifact; and a compiler/die-owned scenario manifest. That
manifest contains the exact K/phase/age/reset case, actual native root
period/rise/fall, absolute reset origins and first usable edge, immutable
compiler inputs, mapped netlist and mapped ICG identities. A certificate must
cover all 8 K values, 8 root phases, both reset orders, every declared age band,
and four banks per case. Emission selects one exact compiled case and preserves
its real native phase. PH .875 stays .875; E_case is never substituted for a
physical waveform. Root phases must already exist and match the compiled case.

Native ICG master/pin semantics come from hashed Liberty
`clock_gating_integrated_cell : latch_posedge` and actual clock/enable/output pin
attributes. Runtime Tcl checks the exact loaded Liberty and mapped netlist
hashes, one actual target instance and every pin, native master, primary source
port, root period/rise/fall and clock lineage. No wildcard or clock-name
heuristic supplies ancestry. Foreign clocks, double wrappers, stale hashes,
missing/duplicate cases, wrong generated edges and alternate timing hooks refuse.

Ordinary 60ps setup/25ps hold and cross-family 150/210ps setup plus100ps hold
remain prerequisites in the separate CE implementation. The emitter never
removes, weakens or manufactures an uncertainty. Its dependency is the reviewed
native family API from `codex/genclock-family-1019@b2cbf3555`:
`ot_cf_refresh`, `ot_cf_root`; that API must be merged and daemon-synced by ROOT.

## Evidence and scope

`evidence/fleet.log`: 15 tests PASS on the fleet with OpenSTA3.1.0,
`openroad/orfs:latest`. One native test creates eight exact ICG declarations;
two real STA negative tests reject foreign primary sources and native phase
changes. Remaining negatives cover source hashes, custom hooks, waveform
mutation, incomplete coverage, reserves and witness identity. The test fixture
is a mechanism probe, not the LAND netlist, physical phase join or ICG timing.

The test also independently checks all1536 rows/384 cases in actual LAND
`gated_phase_joined_r2_384.json`, source branch
`codex/safe-qw-land-1019@f544cb1a3` (later certificate checkpoint1461bca01),
SHA256 `a1ffbdc6209fb17a025c835d548a7c1caed8d39f5f6b4c68c8cf75f9be23665f`.
It requires the real .875-age case and rejects removal of one bank row.
No actual LAND compiled physical scenario has been fabricated or emitted.

## Remaining admission work

The compiler/die phase owner must produce and validate the source-bound
manifest, including real reset-origin/boot-first-usable and enable-waveform
joins. The current existing behavioral certificate alone lacks that complete
binding. A mapped identity JSON is a cross-check, not proof of its own producer;
the runtime native netlist/Liberty checks do not independently establish the
enable cone's entire periodic behavior. That producer and source-bound enable
proof require review before any gate integration. Never turn missing evidence
into a boolean waiver.

The gate integrator must install a typed preCTS hook without opening arbitrary
`sdc_extra`, `boundary_tcl` or `pre_cts_extra`. For runtime-selectable/unstrapped
K or phase, all legal scenario timing runs and exact receipts are mandatory;
one emitted script is only one scenario and cannot confer all-case closure.
The immutable compiler inputs must establish any narrower compiled scenario.
Every family still needs explicit ordinary base uncertainties, CE cross-family
projection, actual ICG gating setup/hold, all data/select/status/reset paths,
TT setup/FF hold, native descendants/spread, propagated physical root references
and boot-first-usable bind. Source hashing and a native census are insufficient
phase qualification. No masks, false paths, multicycle data paths or invented
root phases are authorized by this proposal.
