# ROM read-path circuit evidence

[Project home](../README.md) · [Documentation](../docs/README.md) ·
[Physical methodology](../docs/ROM_PHYSICAL_METHODOLOGY.md) ·
[Contributing](../CONTRIBUTING.md)

The circuit work is intentionally split into evidence levels. Passing a later
level does not turn SKY130 into an N7/N4 scaling anchor.

## Generic topology smoke test

`via_rom_read.sp` is the smallest precharge/evaluate NOR-ROM experiment:

- a programmed cell has a drain connection to the bitline and discharges it;
- an unprogrammed cell omits that connection at the programming-via layer;
- a programmed cell behind a masked wordline remains inactive;
- simple inverters demonstrate sense polarity.

`make verify` runs generic level-1 MOS models. This checks only topology and test
plumbing.

## Pinned primitive-model campaign

`run_sky130_rom_read.py` runs 51 deterministic SKY130 BSIM cases over declared
SS/TT/FF, supply, temperature, synthetic bitline-capacitance, and output-load
dimensions. `array_rows` changes only an explicit lumped capacitance; it is not
physical array geometry. Results are in `results/spice/sky130_rom_read.json` and
`results/spice/ROM_READ_REPORT.md`.

## Physical slice and extracted campaign

`sky130_rom_slice/generate_layout.tcl` creates two matched custom-transistor
columns under the exact locked public SKY130A deck. They differ by one physical
via1 connection. `tools/run_sky130_physical.py` verifies the complete PDK tree
and pinned tools, generates MAG/GDS/EXT/netlists, requires zero Magic DRC errors,
parses an explicit unique Netgen LVS verdict including ports, audits topology and
the one-via invariant, extracts capacitance, and hashes every archived artifact.

The current governed result is:

- zero DRC errors;
- unique LVS match for 10 MOS devices, 15 nets, and 10 ports;
- six via1 shapes in the present half versus five in the absent half;
- 59 extracted capacitance elements in the deliberately roomy two-column slice.

`tools/run_sky130_extracted_pvt.py` instantiates the exact archived PEX slice and
runs 33 deterministic PVT/load cases; all currently pass. It uses a minimal,
hash-recorded subset of the installed 1V8 SKY130 models instead of loading
unrelated device families. See `results/spice/sky130_physical/REPORT.md` and
`results/spice/SKY130_EXTRACTED_PVT_REPORT.md`.

`tools/run_sky130_extracted_mismatch.py` uses that same PEX and the installed TT
1V8 NFET/PFET per-instance mismatch equations. It runs 256 contract-derived,
recorded seeds in fresh ngspice processes, puts `.option seed=<value>` in each
deck before model expansion, and repeats one seed exactly. The current run has
256/256 local functional passes, an exact same-seed replay, and measured
cross-seed spread. See `results/spice/SKY130_EXTRACTED_MISMATCH_REPORT.md`.

This is finite sampling of a public compact-model mismatch mechanism. It is not
a silicon-yield estimate, a defect model, a spatial/systematic-variation model,
or sign-off Monte Carlo coverage.

## Distributed-interconnect extraction

`tools/run_sky130_resistance.py` uses Magic's integrated detailed-resistance
flow on the exact archived layout. Network, delay, and resistor-pruning
thresholds are zero and simplification is disabled. It extracts nominal,
high-R/high-C, high-R/low-C, low-R/high-C, and low-R/low-C styles twice in fresh
directories and requires exact semantic equality of ports, devices, resistor
edges/values, and capacitor edges/values. Every netlist contains ten MOS
instances, 630 explicit resistor elements, and 269 capacitor elements; the
strengthened graph check also proves that the programmed and absent-via drain
components remain disjoint.

The current deterministic campaign passes 165/165 cases over the same 33 PVT,
supply, temperature, and load points per interconnect style. Nominal local
discharge delay is 0.0412 ns, versus 0.0354 ns for the capacitance-only PEX. The
declared style envelope at nominal TT is +5.2% to +38.5%. Because detailed
network subdivision also redistributes capacitance, these are full-RC-versus-
capacitance-only deltas, not a pure resistance penalty. See
`results/spice/sky130_resistance/REPORT.md`.

## Independent IHP SG13G2 replication

`tools/run_ihp_device_smoke.py` establishes the independent foundry-PDK device
path before any IHP layout is interpreted. It verifies a pristine, recursively
locked IHP Open PDK v0.3.0 checkout, compiles all four official ngspice
Verilog-A modules twice with `-D__NGSPICE__ --target_cpu generic`, requires the
two output sets to be byte-identical, and keeps every generated OSDI file outside
the immutable PDK tree.

The official `sg13_lv_nmos` and `sg13_lv_pmos` wrappers then pass a 1.2-V,
27-°C TT DC/transient inverter smoke test. Exact source, PDK, compiler,
simulator, generated-module and log identities are in
`results/spice/ihp_device_smoke/device_smoke.json`; the concise report is
`results/spice/ihp_device_smoke/REPORT.md`.

`ihp_sg13g2/rom_slice/generate_layout.tcl` independently implements the same
controlled-via contract using native IHP low-voltage MOS generators and legal
remote M1/M2 landing sites. `tools/run_ihp_physical.py` requires zero full DRC
errors, a unique ten-port LVS match, ten MOS devices and fifteen nets, six
top-level via1 shapes on the programmed side versus five on the unprogrammed
side, and a distinct `ROM_DRAIN_ABSENT` endpoint. The capacitance PEX contains
59 elements; the 32.5 × 11.5-µm layout is deliberately roomy and is not a
density macro. See `results/spice/ihp_sg13g2_physical/REPORT.md`.

`tools/run_ihp_extracted_pvt.py` uses the exact archived PEX, official
`cornerMOSlv.lib` SS/TT/FF sections, and the four pinned OSDI modules over the
same 33-case process/voltage/temperature/output-load structure used for the
primary methodology vehicle. All 33 cases pass. See
`results/spice/IHP_SG13G2_EXTRACTED_PVT_REPORT.md`.

`tools/run_ihp_resistance.py` invokes all five public IHP Magic RC styles with
zero thresholds and simplification disabled. Every style is extracted twice in
a fresh directory; exact semantic equality is required for ports, MOS
terminals/parameters, resistor edges/values, and capacitor edges/values. Each
netlist contains ten MOS devices, 41 explicit resistors, and 68 capacitors. The
resistor graph proves programmed/absent topology separation and retains
positive-resistance paths from all six extracted NMOS body nodes to ground.
All five semantic replays and 165/165 full-RC electrical cases pass. See
`results/spice/ihp_sg13g2_resistance/REPORT.md`.

Reproduce the optional PDK campaign from the repository root with:

```bash
make spice-pdk
```

These runs do **not** establish a compact ROM macro density, distributed
full-row/column resistance, silicon yield, sense-amplifier offset, full-array
current, IR/noise, repair, target-node behavior, late-via mask
availability/economics, whole-wafer performance, or silicon correlation.
Compact/full-array extraction, IHP mismatch/yield characterization,
target-foundry macros, product statistical sign-off, and a reticle test vehicle
remain separate gates.
