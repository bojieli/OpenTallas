"""KIT-CHAN-1 (DIE-QC-97 11-11) identity: plans with the existing leg orders (normal_first default, along_first, with
and without start_core starts) give byte-equal kit outputs (istations.tcl, the edited bound RTL and the kit_istations
report) to main before the channel order (cd5748bb222), plus byte-equal taps.per_bit_station_sites.  GOLDEN was
measured on cd5748bb222 with this same file."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_kit_istations_core_pin as F   # noqa: E402  (fixtures: plan, run, lplan, lrun)

GOLDEN = json.loads('{"kit": {"along_all": {"rep": "06f3b4158feec86f", "rtl": "670a74ed1e7f6638", "tcl": "30be0e4ab368ac0d"}, "along_some": {"rep": "06f3b4158feec86f", "rtl": "670a74ed1e7f6638", "tcl": "b268bce649abd292"}, "normal": {"rep": "06f3b4158feec86f", "rtl": "670a74ed1e7f6638", "tcl": "5485327033045574"}, "start_along": {"rep": "65b61b210531356f", "rtl": "658ecf79365751d1", "tcl": "c96a0b5351964a4b"}, "start_normal": {"rep": "65b61b210531356f", "rtl": "658ecf79365751d1", "tcl": "7493e7ae2e3b8a81"}}, "taps": {"along_all": "4f67ac81dda8d86d", "along_some": "51f0c0fc8965da72", "normal": "fb23b2faa1f930e8", "start_along": "362613a23e847c26", "start_normal": "387284cb2f817dcd"}}')


def _h(b):
    return hashlib.sha256(b).hexdigest()[:16]


def _kit(kd, bf):
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    return dict(tcl=_h((kd / "istations.tcl").read_bytes()), rtl=_h(bf.read_bytes()),
                rep=_h(json.dumps(rep, sort_keys=True).encode()))


def _along(p, which):
    for i, e in enumerate(p["partition_types"]["t"]["internal_stations"]):
        if i in which:
            e["leg_order"] = "along_first"
    return p


def _run_plan(tmp_path, p, bound, pins=None):
    if pins is not None:
        (tmp_path / "LM_pins.json").write_text(json.dumps(dict(pins=pins)))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(p))
    kd = tmp_path / "kit"
    kd.mkdir()
    bf = kd / "t_part_bound.sv"
    bf.write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(bf)])))
    import subprocess
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    return _kit(kd, bf)


def cases():
    lp, lpins = F.lplan()
    lpa, _ = F.lplan()
    lpa["partition_types"]["t"]["internal_stations"][0]["leg_order"] = "along_first"
    return {
        "normal": (F.plan(), F.BOUND, None),
        "along_some": (_along(F.plan(), {0, 3, 5}), F.BOUND, None),
        "along_all": (_along(F.plan(), set(range(6))), F.BOUND, None),
        "start_normal": (lp, F.LBOUND, lpins),
        "start_along": (lpa, F.LBOUND, lpins),
    }


def taps_digest():
    import taps
    out = {}
    for nm, (p, _b, _pins) in cases().items():
        t = p["partition_types"]["t"]
        if nm.startswith("start"):
            pins = [("z", b, "M4", 100.0, 30.0 + b, "E") for b in range(4)]
        else:
            pins = [("x", b, "M4", 0.0, 10.0 + b, "W") for b in range(5)] + \
                [("f", b, "M4", 0.0, 30.0 + b, "W") for b in range(2)] + [("y", b, "M5", 10.0 + b, 100.0, "N") for b in range(4)]
        s = taps.per_bit_station_sites(t, pins)
        out[nm] = _h(json.dumps([[round(x, 6), round(y, 6), k] for x, y, k in s]).encode())
    return out


@pytest.mark.parametrize("name", sorted(cases()))
def test_existing_leg_orders_kit_byte_equal(tmp_path, name):
    p, bound, pins = cases()[name]
    got = _run_plan(tmp_path, p, bound, pins)
    assert got == GOLDEN["kit"][name], (name, got)


def test_existing_leg_orders_taps_equal():
    assert taps_digest() == GOLDEN["taps"]


if __name__ == "__main__":       # print the golden digests (run on the base commit)
    import tempfile
    kit = {}
    for nm, (p, bound, pins) in cases().items():
        with tempfile.TemporaryDirectory() as d:
            kit[nm] = _run_plan(Path(d), p, bound, pins)
    print(json.dumps(dict(kit=kit, taps=taps_digest()), indent=1, sort_keys=True))
