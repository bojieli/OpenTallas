import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prebuild_gate as PG  # noqa: E402
import census_table as CT  # noqa: E402

LOG = """GATE cells 1200 macros 2 stdcell_area_um2 345.6 stage place_resized
GATE period 833.0
GATE group r2r slack 120.5 start a/CLK end b/D
GATE group in2reg slack 90.0 start x end c/D
GATE group reg2out none
GATE group in2out none
GATE r2r_endpoints_stage_over_583 3
GATE_WORST_BEGIN
path
GATE_WORST_END
"""


def test_sta_numbers():
    s = PG.sta_numbers(LOG)
    assert s["cells"] == 1200 and s["macros"] == 2 and s["sta_stage"] == "place_resized"
    assert s["wns"] == 90.0 and s["groups"]["reg2out"] is None and s["r2r_endpoints_stage_over_583"] == 3
    assert s["worst_path"].strip() == "path"


def test_cfg_vars_override_last_wins():
    v = PG.cfg_vars("export A = 1\noverride export A = 2\nexport SYNTH_MEMORY_MAX_BITS = 16384\n")
    assert v["A"] == "2" and v["SYNTH_MEMORY_MAX_BITS"] == "16384"


def test_memories_over(tmp_path):
    f = tmp_path / "mem.json"
    f.write_text(json.dumps({"modules": {"m": {"memories": {"r": {"width": 64, "size": 512}, "s": {"width": 8, "size": 4}}}}}))
    m = PG.memories(f, 16384)
    assert {x["memory"]: x["over"] for x in m} == {"r": True, "s": False}
    assert PG.memories(tmp_path / "none.json", 1) == []


def test_census_row_flags():
    d = {"schema": "opentallas.prebuild_gate.v1", "verdict": "FAIL", "sta_stage": "place_resized", "cells": 10,
         "wns": -300.0, "stage_ps": 1133.0, "needs_stage_cut": True, "groups": {"r2r": {"slack": -300.0}},
         "checks": {"cells": {"ok": True}, "memory": {"ok": True, "largest": 0}, "face": {"pin_unreg": 63},
                    "reset": {"ok": True}, "straps": {"leaked": []}}}
    r = CT.row("x", d)
    assert r["needs"] == "STAGE_CUT+FACE_REG" and r["pin_unreg"] == 63
    assert CT.row("y", {})["verdict"] == "RUNNING"
