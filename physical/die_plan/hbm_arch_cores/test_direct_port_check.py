#!/usr/bin/env python3
"""Regression (HBM i8w_front 11-10): a plan drop_face_shell_pins event narrows an unread input bus
(command[191:184] gone from the i8w8 1109 pin table).  The top == module port check defers it to the
face-shell keep check instead of failing PORT_MISMATCH; everything else still fails."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("gk", Path(__file__).with_name("gen_core_kit_hbm.py"))
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)

rtl = [("clk", "input", 1), ("command", "input", 192), ("spare", "input", 4), ("y", "output", 16)]
plan = {"clk": (1, True), "command": (184, False), "y": (16, False)}
bad, dfr = gk.direct_port_check(plan, rtl, True)
assert not bad and dfr == {"command": 184, "spare": 0}, (bad, dfr)
# face shell drop off: same tables are a mismatch
bad, dfr = gk.direct_port_check(plan, rtl, False)
assert sorted(bad) == ["command", "spare"] and not dfr, (bad, dfr)
# outputs, wider plan buses and plan-only buses never defer
bad, _ = gk.direct_port_check({"clk": (1, True), "command": (192, False), "spare": (4, False), "y": (8, False)}, rtl, True)
assert bad == ["y"], bad
bad, _ = gk.direct_port_check({"clk": (1, True), "command": (200, False), "spare": (4, False), "y": (16, False), "z": (2, False)}, rtl, True)
assert bad == ["command", "z"], bad
# exact match: nothing deferred
bad, dfr = gk.direct_port_check({"clk": (1, True), "command": (192, False), "spare": (4, False), "y": (16, False)}, rtl, True)
assert not bad and not dfr
print("ok")
