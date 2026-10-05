Opt-in existing native input-cut build selection, source integration only.

The actual caller archive57ab802e uses dsrom_source_cut/Vcut, dut.u_sp and
 dut.vm; PHW10/VAW16/R128, FAST1 PP1 BP0 NP4096 NBF724. The latter two are
retained cut labels: RT_CUT suppresses the field array. Physical source mapping
remains canonical S81 NP2417 BF519. No geometry, phase or VM alias is invented.
The source template preserves the actual native ports and source observations;
STATIC_CONTROLS defaults0. Only the frozen static serialized top is selectable.
PQ flat-only top refuses; Epicurus owns its required tagged RT_CUT surface.

Source-only selection (no compile):
python3 tools/dsrom_s81_static_native_cut.py --enable-static-controls \
 --reference-cut EXISTING_NATIVE_CUT_DIRECTORY --control-stage 37 --rank 0 \
 --out FRESH_SELECTION_DIRECTORY
Optional --build is admitted EPYC2-only, after frozen functional-provider
source/model and existing-compatible-archive check. It builds ONLY Vcut,
not pair/return/root/VM/quantizer/whole-field models or an executable/testbench.
G0/physical containment gates P&R, not this minimum functional compilation.
No model regeneration, runtime, proof campaign or active job replacement.

The existing archive-only host linker tools/dsrom_s81_minimum_link.py NEW
--static-native-cut FRESH_SELECTION_DIRECTORY/selection.json validates the
actual completed static cut's headers/archive/build command and source pins,
then chooses that archive/include path and BOTH matching DSROM_S81_STATIC_
CONTROL_STAGE/MODEL_STAGE defines. It replaces s81_minimum_qe.cpp with
s81_minimum_qe_static.cpp exactly once. Existing controls TU is retained, QE
root-tag TU replaces the same source-tag component namespace, never both.
Foreign/old Vcut includes/archives and unbuilt plans refuse before compiler
execution. No flag alone can select the mutable-array cut as static hardware.
Default linker inputs/source selection remain unchanged.

For actual source fragment controls call EXISTING emit_native_phase_controls
with NEW static_native_cut=selection.json. This selects the SAME compiled
stage/rank/canonical assignment's immutable image and existing linked SBASE;
canonical phase/key/CFG25*phase remain unchanged. Parent keeps actual captured
expert IDs, positive SourceIo/span/VM publication/ACK and shared clock/context.
No zero image, expected inputs, phase0 relabel or intermediate-ACK substitute.
Provider/runtime hardware adoption/loaded physical timing remain open.

Completed selection directory is portable as one directory with obj/ plus
selection.json. Model paths resolve relative to that directory; canonical
image paths resolve against the caller's current source checkout. Frozen
source/artifact hashes must still match; relocation is not a source override.
Cheap checks PASS:3 Python source parses, original native port/observer block
byte-identical, exact reference parameters and stage37/rank0/image/flags
binding, refusals for unbuilt cut, flat PQ, and different stage enrollment.

ONE minimum stage37 baseline-static cut compilation EPYC2 TERMINAL0.
Public Vcut.h hash equals retained actualcaller ABI. Completed enrollment
checks PASS, dut.vm present, no dut.u_f field array. All7 COMMON arithmetic
sources match retained cut exactly. No runtime/numerical/physical gate claim.
Exact remote build path and artifact hashes: terminal.json plus
selection.stage37.rank0.json. Other model archives remain reused unchanged.
