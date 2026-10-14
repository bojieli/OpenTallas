# HBM front leaf decomposition — structural candidate

The rejected flattened front has 56,373 mapped sinks on one root and prior TT insertion 728 ps. The prior four crossbar slices do not resolve its roughly 18k core root. This candidate extracts the complete FIFO, SRAM, skid and double output buffer for each of eight production service lanes into a separately clocked module; the residual controller owns request generation, tags, X1 picks and completion. Wrapper clock pins are actual independent ports, with no fallback clock alias.

| Leaf | Replicas | Logical register bits/root | SRAM/root | Rate |
| --- | ---: | ---: | ---: | --- |
| Lane | 8 | 2,125 | 1 × 128×256 | one 32-byte sector/cycle |
| Controller including reset relay | 1 | 3,116 | 0 | one request/cycle |
| Crossbar slice | 4 | 11,048 | 0 | eight destination sectors/cycle |

These are unmapped Yosys Q-bit counts; actual mapped sink counts, CTS insertion and leaf arrival spread remain unmeasured. All candidate roots are below 15k before mapping. The byte-exact NL2 production bench reports 2,921,984 bytes in 14,482 cycles, 201.8 bytes/cycle, preserving predecessor behavior and its crossbar extra cycle. The immutable price remains untouched. This is not a measured priced-layer acceptance.

The extraction exposes rather than resolves the combinational grant loop: request-bank flops feed controller arbitration, while combinational grants drive lane retirement. A true registered seam needs an outstanding-grant scoreboard and buffer identity so delayed grant receipt cannot duplicate slots or free the data before the slice consumes it. The lane output mux bf[pa] also needs a launch register and aligned selection/valid stages. Metadata/config pins need local capture. Until that protocol is implemented and its cycle cost measured, no route or die membership is submitted for this candidate. CLOSED leaves are untouched.
