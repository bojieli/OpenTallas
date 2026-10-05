#!/usr/bin/env python3
"""Remove irrelevant signed wire declarations for OpenROAD's Verilog reader.

Yosys has already mapped all arithmetic to cells. At this stage Verilog wire
signedness cannot affect the netlist; OpenROAD rejects the signed declarations
for escaped/generated lane names in this mapped file.
"""
from pathlib import Path

path = Path("/tmp/qwen-o4-shard-route/mapped.v")
original = path.read_text()
assert original.count("wire signed ") == 399
path.write_text(original.replace("wire signed ", "wire "))
