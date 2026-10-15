Explicit raw SRAM clock-entry helper, 2026-10-15

`tools/ref_tile/direct_macro_clock_entries.py` is opt-in on each `spec.macros`
item: `clock_entry: {port: NAME, pin: clk, reference: raw_liberty_clock_pin}`.
`load(spec, source_root)` returns `entries` with exact Liberty/LEF SHA256s,
physical dimensions and corner semantics, plus `bindings_tcl` defining
`ot_ce_direct_rows corner`. This hook returns the existing nine-field CE row
format. Call after hard-child rows, check duplicate source ownership, add each
source to `seen`, and include the number of direct entries in hard-port coverage.
Source compensation for these rows is `phi - actual_clock_wire`; the zero
internal offset denotes a Liberty-pin reference, never measured zero insertion.
The actual SRAM setup, hold and clock-to-Q arcs remain untouched in Liberty.

Admission requires one explicit instance, an exclusive declared hard clock port,
actual LEF CLOCK/INPUT pin geometry and positive dimensions, all three uniquely
named native-corner libraries, memory semantics, unique input clock, real
setup/hold/clock-to-Q arcs, and no routed-ETM insertion arcs. Runtime checks actual
linked instance/master/pin/source/corner association and a finite propagated
clock path. Physical-mode direct entries require a positive measured wire.
The normal source-binding machinery must preserve the exact declared artifacts.

Validation:

- Three Python unittest methods PASS, including bad clock identity, missing hold,
  wrong library corner, CTS-root collision, unknown source, and multi-instance
  binding rejection. Both actual memory macro families in QCOLL S3 were admitted
  from its current explicit nine-entry source spec during development.
- Real OpenROAD 26Q3-1510-g6cb3f2b704, ORFS image
  `sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`.
  Unit `oth-ubuntu-3784404-1792054096`, ot-agidock128, 2 GB/one thread, terminal
  status zero. Full logs, source hashes and nine-case receipt are alongside this
  file. TT clock-wire arrivals are 9.943751591 and 19.887503182 ps; reference
  balancing brings both to the larger value and the real SRAM output-path slack
  changes by exactly the source shift, preserving internal clock-to-Q arcs.
  TT, FF and SS positives PASS; wrong-source and wrong-corner DUT bindings fail
  the actual runtime guards in every corner.
- The SPEF is an explicit nonzero-RC fixture to test STA semantics. It is not a
  routed parent, extracted-layout signoff, or a QCOLL native qualification.
  Shared-flow integration and the actual QCOLL parent route remain separate.

Reproduce Python admission:
`python3 -m unittest discover -s tools/ref_tile -p test_direct_macro_clock_entries.py -v`

Run the remote probe under `ot-run --mem 2 --threads 1` in the declared ORFS
container, setting `OPENROAD=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad`:
`python3 tools/ref_tile/test_direct_macro_clock_entries.py --openroad-probe OUT`

Initial infrastructure attempts are not evidence: host/container PATH lacked
OpenROAD, then the fixture lacked a technology LEF, used the wrong SPEF pin
delimiter, and queried an unsupported path property. The final suite fixes each
of these and checks numerical output-path slack and clock tags directly.
