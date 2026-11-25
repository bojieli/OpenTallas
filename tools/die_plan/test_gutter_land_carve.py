"""GUTTER-LAND-CARVE 11-24 (FAIL-CLASS f5fa4d600f): gutter_block.tcl cuts every landing window out of its gutter rects."""
import pathlib, shutil, subprocess
import pytest

SRC = pathlib.Path(__file__).with_name("gutter_block.tcl")
TCLSH = shutil.which("tclsh")


def _procs():
    s = SRC.read_text()
    i = s.index("proc gb_carve")
    return s[i:s.index("uplevel #0 {")]


def _run(tmp_path, body):
    f = tmp_path / "t.tcl"
    f.write_text(_procs() + body)
    return subprocess.run([TCLSH, str(f)], capture_output=True, text=True, check=True).stdout.split("\n")


@pytest.mark.skipif(TCLSH is None, reason="tclsh")
def test_window_inside_gutter_is_cut_out(tmp_path):
    # kv3_pc cl254 gutter 958.656..993.216 x 1006.56..1274.4 (DBU 1000) and reader-start i_embgw_est_5 984.96..989.28 x 1160.066..1164.386
    out = _run(tmp_path, "foreach r [gb_carve {958656 1006560 993216 1274400} {{984960 1160066 989280 1164386}}] { puts $r }\n")
    rects = [tuple(map(int, l.split())) for l in out if l.strip()]
    area = sum((c - a) * (d - b) for a, b, c, d in rects)
    assert area == 34560 * 267840 - 4320 * 4320
    w = (984960, 1160066, 989280, 1164386)
    assert not any(a < w[2] and w[0] < c and b < w[3] and w[1] < d for a, b, c, d in rects)


@pytest.mark.skipif(TCLSH is None, reason="tclsh")
def test_no_window_keeps_one_rect(tmp_path):
    out = _run(tmp_path, "puts [gb_carve {0 0 100 100} {}]\n")
    assert out[0] == "{0 0 100 100}"


@pytest.mark.skipif(TCLSH is None, reason="tclsh")
def test_land_windows_parse(tmp_path):
    body = ('set t "x\\nset cland_groups \\{\\n  {u_cland_a {1.0 2.0 3.5 4.25} reader-start:a}\\n  {u_cland_b {10 20 30 40} ring:b}\\n\\}\\nrest"\n'
            "foreach r [gb_land_windows $t 1000] { puts $r }\n")
    out = [l for l in _run(tmp_path, body) if l.strip()]
    assert out == ["1000 2000 3500 4250", "10000 20000 30000 40000"]
