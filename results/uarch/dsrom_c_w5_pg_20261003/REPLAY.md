W5 Scenario C default-off component. Base: `4a18e3cc0b4c04f75a2e76e4535d9560cdc730c6`.

Run from the repository root; choose a fresh output directory:

```sh
python3 tools/dsrom_c_w5_validate.py --out /tmp/dsrom-c-w5-replay-fresh
```

This runs seven meaningful model tests, compiles and executes the digital RTL fixture, then regenerates the Liberty screen and conditional model. `local_final/inputs.json` pins every replay input. `liberty.json` pins every archived Liberty. `toolchain.json` identifies the container and tools. The source-controlled `model.json` adds the local digital-fixture receipt and a provisional 292-controller array allocation to the generated model; it does not qualify production wake or power.

Generic controller synthesis (no timing/physical qualification):

```sh
docker run --rm -v "$PWD:/work" -w /work --entrypoint yosys \
  sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34 \
  -p 'read_verilog -sv rtl/v41rom/ot_dsrom_c_w5_pg.sv; chparam -set ENABLE_PG 1 ot_dsrom_c_w5_pg; synth -top ot_dsrom_c_w5_pg; write_json /tmp/w5-netlist.json; stat'
```

The analytical model was emitted before RTL in `model_preRTL/`, and revised before mutable-state protection in `model_pre_protection/`. The generic controller has 14 retained FF bits and 147 generic cells (measured synthesis inventory). A conservative NAND/INV/dual-reset-FF construction uses the archived SS/TT/FF Liberty cell areas and maximum on-rail state leakage. This is model allocation, not a mapped netlist, hardened element or closure. Switches, clamps, retained external debt, CDC, CTS, fanout, PDN and SerDes remain unpriced. On-rail logic states do not characterize off-rail leakage; no 10% residual is adopted.

RTL use: instantiate the controller in an always-on island. `ENABLE_PG=0` by default. `ALWAYS_ON=1` keeps Engram powered; the model always includes its inherited 3324.4 W. Debt inputs and identity/protection live outside the switched island. The controller latches a prewake pulse, waits for inrush grant before cold/ramp power request, requires power-good and relock, adds a priced minimum guard and release dwell, and clamps valid and data until ready. State parity faults fail closed and stay sticky. The link wrapper unions both endpoint activities/prewakes and separate protected TX/RX debt. All input ACKs/debt are synchronized before this interface: actual CDC and distribution delay must be priced externally.

Prewake is derived from explicit directed `SUCCESSOR_EDGES`, never numeric ID adjacency. The fixture uses 0→2→1→3→0. The model accepts a W2 domain map (`domains`, `successors`, link `endpoints`) and an observed tick calendar (`busy`, `live_debt`, `explicit_wake`), counting the union of actual awake domains. It has no production calendar yet. A start-phase pulse must be held/handshaken over any CDC by the parent; no free pulse transport is assumed.

Measured fixture: zero added scheduled-token cycles and exact clamp payload; deliberately late wake adds seven cycles. It covers isolation ACK ordering, delayed grant, power-good/relock wait, every stage debt bit, TX/RX link debt, either endpoint, reset-retained debt, lock loss, parity fault, default-off bypass and Engram. These are controlled digital environment delays, not analog wake/relock measurements or complete token numerical evidence.

`coordination.json` pins read-only W2 Arendt and W4 Maxwell snapshots and specifies required joins. W2's source packing and new split-delivery/auxiliary ABI do not transfer the inherited C rate. Maxwell's W4 attribution provides no qualified replacement PG rectangle or wake-droop result. Acknowledgments, actual stage/link residence, off-rail switch and SerDes standby characterization, inrush/ramp/droop and loaded SS/FF with 60/25 ps uncertainties remain open. Hub routing-layer and slot-fit checks are pending. No hardware adoption or array saving is claimed.

Failed records are retained: `rtl_r2_FAIL/` (cold startup demand), `rtl_r5/` (fixture sleep interaction), `liberty_r3_FAIL/` (dangling FF Liberty alias), `synth_generic_r3_FAIL/` (local old Yosys unsupported syntax), and `validation_discovery_FAIL/` (unrelated ABI package missing from sparse checkout). Historical source/records, including the assumed 7.07 kW PG result, remain byte-identical. The direct test-file invocation avoids unrelated discovery imports.
