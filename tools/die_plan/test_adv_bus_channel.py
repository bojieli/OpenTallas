"""ADV-BUS-CHANNEL-FIT: sle_fe_v2-like E strip (13 per-bit E-face buses, 311 um strip) fires; grown to the needed width it passes."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_bus_channel as A  # noqa: E402
import plan_advisory as PA  # noqa: E402

# (name, dir, bits, pin y) of the sle_fe_v2 E-face buses (plan C1o v13), leaf at the core centre (311.04, 915.84)
E_BUSES = [("cmd_wo", "out", 116, 161.224), ("dr_wo", "out", 520, 365.008), ("hr_wo", "out", 453, 486.096),
           ("rd_wo", "out", 512, 605.248), ("sc_wo", "out", 48, 695.384), ("st_wo", "out", 1088, 1087.064),
           ("ag_wi", "in", 10, 5.24), ("ard_wi", "in", 512, 68.752), ("art_wi", "in", 32, 137.376),
           ("dd_wi", "in", 548, 245.712), ("sc_wi", "in", 48, 677.608), ("treq_wo", "out", 9, 1217.432),
           ("st_wi", "in", 1088, 828.984)]


def _type(extra=0.0):
    W = 622.08 + extra
    buses, st = [], []
    for n, d, bits, y in E_BUSES:
        buses.append({"name": n, "dir": d, "width": bits, "face": "E"})
        pin, leaf = [W, y], [311.04, 915.84]
        e = {"conn": "bus:" + n, "bits": bits, "bit_route": "per_bit", "leaf_um": leaf, "regs_um": [[1, 1]]}
        e["from_um" if d == "in" else "to_um"] = pin
        e["to_um" if d == "in" else "from_um"] = leaf
        st.append(e)
    return {"outline_um": [W, 1831.68], "buses": buses, "internal_stations": st}


def test_narrow_strip_fires():
    out = A.findings({"partition_types": {"sle_fe_v2": _type()}})
    assert len(out) == 1 and out[0].startswith("WARN ADV-BUS-CHANNEL-FIT sle_fe_v2: E side strip 311 um")
    assert "ard_wi" in out[0]


def test_grown_strip_passes():
    need = A.side_fit(_type(), "E")["need"]
    assert 311 < need < 600
    assert A.findings({"partition_types": {"sle_fe_v2": _type(need - 311.04)}}) == []


def test_mutant_one_um_short_fires():
    need = A.side_fit(_type(), "E")["need"]
    assert A.findings({"partition_types": {"sle_fe_v2": _type(need - 311.04 - 3)}})


def test_bad_rows_never_raise():
    t = copy.deepcopy(_type())
    t["internal_stations"][0]["leaf_um"] = "x"
    out = A.findings({"partition_types": {"bad": t, "empty": {"outline_um": [1, 1]}}})
    assert all(x.startswith("WARN ADV-BUS-CHANNEL-FIT") for x in out)


def test_registered():
    assert ("BUS-CHANNEL-FIT", "adv_bus_channel") in PA.CHECKS
