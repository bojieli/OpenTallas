# GRP private0 stage 1 source packet

Status: default-off source prototype; physical and release adoption HOLD.

`OT_KV_GRP_PRIVATE0=1` selects distinct `qkd_kvs_grp_private0` and
`qkd_kvs_grp_h_private0` modules. The switch defaults to zero. It requires the
exact merged static HROOT/FANFOLD/KITS/MU/BOOT_AGES point without DOMSPLIT and
refuses any change to the selected GRP module bodies. The generated `_gp0.sv`
file is separate; all public RTL files remain byte identical. The standalone
`qkd_kvs_grp_private0.sv` contains the same two exact private module bodies for
minimum-component proofs. Do not include both files in one elaboration.

The deletion is precisely 80 pins per GRP and 428 per H, hence 3952 across
28+4 instances: unused TOK/TEP input/output aliases, unused EST[12:1], H-only
unconsumed o_dn and H control[270:194]. EST becomes an explicit scalar input.
Live y__est__0_1 remains a direct equation, feeding all 128 PC boot-admission
consumers. Every other equation, leaf instance, leaf parameter, clock and reset
is identical to the selected merged source. No constant or placeholder port
replaces a deletion. No additional state or edge is introduced by this step.

The generator changes master selection, actual port dictionaries, binding
widths and canonical pin maps together. Both actual parent exporter function
bodies pass default/private connection tests; compressed k>1 ABI is refused
before writing (`export_receipt.json`). Both parent netlist export paths remove
only deleted named connections and explicitly select EST[0:0] and H
control[193:0]. Original producer buses and every other consumer remain intact;
there is no reliance on implicit truncation. The parent transform is idempotent
and refuses shifted/unknown slice shapes or replica counts.

## Exact source and consumer evidence

Selected full public source SHA256 is
`df66545140a103b45170c9132cf19e521945c61c8fc649e836df4bb9c49e6e97`:
`qkd_kvs_tiles_hroot_ff_k_mu_ba.sv`, not the retired `_ds` source.
`../grp_private_model_1019/consumer_ledger.json` pins the actual GEN7 bound die
and the GEN8 PREP snapshot, all32 groups, and all128 EST consumers.
`parent/parent_receipt.json` reproduces those graph identities and proves that
only the32 group instantiation lines change; declarations, producers and every
other instance are byte identical. **GEN8 final bound proof is pending.**

`generator_receipt.json` records the actual fleet generator audit. The default
schema/text/binding/pin metadata equals the exact pre-change generator. The
private32 bodies equal the deletion transform of the frozen selected source;
all other tile records equal the default records, and every retained face is
unchanged. Initial checks uncovered inherited staleness between the frozen
full `_mu_ba` file and the current generator in CTL layer-programme/ownership
modules; this is explicitly recorded. It is not caused by private0. The candidate `_gp0` full file is a diagnostic generator export. Actual private
GRP bindings select only the standalone two-module private0 file; every other
binding, including its original source file, equals the default binding byte
for byte. The public file is never regenerated or overwritten by this packet.
The inherited unrelated discrepancy therefore cannot change a retained public
binding through this opt-in.

## Verification and practical limits

The separate `../grp_private_oracle_1019` packet (commit047061e21) runs the
actual two full components with16 exact real leaf definitions, including the
real SRAM behavioral model. Every retained output is compared against the
original component: 19 output vectors, 2048 core edges, 38912 comparisons PASS.
Core/HBM clocks are independent, with reset and warm pulses. Five causal source
mutants fail at retained outputs: both EST inversions, GRP down-bit corruption,
GRP down permutation bypass, and H control corruption. Their fail witnesses
are committed. This is finite two-state sampled equivalence, not boot/CDC-phase,
production throughput or physical qualification. No leaf outputs are forced.

Generator audits ran through unpinned ot-run, 16 GB/two threads, on the frozen
source/dependency snapshot. External read-only source symlinks justify
`--no-spill`; they must not be modified. Audit r1 missing ancillary tool path,
r2 inherited full-file staleness, and r3 comment-only expectation mismatch are
preserved as earlier diagnostic failures; successful qualification uses the
correct exact pre-change baseline and exact selected GRP bodies. No physical
build, gate, submission or whole-SAFE claim is part of this source packet.

Model delta for deletion: state0, MAC/cycle0, memory bytes/cycle0, added source
edges0 for SU and MU. Removed physical ABI pins3952 is not an FF, area or token
rate saving. Area, copy loads, actual routing access, token rate and final GEN8
binding remain NULL.

## Stage 2 remains a separate model prerequisite

Registered useful boundary cohorts (especially live EST), genuine two-stage
face reset preserving async/sample semantics, kept BUF/INV-transparent <=32
copy fixed point, real boot/storage collision/lifetime, depth, native area,
full-face local contacts/PG/OBS/vias, clock spread, individual wire reach and
SU/MU compiler/STATUS/retirement calendars remain HOLD. No retired235/230-root
census, old native views, timing, macros or schedules qualify this selected
source. ROOT must review the complete stage2 model before more RTL or physical
work. Nothing here changes source defaults or current release bindings.
