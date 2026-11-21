"""Re-pin a column from its class windows without changing lane identity or slot depths."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import class_window_solve as C  # noqa: E402


def test_repin_propagates_across_repeated_type():
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    types = raw["partition_types"]
    layers = ["M6", "M4"]
    original = [400, 420]
    target = [420, 440]
    C.set_type_end(types["src"], "x_o", "E", target, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_i", "W", original, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_o", "E", original, layers, "lsb_low")
    C.set_type_end(types["sink"], "x_i", "W", original, layers, "lsb_low")
    depths = [s["stations"] for s in types["mid"]["ft_slots"]]

    report = C.solve(raw, ["src"])

    assert report["mismatches_before"] == 1
    assert report["mismatches_after"] == 0
    assert report["conflicts"] == report["overlaps"] == []
    assert [(d["type"], d["bus"]) for d in report["moved"]] == [("mid", "fx_i"), ("mid", "fx_o"), ("sink", "x_i")]
    assert [p["window_um"] for p in raw["ports"] if p["id"] in {"x0", "x1", "x2"}] == [target] * 3
    assert [s["stations"] for s in types["mid"]["ft_slots"]] == depths


def test_repin_clears_stale_ft_end_override():
    slot = dict(name="ft", layers=["M6", "M4"], in_layers=["M6"], order="lsb_low", in_order="lsb_high")
    row = {"ft_slots": [slot]}

    C.set_type_end(row, "ft_i", "W", [2.0, 8.0], ["M6", "M4"], "lsb_low")

    assert "in_layers" not in slot and "in_order" not in slot
    assert slot["in_window_um"] == [2.0, 8.0]


def _column(target, original):
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    types = raw["partition_types"]
    layers = ["M6", "M4"]
    C.set_type_end(types["src"], "x_o", "E", target, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_i", "W", original, layers, "lsb_low")
    C.set_type_end(types["mid"], "fx_o", "E", original, layers, "lsb_low")
    C.set_type_end(types["sink"], "x_i", "W", original, layers, "lsb_low")
    return raw


def test_two_anchors_conflict_without_column_mode():
    raw = _column([420, 440], [400, 420])
    report = C.solve(raw, ["src", "mid"])
    assert report["conflicts"] and all(m["type"] != "mid" for m in report["moved"])


def test_column_mode_weaker_anchor_takes_stronger_window_and_propagates():
    """UNIFY-TOOLS whole column: src and mid are both class rows; src is stronger, so mid's ends move to src's window
    and the move propagates on to sink in the same pass; no conflict."""
    target = [420, 440]
    raw = _column(target, [400, 420])
    report = C.solve(raw, ["src", "mid"], column=True)
    assert report["conflicts"] == [] and report["overlaps"] == []
    assert [(d["type"], d["bus"]) for d in report["moved"]] == [("mid", "fx_i"), ("mid", "fx_o"), ("sink", "x_i")]
    assert report["mismatches_after"] == 0
    assert [p["window_um"] for p in raw["ports"] if p["id"] in {"x0", "x1", "x2"}] == [target] * 3


def test_column_mode_order_decides_the_winner():
    raw = _column([420, 440], [400, 420])
    report = C.solve(raw, ["mid", "src"], column=True)
    assert ("src", "x_o") in [(d["type"], d["bus"]) for d in report["moved"]]
    assert report["conflicts"] == [] and report["mismatches_after"] == 0


# ---- S81-LEAF-CLASS-1730: joint class floorplan
def _bus(name, d, face, win):
    return dict(name=name, dir=d, width=4, kind="data", face=face, window_um=list(win), layers=["M7", "M5"])


def _ft(name, fi, fo, wi, wo):
    return dict(name=name, width=4, in_face=fi, out_face=fo, in_window_um=list(wi), out_window_um=list(wo),
                layers=["M7", "M5"], order="lsb_low", stations=2, regs_um=[[0, 0], [0, 0]])


def _shift_column(orient_l1="R0"):
    """C (source) under L0 (class member m1: own dn + one pass slot) under L1 (class member m2: own dn only).
    The lane to L1 passes L0's slot: L0.ft0_o (N) abuts L1.own (S), so the class needs the shift form."""
    T = {"src": dict(outline_um=[100.0, 100.0], buses=[_bus("o0", "out", "N", (10, 20)), _bus("o1", "out", "N", (60, 70))]),
         "m1": dict(outline_um=[100.0, 100.0], buses=[_bus("dn", "in", "S", (60, 70))],
                    ft_slots=[_ft("ft0", "S", "N", (10, 20), (10, 20))]),
         "m2": dict(outline_um=[100.0, 100.0], buses=[_bus("dn", "in", "S", (40, 50))], ft_slots=[])}
    parts = [dict(name="C", type="src", origin_um=[0.0, 0.0]), dict(name="L0", type="m1", origin_um=[0.0, 100.0]),
             dict(name="L1", type="m2", origin_um=[0.0, 200.0], orient=orient_l1)]
    ports = [dict(id="a", src=dict(part="C", bus="o0"), dst=dict(part="L0", bus="ft0_i"), width=4),
             dict(id="b", src=dict(part="L0", bus="ft0_o"), dst=dict(part="L1", bus="dn"), width=4),
             dict(id="c", src=dict(part="C", bus="o1"), dst=dict(part="L0", bus="dn"), width=4)]
    return dict(partition_types=T, partitions=parts, ports=ports)


def _die(raw, part, bus):
    P = {p["name"]: p for p in raw["partitions"]}[part]
    t = raw["partition_types"][P["type"]]
    for b in t["buses"]:
        if b["name"] == bus:
            face, win = b["face"], b["window_um"]
    for s in t.get("ft_slots", []):
        for e, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            if s["name"] + e == bus:
                face, win = s[fk], s[wk]
    o = P.get("orient", "R0")
    a, b = win
    if face in "NS" and o in ("MY", "R180"):
        a, b = 100.0 - b, 100.0 - a
    return C.oface(face, o), [round(P["origin_um"][0] + a, 6), round(P["origin_um"][0] + b, 6)]


def test_class_floorplan_shift_form_joins_class_ports_without_overlap():
    raw = _shift_column()
    rep = C.class_floorplan(raw, [("cls", "m1", [("m1", "R0"), ("m2", "R0")])])
    T = raw["partition_types"]
    assert rep["class_class_ports"] == 1
    assert T["m1"]["buses"] == T["m2"]["buses"]                      # one own window for the class
    (fo, wo), (fi, wi) = _die(raw, "L0", "ft0_o"), _die(raw, "L1", "dn")
    assert fo == "N" and fi == "S" and wo == wi                       # the class-class port meets on one window
    s_face = sorted([T["m1"]["buses"][0]["window_um"], T["m1"]["ft_slots"][0]["in_window_um"]])
    assert s_face[0][1] + 1.2 <= s_face[1][0] + 1e-6                 # no overlap on the S face
    assert T["m1"]["ft_slots"][0]["name"] == "ft0"                    # member slot names kept (class_merge renames)


def test_class_floorplan_mirrored_instance_takes_the_mirror_order():
    raw = _shift_column(orient_l1="MY")
    C.class_floorplan(raw, [("cls", "m1", [("m1", "R0"), ("m2", "R0")])])
    assert _die(raw, "L0", "ft0_o")[1] == _die(raw, "L1", "dn")[1]
    T = raw["partition_types"]
    assert T["m1"]["ft_slots"][0].get("out_order", T["m1"]["ft_slots"][0]["order"]) != T["m1"]["buses"][0]["order"]


def test_class_floorplan_refuses_different_own_buses():
    raw = _shift_column()
    raw["partition_types"]["m2"]["buses"][0]["width"] = 5
    try:
        C.class_floorplan(raw, [("cls", "m1", [("m1", "R0"), ("m2", "R0")])])
    except ValueError as e:
        assert "own buses" in str(e)
    else:
        raise AssertionError("expected a refusal")


def test_exact_classes_split_on_face_capacity():
    raw = _shift_column()
    T = raw["partition_types"]
    T["m2"]["ft_slots"] = [_ft("ft0", "S", "N", (10, 20), (10, 20))]
    T["m2"]["ft_slots"][0]["width"] = 300                             # a 300-bit lane only m2 carries
    subs = C.exact_classes(raw, [("m1", "R0"), ("m2", "R0")], face_cap_pins_um=3.6, bit_cap=4500)
    assert len(subs) == 1
    subs = C.exact_classes(raw, [("m1", "R0"), ("m2", "R0")], face_cap_pins_um=3.6, bit_cap=200)
    assert sorted(len(s) for s in subs) == [1, 1]


def test_cli_classes_mode(tmp_path):
    raw = _shift_column()
    tiny = json.loads((HERE / "examples/tiny_plan.json").read_text())
    raw.update({k: v for k, v in tiny.items() if k not in raw})
    (tmp_path / "p.json").write_text(json.dumps(raw))
    (tmp_path / "c.json").write_text(json.dumps([dict(cls="cls", rep="m1", members=[["m1", "R0"], ["m2", "R0"]])]))
    rc = C.main([str(tmp_path / "p.json"), "--classes", str(tmp_path / "c.json"), "--out", str(tmp_path / "o.json"),
                 "--report", str(tmp_path / "r.json")])
    out = json.loads((tmp_path / "o.json").read_text())
    assert out["partition_types"]["m1"]["buses"] == out["partition_types"]["m2"]["buses"]
    assert json.loads((tmp_path / "r.json").read_text())["class_floorplan"]["class_class_ports"] == 1
    assert rc in (0, 1)


def test_class_floorplan_drops_stale_bit_sites():
    """the class window moves the slot: bit_sites_um and bit_site_cell_um go together (schema: cell needs sites)"""
    raw = _shift_column()
    s = raw["partition_types"]["m1"]["ft_slots"][0]
    s["bit_sites_um"] = [[1.0, 1.0]] * 4
    s["bit_site_cell_um"] = [0.4, 0.4]
    C.class_floorplan(raw, [("cls", "m1", [("m1", "R0"), ("m2", "R0")])])
    s = raw["partition_types"]["m1"]["ft_slots"][0]
    assert "bit_sites_um" not in s and "bit_site_cell_um" not in s


def _mirror_pair(lo, hi, width=5):
    """class type m (S bus x) on an R0 and an MY copy; each fed by its own source type through a port that carries
    die-frame geometry (the S81 class shape that showed the 0.064 um M7 offset).  Outline on the 8.64 um lattice."""
    W, X2 = 172.8, 345.6
    raw = json.loads((HERE / "examples/tiny_plan.json").read_text())
    def bus(name, d, face, win, **k):
        return dict(name=name, dir=d, width=width, kind="data", face=face, window_um=list(win), layers=["M7", "M5"], **k)
    raw["partition_types"] = {"m": dict(outline_um=[W, W], buses=[bus("x", "in", "S", (lo, hi))]),
                              "a1": dict(outline_um=[W, W], buses=[bus("y", "out", "N", (lo, hi))]),
                              "a2": dict(outline_um=[W, W], buses=[bus("y", "out", "N", (W - hi, W - lo), order="lsb_high")])}
    raw["partitions"] = [dict(name="A1", type="a1", origin_um=[0.0, 0.0]), dict(name="M1", type="m", origin_um=[0.0, W]),
                         dict(name="A2", type="a2", origin_um=[X2, 0.0]),
                         dict(name="M2", type="m", origin_um=[X2, W], orient="MY")]
    raw["ports"] = [dict(id="p1", src=dict(part="A1", bus="y"), dst=dict(part="M1", bus="x"), width=width, epoch=False,
                         face="N", window_um=[lo, hi], layers=["M7", "M5"]),
                    dict(id="p2", src=dict(part="A2", bus="y"), dst=dict(part="M2", bus="x"), width=width, epoch=False,
                         face="N", window_um=[round(X2 + W - hi, 6), round(X2 + W - lo, 6)], layers=["M7", "M5"],
                         order="lsb_high")]
    raw["lanes"] = []
    return raw


def _type_pins(raw, pid, base, flip):
    import schema as S
    P = S.Plan(raw)
    pr = {p["id"]: p for p in raw["ports"]}[pid]
    return sorted((b, ln, round(172.8 - (c - base) if flip else c - base, 6)) for b, ln, c in S.pin_positions(pr, P.layers))


def test_mirror_parity_makes_mirrored_copies_share_one_pin_table():
    """UNIFY-TOOLS-R3 (S81 J7 '0.064 um mirror off-grid'): an odd M7 pin count on an even usable track count puts the
    MY copy's pins one track off the R0 copy's; the class window is resized to an odd track count and the copies agree"""
    import schema as S
    L = S.Plan(_mirror_pair(32.0, 32.3)).layers
    lo = 32.0                                   # clear of the partition PG bands
    hi = next(round(lo + 0.256 + 0.008 * k, 6) for k in range(40)
              if C._usable(L["M7"], "M7", [lo, lo + 0.256 + 0.008 * k]) % 2 == 0
              and C._usable(L["M5"], "M5", [lo, lo + 0.256 + 0.008 * k]) >= 2)
    raw = _mirror_pair(lo, hi)
    assert _type_pins(raw, "p1", 0.0, False) != _type_pins(raw, "p2", 345.6, True)     # the bug
    rep = C.solve(raw, ["m"])
    assert [(m[0], m[1]) for m in rep["mirror_parity"]] == [("m", "x")] and rep["mirror_parity_left"] == []
    assert rep["conflicts"] == [] and rep["mismatches_after"] == 0
    assert _type_pins(raw, "p1", 0.0, False) == _type_pins(raw, "p2", 345.6, True)
    # an even pin count, or ports that take their pins from the type frame, are left alone
    raw = _mirror_pair(lo, hi, width=4)
    assert C.mirror_parity(raw, ["m"]) == ([], [])
    raw = _mirror_pair(lo, hi)
    for pr in raw["ports"]:
        for k in ("face", "window_um", "layers", "order"):
            pr.pop(k, None)
    assert C.mirror_parity(raw, ["m"]) == ([], [])
