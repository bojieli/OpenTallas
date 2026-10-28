"""QK-CORES-11: macro_sites mirrored-view image + pins_view_image (GEOM-REVIEW-37 fMX FAIL STRUCTURAL)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import macro_sites as MS  # noqa: E402
import pins_view_image as PVI  # noqa: E402

MW, MH = 51.408, 20.79
SITES = json.loads((HERE / "kv3_pv_pair.json").read_text())
CFG = """export DIE_AREA = 0 0 380.16 190.08
export CORE_AREA = 4.32 4.32 375.84 185.76
export MACRO_PLACE_HALO = 4.32 4.32
"""
R0_RECTS = [[268.11, 43.2, 269.73, 43.47], [107.46, 138.24, 110.7, 138.51]]


def kit(tmp, name, rects, ftype=None):
    kd = tmp / name
    (kd / "macros").mkdir(parents=True)
    (kd / "macros" / "ot_sram_1r1w_32x128_m1.lef").write_text(f"MACRO ot_sram_1r1w_32x128_m1\n  SIZE {MW} BY {MH} ;\nEND\n")
    (kd / "config.mk").write_text(CFG)
    (kd / "island_ft.json").write_text(json.dumps(dict(arcs=[dict(source=f"ft_ck_i_{k}", rect_um=r)
                                                            for k, r in enumerate(rects)])))
    if ftype:
        (kd / "freeze.json").write_text(json.dumps(dict(type=ftype)))
    return kd


def sites_of(kd):
    t = (kd / "macro_place.tcl").read_text()
    return t, [s.split() for s in t.split("foreach {master sites} {")[1].split("} {\n")[0].split("{")[2:]]


def test_r0_identity(tmp_path):
    kd = kit(tmp_path, "kv3_pv_pair__380.16x190.08", R0_RECTS, "kv3_pv_pair__380.16x190.08")
    MS.apply(HERE / "kv3_pv_pair.json", kd)
    t, s = sites_of(kd)
    assert "view image" not in t
    want = [[f"{x:g}", f"{y:g}", o + "}" if i < 7 else o + "}}"] for i, (x, y, o) in
            enumerate(SITES["sites"]["ot_sram_1r1w_32x128_m1"])]
    assert [[a, b, c.rstrip("}")] for a, b, c in s] == [[a, b, c.rstrip("}")] for a, b, c in want]
    assert "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl" in (kd / "config.mk").read_text()


def test_fmx_image(tmp_path):
    img = [[r[0], round(190.08 - r[3], 4), r[2], round(190.08 - r[1], 4)] for r in R0_RECTS]
    kd = kit(tmp_path, "kv3_pv_pair__380.16x190.08_fMX", img, "kv3_pv_pair__380.16x190.08_fMX")
    assert MS.kit_view(kd) == "MX"
    boxes = MS.apply(HERE / "kv3_pv_pair.json", kd)
    t, s = sites_of(kd)
    assert "# view image: MX" in t
    got = [(float(a), float(b), c.rstrip("}")) for a, b, c in s]
    flip = {"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"}
    for (x, y, o), (gx, gy, go) in zip(SITES["sites"]["ot_sram_1r1w_32x128_m1"], got):
        assert gx == pytest.approx(x) and gy == pytest.approx(190.08 - y - MH, abs=1e-4) and go == flip[o]
    # the S-face pair (R0 y 4.35) moves to the N edge, the W stack to y 61.134 / 92.94
    assert sorted({round(b[2], 3) for b in boxes}) == [26.43, 61.134, 92.94, 164.94]


def test_fmx_fails_closed_on_unimaged_island(tmp_path):
    kd = kit(tmp_path, "kv3_pv_pair__380.16x190.08_fMX", R0_RECTS, "kv3_pv_pair__380.16x190.08_fMX")
    with pytest.raises(SystemExit, match="ft_ck_i_0.*inside macro"):
        MS.apply(HERE / "kv3_pv_pair.json", kd)


def test_image_site_my_r180():
    assert MS.image_site(10, 20, "R0", 5, 6, 100, 50, "MY") == (85, 20, "MY")
    assert MS.image_site(10, 20, "MX", 5, 6, 100, 50, "R180") == (85, 24, "MY")
    assert MS.image_site(10, 20, "MY", 5, 6, 100, 50, "R0") == (10, 20, "MY")


def test_kit_view_dirname(tmp_path):
    assert MS.kit_view(tmp_path / "x__1x1_fR180") == "R180"
    assert MS.kit_view(tmp_path / "x__1x1") == "R0"


def view(ft, rects, extra_y=0.096):
    pins = [dict(name="s0__bc[0]", layer="M5", x=2.28, y=extra_y)]
    pins += [dict(name=n, layer="M5", x=x, y=y) for n, (x, y) in ft.items()]
    return dict(frame="core R0, origin (0,0), outline 380.16 x 190.08", source="t", pins=pins,
                island_ft=dict(arcs=[dict(source=f"ft_ck_i_{k}", sink=f"ft_ck_o_{k}", rect_um=r) for k, r in enumerate(rects)]))


def test_pins_view_image():
    ft = {"ft_ck_i_0": (267.0, 43.335), "ft_ck_o_0": (270.84, 43.335)}
    r0 = view(ft, R0_RECTS[:1])
    mir = view(ft, R0_RECTS[:1], extra_y=189.984)       # data pins already MX-imaged, ft copied un-imaged
    o = PVI.image(r0, mir, "MX")
    p = {q["name"]: q for q in o["pins"]}
    assert (p["ft_ck_i_0"]["x"], p["ft_ck_i_0"]["y"]) == (267.0, 146.745)
    assert p["s0__bc[0]"]["y"] == 189.984
    assert o["island_ft"]["arcs"][0]["rect_um"] == [268.11, 146.61, 269.73, 146.88]
    # row grid of gen_core_kit_kv.island_ft_arcs: (y0 - 4.32) / 0.27 integral
    assert abs((146.61 - 4.32) / 0.27 - round((146.61 - 4.32) / 0.27)) < 1e-6


def test_pins_view_image_refuses_mismatch():
    r0 = view({"ft_ck_i_0": (1, 2)}, R0_RECTS[:1])
    mir = view({"ft_ck_i_1": (1, 2)}, R0_RECTS[:1])
    with pytest.raises(SystemExit, match="ft pins differ"):
        PVI.image(r0, mir)
