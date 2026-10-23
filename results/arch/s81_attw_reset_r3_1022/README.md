# ATTW controller reset distribution R3

Source-level structural successor to the frozen ROOT0/ROOT1 controller inventory at e6455d4b0. Enabled only by OT_S81_ATTW_RESET_R3; all ports, arithmetic, pipeline registers, existing storage and frozen parameters remain unchanged. This packet does not qualify a parent or claim native closure.

The original ROOT1 census has 7,542 violations and maximum fanout 15,376. The worst driver is the second stage of u_rl.rs: its complement drives reset control across the controller. Other large cones include engine merge valid and SRAM write-through data captures; R3 does not claim to fix those enable cones.

R3 distributes each source reset consumption through a retained, non-inverting binary buffer tree. Each internal fork drives two inverter inputs; each leaf ends at an original reset expression or child reset port. A process uses the same leaf for its asynchronous event and reset condition. Repeated generate consumers can still create fanout at a leaf; the new native census is required to measure these and remaining enable loads. This is RTL structural hierarchy, without cloning or rewriting a mapped graph.

The existing two-edge asynchronous-assert/synchronous-release u_rl reset synchronizer remains unchanged. The buffer tree adds no clock edge. Startup release age stays two edges; data and valid latency, initiation interval, boundary widths and bytes/cycle remain the baseline's. Combinational reset distribution delay and physical reach still need placement qualification.

The measured original ROOT1 controller contains 1,527,092 mapped cells, 165,582.523 square microns of standard cells, 32 SRAM256x256 and 38 SRAM32x128 macros (70 real macros, 2,252,800 bits). These storage counts must match in R3. Additional buffer area and actual fanout will come from the successor census; no floorplan is sized from a guessed smaller controller. No gate or parent bind is authorized from this packet alone.

R4 adds OT_S81_ATTW_ENABLE_R4. The SRAM wrapper distributes each same-cycle write enable to at most 32 captured data bits or one SRAM bank, and each bypass select to one 32-bit output word. No macro, data register, port, cycle or arithmetic changes. Exact 2,120-bit Verilator 5.050 comparison passed 19,936 checked cycles with 5,325 same-address writes; the bypass-polarity mutant failed at cycle 64 with FMEM_R4_MISMATCH. Full-controller native R4 is required to measure surviving controls.
