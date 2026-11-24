from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))

import rom_base_narrow as rbn  # noqa: E402
import rom_seam_gate as sg  # noqa: E402
import rom_viamap_gds as vg  # noqa: E402

P = ROOT / "physical" / "asap7_memory_macros_v2"
SRC = P / "ot_rom_4096x274_m8"
DST = P / "ot_rom_4096x266_m8"


def _args(tmp_path, **kw):
    a = dict(base_gds=str(SRC / "ot_rom_4096x274_m8.base_head_driver.gds.gz"),
             src_grid=str(SRC / "ot_rom_4096x274_m8.via_grid.json"), src_lef=str(SRC / "ot_rom_4096x274_m8.lef"),
             dst_macro=str(DST / "ot_rom_4096x266_m8.json"), out_gds=str(tmp_path / "b.gds"),
             out_grid=str(tmp_path / "g.json"), src_array="head_274_array_center", dst_array="qc_266_array_center",
             src_top="ot_rom_head_driver_trial", dst_top="ot_rom_qc266_driver_trial", report=str(tmp_path / "r.json"))
    a.update(kw)
    return argparse.Namespace(**a)


def test_qc266_base_and_grid_reproduce_the_released_files(tmp_path):
    rep = rbn.derive(_args(tmp_path))
    assert rep["m4_stripes_clipped"] == 163 and rep["max_drawn_x_um"] == 121.548
    assert rep["grid_rows_cols"] == [512, 2128]
    assert all(len(v) == 16 for v in rep["edge_dummy_columns"].values())
    released = DST / "ot_rom_4096x266_m8.base_qc_driver.gds.gz"
    with gzip.open(released, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == rep["out_sha256"]
    assert json.loads((tmp_path / "g.json").read_text()) == json.loads(
        (DST / "ot_rom_4096x266_m8.via_grid.json").read_text())
    # the grid binds to the signed 266 LEF and covers every logical bit once
    m = vg.Macro(DST / "ot_rom_4096x266_m8.json", via_grid=tmp_path / "g.json")
    assert m.grid.base_gds_sha256 == rep["out_sha256"] and m.grid.seam_array_cell == "qc_266_array_center"
    assert sg.residual(tmp_path / "b.gds", "qc_266_array_center")["short_seams"] == 0


def test_every_record_except_m4_stripe_ends_is_unchanged(tmp_path):
    rbn.derive(_args(tmp_path))
    src = tmp_path / "src.gds"
    with gzip.open(SRC / "ot_rom_4096x274_m8.base_head_driver.gds.gz", "rb") as f:
        src.write_bytes(f.read())

    def recs(path, rename):
        out = []
        with path.open("rb") as f:
            for rt, dt, p in vg.read_records(f):
                if rt in (vg.STRNAME, vg.SNAME):
                    p = rename.get(p.rstrip(b"\0"), p.rstrip(b"\0"))
                out.append((rt, p.rstrip(b"\0") if rt in (vg.STRNAME, vg.SNAME) else p))
        return out
    ren = {b"head_274_array_center": b"qc_266_array_center", b"ot_rom_head_driver_trial": b"ot_rom_qc266_driver_trial"}
    a, b = recs(src, ren), recs(tmp_path / "b.gds", {})
    assert len(a) == len(b)
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    assert len(diff) == 163 and all(x[0] == vg.XY for x, _ in diff)


def test_refuses_a_wider_destination(tmp_path):
    with pytest.raises(SystemExit):
        rbn.derive(_args(tmp_path, src_lef=str(DST / "ot_rom_4096x266_m8.lef"),
                         dst_macro=str(SRC / "ot_rom_4096x274_m8.json")))
