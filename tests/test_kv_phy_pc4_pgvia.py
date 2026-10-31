"""DIE-KV-51: modeled PHY LEF leaves M6->M7 PG via openings (PDN-0006) and reproduces the checked-in KV views."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/qwen_kv_die"))
import phy_pc4_gen as g

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "physical/die_plan/qwen_kvsys/cores/phy_pc4" / g.NAME


def _parse(lef):
    pins, obs, cur, layer, in_obs = {}, {}, None, None, False
    for line in lef.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "PIN":
            cur = t[1]
        elif t[0] == "OBS":
            in_obs, cur = True, None
        elif t[0] == "LAYER":
            layer = t[1]
        elif t[0] == "RECT":
            r = tuple(map(float, t[1:5]))
            (obs.setdefault(layer, []) if in_obs else pins.setdefault(cur, {}).setdefault(layer, [])).append(r)
    return pins, obs


def _overlap(a, b, gap=0.0):
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def _check(lef_text):
    pins, obs = _parse(lef_text)
    pg = [r for n in ("VDD", "VSS") for r in pins[n]["M6"]]
    assert len(pg) == 2
    for r in pg:
        assert not any(_overlap(o, r, g.PG_VIA_CLEAR - 1e-6) for o in obs["M7"]), r
    # every other OBS layer keeps the full-body rect
    for i in range(1, 7):
        assert len(obs[f"M{i}"]) == 1
    return pins, obs


def test_m7_obs_clears_pg_pins(tmp_path):
    for faces in (g.FACES, ("E",) * 4):
        g.generate(tmp_path / "-".join(faces), 302.4, 1501.2, faces)
        _check((tmp_path / "-".join(faces) / g.NAME / f"{g.NAME}.lef").read_text())


def test_checked_in_views_regenerate(tmp_path):
    g.generate(tmp_path, 302.4, 1501.2, ("E",) * 4)
    for f in VIEWS.iterdir():
        assert (tmp_path / g.NAME / f.name).read_bytes() == f.read_bytes(), f.name
    _check((VIEWS / f"{g.NAME}.lef").read_text())


def test_old_full_m7_obs_would_fail():
    lef = (VIEWS / f"{g.NAME}.lef").read_text()
    full = re.sub(r"(  LAYER M7 ;\n)(   RECT .*\n)+", r"\1   RECT 0.4 0.4 302 1500.8 ;\n", lef)
    try:
        _check(full)
    except AssertionError:
        return
    raise AssertionError("full-body M7 OBS must be caught")
