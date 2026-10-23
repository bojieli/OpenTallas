"""Unit tests for corridors.py (policy s81-shifted) on a synthetic 2-column x 3-row frame array (W side, hub east).

(a) no tie-offs: every port of a variant carries a lane in every instance of that variant;
(b) abutting ports line up in die coordinates (frame out port = neighbour in port = the lane's continuing leg);
(c) the variant count per frame family is reported and is <= 4 (here 1 for uniform rows, 2 with one mirrored row).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import corridors  # noqa: E402
import geom  # noqa: E402
from dump_io import Bus, Inst, Master  # noqa: E402

FW, FH = 1436.832, 3369.6
COLS = (100.0, 1623.232)                 # col 0 (outer, die edge) and col 1; street 86.4 um
ROWS = (100.0, 3728.8, 7357.6)          # row streets 259.2 um
HUB = ("u_s_0", 12000.0, 4000.0, 1200.0, 3000.0)
FAM = "col_h9_l4_lp"


class FakeDump:
    def __init__(self, orients):
        self.die = {"die": [0.0, 0.0, 20000.0, 11000.0],
                    "layers": [{"name": "M8", "dir": "HORIZONTAL", "pitch": 0.08},
                               {"name": "M9", "dir": "VERTICAL", "pitch": 0.08}]}
        fr = Master("rv_f", FW, FH, 2, {}, {})
        fr.buses = {"x": Bus("x", "INPUT", 1104, ("M4",), "E", 341.086, 530.914),
                    "ret": Bus("ret", "OUTPUT", 70, ("M4",), "E", 534.129, 551.871)}
        hub = Master("rv_hub", HUB[3], HUB[4], 2, {}, {})
        hub.buses = {"xc": Bus("xc", "OUTPUT", 1104, ("M4",), "W", 100, 300),
                     "rt": Bus("rt", "INPUT", 70, ("M4",), "W", 400, 420)}
        self.masters = {"rv_f": fr, "rv_hub": hub}
        self.insts = {HUB[0]: Inst(HUB[0], "rv_hub", *HUB[1:], "R0")}
        for (c, r), o in orients.items():
            n = f"u_f_{c}{r}"
            self.insts[n] = Inst(n, "rv_f", COLS[c], ROWS[r], FW, FH, o)

    def layer(self, name):
        return next((L for L in self.die["layers"] if L["name"] == name), None)


def build(orients, **opts):
    """-> (policy, census-like groups); orients {(col, row): orient}."""
    d = FakeDump(orients)
    blocks = {n: dict(inst=n, master=i.master, x=i.x, y=i.y, w=i.w, h=i.h) for n, i in d.insts.items()}
    hub_pt = (HUB[1], HUB[2] + 200.0)
    groups = []
    for (c, r), o in sorted(orients.items()):
        n = f"u_f_{c}{r}"
        i = d.insts[n]
        for bus in ("x", "ret"):
            b = d.masters["rv_f"].buses[bus]
            pt = geom.xform(*geom.face_point(b.face, b.lo, b.hi, FW, FH), FW, FH, o, i.x, i.y)
            if bus == "x":
                groups.append(dict(src=HUB[0], src_bus="xc", dst=n, dst_bus="x", kind="data", bits=1104,
                                   src_pt=list(hub_pt), dst_pt=list(pt)))
            else:
                groups.append(dict(src=n, src_bus="ret", dst=HUB[0], dst_bus="rt", kind="data", bits=70,
                                   src_pt=list(pt), dst_pt=list(hub_pt)))
    o = dict(groups=groups, n_street=0, families={FH: FAM})
    o.update(opts)
    pol = corridors.make_policy("s81-shifted", "synthetic", blocks, d, {}, o)
    return pol, groups


def run(orients, **opts):
    pol, groups = build(orients, **opts)
    specs, variant, lane_hosts, misc = corridors.simulate(pol, groups, reach=1500.0, rep=450.0)
    return pol, groups, specs, variant, lane_hosts


UNIFORM = {(0, 0): "R0", (1, 0): "R0", (0, 1): "R0", (1, 1): "R0", (0, 2): "MX", (1, 2): "MX"}


def test_hooks_row_aligned_orders_and_shifted_slot():
    pol, groups = build(UNIFORM)
    ret0 = next(g for g in groups if g["src"] == "u_f_00")
    x0 = next(g for g in groups if g["dst"] == "u_f_00")
    assert pol.route_orders(ret0) == ("HV",) and pol.route_orders(x0) == ("VH",)
    lp = pol.lane_plan(ret0)
    assert lp["kind"] == "corridor" and [h["F"] for h in lp["hosts"]] == ["u_f_10"]
    h = lp["hosts"][0]
    assert abs(h["y_in"] - (ROWS[0] + 543.0)) < 1e-6                 # own ret pin = slot 0
    assert abs(h["y_out"] - h["y_in"] - 200.0) < 1e-6                # corridor j in -> slot j + 1 out
    assert pol.band(ret0, True, 0, 119, 0, 0) == round(h["y_out"], 3)
    assert pol.band(ret0, False, 0, 119, 0, 0) is None              # vertical legs: plan default
    # refine: pin -> jog inside the host frame -> continuing leg at the band, then the plan's V leg at the hub
    sp, dp = tuple(ret0["src_pt"]), tuple(ret0["dst_pt"])
    y = pol.band(ret0, True, 0, 119, sp[0], dp[0])
    pts = pol.refine(ret0, corridors.dedupe([sp, (sp[0], y), (dp[0], y), dp]))
    xm = COLS[1] + FW / 2
    assert pts[0] == (round(sp[0], 3), round(sp[1], 3)) and (round(xm, 3), round(h["y_in"], 3)) in pts
    assert (round(xm, 3), round(y, 3)) in pts and pts[-1] == (round(dp[0], 3), round(dp[1], 3))
    # a mirrored (MX) host row: the own pins of the MX col-0 frame are slot 0 of the MX host as well
    lp2 = pol.lane_plan(next(g for g in groups if g["src"] == "u_f_02"))
    assert lp2["hosts"][0]["how"] == ("b", 0)


def test_a_no_tie_offs():
    pol, groups, specs, variant, _ = run(UNIFORM)
    assert set(specs) == {"u_f_10", "u_f_11", "u_f_12"}             # col-1 frames host the col-0 bundles
    assert corridors.check_no_ties(specs, variant) == []
    for inst, s in specs.items():
        lanes = {q["path"] for q in s["paths"] if q["lane"]}
        assert {p["path"] for p in s["ports"]} == lanes and len(s["ports"]) == 2 * len(s["paths"])
    # a port without a lane is flagged (it would be a tie-off)
    bad = dict(ports=specs["u_f_10"]["ports"] + [dict(name="ft9_i", path=9, dir="input", face="W", lo=1, hi=2,
                                                      layer="M8", bits=8)], paths=specs["u_f_10"]["paths"])
    assert corridors.check_no_ties({"u_f_10": bad}, {"u_f_10": "v"})
    pol.variant_of("u_f_10", "rv_f", bad["ports"], bad["paths"])
    assert any("tie-offs" in i for i in pol.issues)


def test_b_abutting_ports_line_up():
    pol, groups, specs, variant, lane_hosts = run(UNIFORM)
    assert corridors.check_alignment(lane_hosts, pol.frames) == []
    for g in groups:
        lp = pol.lane_plan(g)
        if not lp["hosts"]:
            continue
        hs = lane_hosts[pol.key(g)]
        F = pol.frames[hs[0]["F"]]
        own = lp["P"][1]
        # in port of the host = the col-0 frame's own pin row, out port = the band of the continuing leg
        pin_up, pin_dn = (hs[0]["p_in"], hs[0]["p_out"]) if lp["src_is_frame"] else (hs[0]["p_out"], hs[0]["p_in"])
        assert abs(pin_up[1] - own) < 1e-6 and abs(pin_dn[1] - lp["y_hub"]) < 1e-6
        assert abs(pin_up[0] - F.x) < 1e-6 and abs(pin_dn[0] - (F.x + F.w)) < 1e-6
        # the master-frame port offsets are the quantised slots: own centre + P (unflipped) or mirrored (MX)
        m_out = F.d2m(pin_dn[1])
        assert abs(m_out - ((436.0 if lp["bus"] == "x" else 543.0) + 200.0)) < 1e-3


def test_c_variant_count_reported_le4():
    pol, *_ = run(UNIFORM)
    r = pol.report()["families"][FAM]
    assert r["n_variants"] == 1 and r["le4"] and r["ft_hosts"] == 3 and r["base_only"] == 3 and r["why"] == []
    (name, v), = r["variants"].items()
    assert v["n"] == 3 and v["n_paths"] == 2 and sorted(v["corridors"]) == ["ret:b0", "x:b0"]
    # one row with opposite y flips: the host receives on the mirrored ladder -> a second variant, still <= 4
    mixed = dict(UNIFORM)
    mixed[(0, 2)] = "R0"
    pol2, *_ = run(mixed)
    r2 = pol2.report()["families"][FAM]
    assert r2["n_variants"] == 2 and r2["le4"]
    assert any(":t0" in c for v in r2["variants"].values() for c in v["corridors"])


def test_street_riders_cross_no_frame():
    pol, groups, specs, variant, _ = run(UNIFORM, n_street=1)
    assert specs == {}                                              # every col-0 lane rides its row street
    for g in groups:
        lp = pol.lane_plan(g)
        if pol.frames[lp["U"]].col == 0:
            r = pol.rows[pol.frames[lp["U"]].row]
            assert lp["kind"] == "street" and r["street"][0] <= lp["y_hub"] <= r["street"][1]
    assert pol.report()["families"][FAM]["n_variants"] == 0
