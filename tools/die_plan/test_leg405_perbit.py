"""tests of leg405_perbit.py and the per-bit part of ADV-LEG405-STAGED (C-LEG405-R3)."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as F  # noqa: E402
import die_hop_scan as D  # noqa: E402
import ft_full_stage  # noqa: E402
import leg405_perbit as LB  # noqa: E402


def fake(monkeypatch, slot, pins):
    P = types.SimpleNamespace(types={"T": {"ft_slots": [slot]}})
    monkeypatch.setattr(D, "pin_table", lambda P_, tn: pins)
    monkeypatch.setattr(D, "normal_slot", lambda *a, **k: True)
    monkeypatch.setattr(ft_full_stage, "load", lambda P_, tn: {})
    return P


def slot(k, **kw):
    s = {"name": "s", "stations": k, "bit_site_cell_um": [1.0, 0.27]}
    s.update(kw)
    return s


def test_first_hop_starts_at_the_pin_not_the_first_station(monkeypatch):
    # explicit station 0 seated 500 um from its input pin: the station -> station hops are short (what OT_FT_LANE and the row model see),
    # the first hop from the true source is not
    pins = {"s_i": {0: (0.0, 0.0, "W")}, "s_o": {0: (900.0, 0.0, "E")}}
    P = fake(monkeypatch, slot(2, explicit_stage0=True, bit_sites_um=[[[500.0, 0.0]], [[600.0, 0.0]]]), pins)
    c = LB.type_census(P, "T")["s"]
    assert c["ss_max"] < 120 and c["first_max"] > 495 and c["full_over"] == 1
    assert LB.type_flag({"s": c}, drift=3.0)[0] == 1


def test_drift_margin_changes_the_verdict(monkeypatch):
    pins = {"s_i": {0: (0.0, 0.0, "W")}, "s_o": {0: (404.0, 0.0, "E")}}
    P = fake(monkeypatch, slot(1, regs_um=[[0, 0]]), pins)
    c = LB.type_census(P, "T")["s"]
    assert c["full_max"] == 403.0 or c["full_max"] == 404.0
    assert LB.type_flag({"s": c}, drift=0.0)[0] == 0
    assert LB.type_flag({"s": dict(c, full_max=402.7)}, drift=3.0)[0] == 1
    assert LB.type_flag({"s": dict(c, full_max=401.9)}, drift=3.0)[0] == 0


def test_regs_only_slot_keeps_each_bits_own_lane(monkeypatch):
    # in pins spread over y 0..300 (centroid 150); out pins all at y=150: the kit lane keeps bit 0 at its own pin y, station 1 moves toward
    # the out pin by t = 1/2, so bit 0 -> station 1 is NOT the centre-line hop
    pins = {"s_i": {0: (0.0, 0.0, "W"), 1: (0.0, 300.0, "W")}, "s_o": {0: (800.0, 150.0, "E"), 1: (800.0, 150.0, "E")}}
    P = fake(monkeypatch, slot(2, regs_um=[[0, 150], [400, 150]]), pins)
    ch = LB.slot_chains(P, "T", P.types["T"]["ft_slots"][0], pins, True, {})
    assert ch[0][2][1] == 150 + 0.5 * (0 - 150) + 0.5 * (150 - 150)      # y of station 1, bit 0 = 75
    assert ch[1][2][1] == 150 + 0.5 * (300 - 150)                         # 225
    assert ch[0][0] != ch[0][2]


def test_placed_reader_matches_ot_ft_lane(tmp_path):
    f = tmp_path / "ot_face_flops.txt"
    f.write_text("a\tst1\t0\t0\tp0\na\tst2\t300\t100\tp0\na\tst3\t300\t600\tp0\nb\tst1\t0\t0\tp1\nb\tst2\t100\t0\tp1\nx\thl\t1\t1\t-\n")
    r = LB.placed_hops(str(f))
    assert r["bits"] == 2 and r["max_um"] == 500.0 and r["n_over"] == 1 and r["worst"][0] == ("p0", 500.0)


def test_check_adds_per_bit_types_and_keeps_relay_rows(monkeypatch, tmp_path):
    raw = {"partition_types": {"A": {"relay_depth": [{"inst": "u", "port": "o", "path_um": 898.5, "stages_existing": 0, "D": 1}], "ft_slots": [{}]},
                               "B": {"ft_slots": [{}]}}}
    plan = tmp_path / "p.json"
    plan.write_text("{}")
    monkeypatch.setattr(F, "leg405_perbit_types", lambda raw_, pp, budget_s=None: ({"B": (1, 1, 431.0, [("s", 431.0, 12.0, 3)])}, ""))
    out = F.findings_by_check["LEG405-STAGED"](raw, str(plan))
    txt = "\n".join(out)
    assert "ADV-LEG405-STAGED A 1 finding" in txt and "ADV-LEG405-STAGED B per-bit chain from the pin: 1 slot(s) over 405" in txt
    assert out[-1].startswith("WARN ADV-LEG405-STAGED summary 2 types flagged (1 relay_depth / cland rows, 1 per-bit chain, 0 both")


def test_near_types_are_listed_not_counted(monkeypatch, tmp_path):
    plan = tmp_path / "p.json"
    plan.write_text("{}")
    monkeypatch.setattr(F, "leg405_perbit_types", lambda raw_, pp, budget_s=None: ({"C": (0, 1, 398.0, [])}, ""))
    out = F.findings_by_check["LEG405-STAGED"]({"partition_types": {"C": {}}}, str(plan))
    assert any("near: 1 slot(s)" in x for x in out) and "summary 0 types flagged" in out[-1]
