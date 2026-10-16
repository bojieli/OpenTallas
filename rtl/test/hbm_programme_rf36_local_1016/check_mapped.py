#!/usr/bin/env python3
"""Check the production candidate's actual mapped load and clock partition."""
import collections
import hashlib
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
module = json.loads(path.read_text())["modules"]["hbm_programme_local_production"]
cells = module["cells"]
ports = module["ports"]
fanout = collections.Counter()
clock_ff = collections.Counter()
macro_clock = collections.Counter()
driven = set()
ff_outputs = set()
transparent_outputs = {}
types = collections.Counter(cell["type"] for cell in cells.values())
macro_type = "ot_sram_1r1w_128x256_m1_r2c2"
for cell in cells.values():
    for port, bits in cell["connections"].items():
        if cell["port_directions"][port] == "input":
            fanout.update(bits)
        else:
            driven.update(bits)
    if cell["type"].startswith("DFF"):
        clock_ff.update(cell["connections"]["CLK"])
        ff_outputs.update(cell["connections"]["QN"])
    if cell["type"] == macro_type:
        macro_clock.update(cell["connections"]["clk"])
    if cell["type"].startswith(("INV", "BUF")):
        inputs = [bit for port, bits in cell["connections"].items()
                  if cell["port_directions"][port] == "input" for bit in bits]
        outputs = [bit for port, bits in cell["connections"].items()
                   if cell["port_directions"][port] == "output" for bit in bits]
        assert len(inputs) == len(outputs) == 1
        transparent_outputs[outputs[0]] = inputs[0]

assert types[macro_type] == 476, types[macro_type]
assert len(ports["command"]["bits"]) == 9688
for bit in ports["command"]["bits"]:
    # DFFHQN maps an inverted storage output plus an output inverter.
    assert bit in ff_outputs or transparent_outputs.get(bit) in ff_outputs, "unregistered command bit"
assert max(fanout[bit] for bit in driven) <= 256, "shared command/control driver"
for port, width in (("clk_ctl", 4), ("clk_cmd", 41), ("clk_macro", 476)):
    assert len(ports[port]["bits"]) == width
    assert len(set(ports[port]["bits"])) == width
assert set(macro_clock) == set(ports["clk_macro"]["bits"])
assert set(macro_clock.values()) == {1}, "macro clock input must serve one actual macro"
assert all(clock_ff[bit] for bit in ports["clk_cmd"]["bits"])
result = {
    "mapped_json_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "actual_macros": types[macro_type],
    "actual_ff": sum(v for k, v in types.items() if k.startswith("DFF")),
    "actual_cells": len(cells),
    "command_bits_registered": 9688,
    "maximum_internal_driven_net_loads": max(fanout[bit] for bit in driven),
    "ctl_clock_ff_loads": [clock_ff[bit] for bit in ports["clk_ctl"]["bits"]],
    "column_clock_ff_loads": [clock_ff[bit] for bit in ports["clk_cmd"]["bits"]],
    "macro_clock_roots": len(macro_clock),
    "macros_per_macro_clock_root": 1,
    "physical_qualification": False,
    "open": ["real geometry and native per-pin timing", "read mux and configuration distribution",
             "compiler startup cost and common-phase release", "full native composition"],
}
print(json.dumps(result, indent=2))
