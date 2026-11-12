"""QC-S28-VISFORM 11-12 (FW-EFACE-BIN): opt-in E/W face pin-register band (budgets.face_flop_ew_types ->
OT_FF_EW_CPITCH_SITES / OT_FF_EW_ROW_STRIDE).  Unset = the 40-site pitch and +-2 rows of before, byte for byte."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys as GP
import schema as S

SRC = Path(__file__).with_name("face_flops.tcl").read_text()
tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh unavailable")


def test_gen_absent_is_empty_and_type_beats_base():
    assert GP._face_flop_ew({}, "sle_fw_v3") == []
    b = {"face_flop_ew_types": {"sle_fw": {"cpitch_sites": 80, "row_stride": 3}, "sle_fw_v3": {"cpitch_sites": 60}}}
    assert GP._face_flop_ew(b, "sle_fw_v1__cl9d029624") == ["export OT_FF_EW_CPITCH_SITES = 80",
                                                            "export OT_FF_EW_ROW_STRIDE = 3"]
    assert GP._face_flop_ew(b, "sle_fw_v3") == ["export OT_FF_EW_CPITCH_SITES = 60"]
    assert GP._face_flop_ew(b, "slw_fw_v3") == []


def test_schema_accepts_form_and_rejects_unknown_field():
    import jsonschema
    sub = S.SCHEMA["properties"]["budgets"]["properties"]["face_flop_ew_types"]
    jsonschema.validate({"sle_fw": {"cpitch_sites": 80, "row_stride": 3}}, sub)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"sle_fw": {"pitch": 80}}, sub)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"sle_fw": {"cpitch_sites": 0}}, sub)


def place(pins_y, env):
    """run the E/W branch of face_flops.tcl on E-face pins at y (dbu); -> [(col, x, y)]"""
    setup = SRC[SRC.index("set ff_ew_cpitch"):SRC.index("\n", SRC.index("set ff_ew_stride")) + 1]
    start = SRC.index("    if {$face in {E W}} {")
    end = SRC.index("    } else {", start)
    branch = SRC[start:end] + "    }\n"
    rows = " ".join("r" for _ in range(4000))
    script = ("set ff_sw 54;set ff_x0 0;set ff_x1 622080;set ff_y0 0;set ff_rh 270;set w 1080;set ff_occ {};set face E\n"
              f"set ff_rows [list {rows}]\n" + "".join(f"set ::env({k}) {v}\n" for k, v in env.items()) + setup +
              "foreach py {" + " ".join(map(str, pins_y)) + "} {\n" + branch +
              "if {!$placed} {error unplaced}\nputs \"LOC $c $cx $cy\"\n}\n")
    cp = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True)
    assert not cp.stderr, cp.stderr
    return [tuple(map(int, m)) for m in re.findall(r"LOC (\d+) (\d+) (\d+)", cp.stdout)]


# 540 pins in a 94-um window (5.75 pins/um, the sle_fw_v1 x_fe_i form)
WIN = [int(557472 + i * 94000 / 540) for i in range(540)]


@tcl
def test_unset_keeps_the_40_site_pitch_and_two_rows():
    got = place(WIN, {})
    assert len(got) == 540 and len({(x, y) for _, x, y in got}) == 540
    assert {622080 - x - 1080 for _, x, _ in got} <= {c * 2160 for c in range(10)}
    assert max(c for c, _, _ in got) >= 1


@tcl
def test_spread_form_is_deeper_sparser_and_legal():
    base = place(WIN, {})
    form = place(WIN, {"OT_FF_EW_CPITCH_SITES": 80, "OT_FF_EW_ROW_STRIDE": 3})
    assert len(form) == 540 and len({(x, y) for _, x, y in form}) == 540
    assert {622080 - x - 1080 for _, x, _ in form} <= {c * 4320 for c in range(10)}
    # the default form puts every register in column 0 (the one-cell hot column); the comb puts <= 1/3 there
    edge = lambda P: sum(1 for _, x, _ in P if x >= 622080 - 2160 - 1080)
    assert edge(base) == 540 and edge(form) <= 540 / 3 + 1
    # every register stays within +-2 rows of its pin row and in a staggered comb row of its column
    for py, (c, x, cy) in zip(WIN, form):
        col = (622080 - 1080 - x) // 4320
        assert abs(cy // 270 - py // 270) <= 2 and (cy // 270 + col) % 3 == 0
