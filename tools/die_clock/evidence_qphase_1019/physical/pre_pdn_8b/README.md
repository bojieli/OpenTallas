# Actual full clock preparation before original PDN

Fleet unit4172919/source8b5a269f4 exits0 on immutable dv2f16 diagnostic geometry.
All42,981 clocks retain actual coordinates/orientation and receive fixed rows;
the total merged row count becomes23,377. Existing cell geometry and the exact
row-derived core `[0,0,31730346,24288660]`DBU remain unchanged. Only the two
supply SWires are removed in a NEW ODB. Neither live GEN nor source snapshots
are modified. This is preparation, not power or timing qualification.

Input ODB SHA256
f8ba8846473eb8a84fdfc3643583224bbda87ed5e280f057320d7209b9ca3bba;
output `before_original_pdn.odb` SHA256
77107fc5e3b57719e756f549d5e1d7db609f4f3d58bfd1fa7e94250ba643fb8a,
350,615,593bytes. All-cell geometry digest is
b602b8a3fd354b7269bfd9d292de06e0a08d4bed51bdb9672d6868da0eb08dff.
The source-bound planned blueprint retains7,081 actual long M8/M9 polygons,
digest89b1c910544719ad71fd88999f243a705094836972272a54a70322a1b868a47c.
`prepare_record.json.gz` and `prepare.log.gz` retain exact metadata/clock IDs.

The actual-ODB negative control unit4191982/source9b8655e53 exits1 at the exact
mesh guard. `reference.json.gz` is a separate mutant of the actual preparation
receipt: first polygon xMin advances1DBU (1nm), with a consistently recomputed
mesh digest. The actual geometry, GEN, clock manifest, cell geometry digest and
policy still match. `verify.log` rejects it with
`actual generated mesh differs from planned source-bound blueprint`. This is
an actual wrong-metal witness; no synthetic phase or future PG is certified.

One isolated original full-PDN generation/strict verification is active at
unit4183868, source9b8655e53,80GB/2threads, using the prepared whole-clock ODB.
It records the original stock PDN/PHY/constant-contact source hashes and keeps
all constant and clock contact/stack-short/native VDD/VSS prerequisites. Actual
generated mesh and all cell geometry must match before those checks. There is
no shared GEN scheduling hook and no timing/admission. Runtime image ID:
`sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`.
Remote receipts are under
`ot-epyc4:/srv/opentallas-scratch/claude/qwen-clock-phase-1019/pg_safe_sites/`.
