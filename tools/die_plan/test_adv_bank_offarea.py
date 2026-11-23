"""ADV-BANK-OFFAREA (COORD 11-22): exact / bank flop sites outside CORE_AREA (outline minus the 4.32 um core inset) are WARN lines,
never a gate.  Shape of the KV kv3_pv_v3 D28 R5 case (OPUS-FIX-KV-PV-R7: 430 + 319 sites, e.g. (1063.152, 1518.48) on a 1080 x 1520.64
outline)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_bank_offarea as A  # noqa: E402
import plan_advisory as PA  # noqa: E402


def plan(sites, face=None, soft=None, margins=None):
    t = {"outline_um": [1080.0, 1520.64], "internal_stations": [{"conn": "bus:x", "regs_um": [[1, 1]], "bit_sites_um": [sites],
                                                                  "bit_site_cell_um": [1.404, 0.27]}]}
    if face:
        t["internal_stations"][0]["face_bit_sites_um"] = face
    if soft:
        t["soft_reg_banks"] = [{"id": "g0", "bit_sites_um": soft}]
    if margins:
        t["kit_core_margins_um"] = margins
    return {"partition_types": {"kv3_pv_v3": t}}


def test_off_area_sites_are_warned():
    out = A.findings(plan([[1063.152, 1518.48], [500.0, 500.0], [195.912, 1.08]]), "p.json")
    assert len(out) == 1 and out[0].startswith("WARN ADV-BANK-OFFAREA kv3_pv_v3: 2 exact / bank flop site(s) outside CORE_AREA")
    assert "internal_stations[0]" in out[0] and "(1063.15,1518.48)" in out[0]


def test_inside_sites_and_face_soft_banks():
    assert A.findings(plan([[500.0, 500.0], [4.32, 4.32]]), "p.json") == []
    out = A.findings(plan([[500.0, 500.0]], face=[[1079.0, 10.0]], soft=[[2.0, 600.0]]), "p.json")
    assert "2 exact / bank flop site(s)" in out[0] and "face bit 0" in out[0] and "soft_reg_banks[0]" in out[0]


def test_explicit_zero_margin_moves_the_area():
    assert A.findings(plan([[1.0, 1.08]], margins=[0.0, 0.0, 4.32, 4.32]), "p.json") == []


def test_registered_as_advisory_never_fails():
    assert ("BANK-OFFAREA", "adv_bank_offarea") in PA.CHECKS
    lines = PA.run(plan([[1063.152, 1518.48]]), "p.json", checks=["BANK-OFFAREA"])
    assert lines and all(x.startswith("WARN ADV-BANK-OFFAREA") for x in lines)
    assert A.findings({"partition_types": {"t": {"outline_um": "bad", "internal_stations": [{"bit_sites_um": [[[1, 1]]]}]}}}, "p")[0].startswith("WARN ADV-BANK-OFFAREA not checked")
