"""QC-PHYSERDES: the regenerated QC PHY abstracts put every FDI pin ON its S4P plan pin site (offset 0 um) for
phy_serdes, phy_serdes_b (E face, renamed macro) and phy_ucie_kv; the 1017/kv views do not (the defect)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "qwen_missing"))
import phy_plan_pins as P  # noqa: E402

TYPES = json.loads((ROOT / "tests" / "qc_phy_s4p_types.json").read_text())


def _gen(tmp_path):
    return P.generate(ROOT / "tests" / "qc_phy_s4p_types.json", tmp_path)


def test_new_views_offset_zero(tmp_path):
    res = _gen(tmp_path)
    for t, r in res.items():
        d = Path(r["dir"])
        lef = (d / f"{d.name}.lef").read_text()
        for bus, o in P.offsets(TYPES["types"][t], lef).items():
            if o["of"] and bus != "phy_rst_i":
                assert o["pins"] == o["of"], (t, bus, o)
                assert o["max_offset_um"] == 0.0 and o["wrong_layer"] == 0 and o["outside_window"] == 0, (t, bus, o)


def test_old_views_do_not_match():
    worst = {}
    for t, sp in P.SPEC.items():
        lef = (ROOT / sp["src"] / f"{sp['name']}.lef").read_text()
        offs = [o["max_offset_um"] for o in P.offsets(TYPES["types"][t], lef).values() if o["pins"]]
        worst[t] = max(offs)
    assert worst["phy_serdes"] > 100 and worst["phy_ucie_kv"] > 100 and worst["phy_serdes_b"] > 1000, worst


def test_lef_geometry_and_libs_unchanged(tmp_path):
    res = _gen(tmp_path)
    for t, sp in P.SPEC.items():
        d = Path(res[t]["dir"])
        lef = (d / f"{d.name}.lef").read_text()
        w, h = map(float, re.search(r"SIZE (\S+) BY (\S+) ;", lef).groups())
        seen = set()
        for name, b in re.findall(r"  PIN (\S+)\n(.*?)  END \1\n", lef, re.S):
            if name in ("VDD", "VSS"):
                continue
            ln = re.search(r"LAYER (\S+) ;", b).group(1)
            x0, y0, x1, y1 = map(float, re.search(r"RECT (\S+) (\S+) (\S+) (\S+) ;", b).groups())
            assert 0 <= x0 < x1 <= w + 1e-9 and 0 <= y0 < y1 <= h + 1e-9, name
            edge = (y1 == h) if res[t]["face"] == "N" else (x1 == w)
            assert edge, name
            key = (ln, round((x0 + x1) / 2, 4) if res[t]["face"] == "N" else round((y0 + y1) / 2, 4))
            assert key not in seen, (t, name, key)
            seen.add(key)
        # LIB = the old LIB with the cell name replaced
        src = ROOT / sp["src"]
        for c in ("tt", "ff", "ss"):
            old = (src / f"{sp['name']}_{c}.lib").read_text().replace(sp["name"], sp["new"])
            assert (d / f"{sp['new']}_{c}.lib").read_text() == old


def test_pin_names_equal_old_view():
    for t, sp in P.SPEC.items():
        old = P.parse_lef((ROOT / sp["src"] / f"{sp['name']}.lef").read_text())[1]
        assert len(old) >= 1171 or t != "phy_ucie_kv"


def test_serdes_b_is_east_variant(tmp_path):
    res = _gen(tmp_path)
    assert res["phy_serdes_b"]["face"] == "E" and res["phy_serdes"]["face"] == "N"
    assert res["phy_serdes_b"]["dir"].endswith("_s597_e")
    assert res["phy_ucie_kv"]["plan_only_pins"] == ["phy_rst_i"]
