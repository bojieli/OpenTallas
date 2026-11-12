"""SEAM-HOP-1: advisory G0 seam-hop check (seam_hop.py): last station of one partition -> first station of the next."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import schema  # noqa: E402
import seam_hop  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _geo(raw):
    P = schema.Plan(raw)
    return P, {lid: check.lane_geometry(P, lid) for lid in P.lanes}


def _far(raw, xs):
    """pm1/pm2 share type mid: stations at type-frame x = xs on the slot centre line (fx and fr)."""
    p = copy.deepcopy(raw)
    P, geo = _geo(p)
    y = geo["x"][1][1][1]                # first station y of lane x (pm1 origin y = 0)
    for s in p["partition_types"]["mid"]["ft_slots"]:
        s["regs_um"] = [[x, y] for x in xs]
    return p


def test_default_tiny_has_no_long_seam_hop():
    P, geo = _geo(copy.deepcopy(EX))
    rows = seam_hop.seam_hops(P, geo)
    assert len(rows) == 2 and not any(r["over"] for r in rows)       # lanes x and r, 288 um each
    assert {round(r["hop_um"]) for r in rows} == {288}
    R, summ = check.run(copy.deepcopy(EX), completeness=True)
    assert not [i for i in R.items if i["check"] == "seam_hop"]
    assert summ["seam_hops"]["over"] == 0 and summ["seam_hops"]["hops"] == 2


def test_long_seam_hop_is_a_warning_and_changes_no_error_count():
    p = _far(EX, [100.0, 200.0, 300.0])       # last station 564 um before pm1 east edge; the first pm2 station is the input site
    P, geo = _geo(p)
    rows = seam_hop.seam_hops(P, geo)
    x = next(r for r in rows if r["lane"] == "x")
    assert x["over"] and abs(x["hop_um"] - 564) < 2 and x["src"] == "pm1.fx[2]" and x["dst"] == "pm2.fx[0]"
    R, summ = check.run(copy.deepcopy(p), completeness=True)
    warn = [i for i in R.items if i["check"] == "seam_hop"]
    assert warn and all(i["level"] == "WARN" for i in warn) and " um > 405" in warn[0]["msg"]
    assert summ["seam_hops"]["over"] >= 1 and summ["seam_hops"]["worst"][0]["hop_um"] >= 564
    # advisory: switching the check off leaves the ERROR list byte-identical
    R0, _ = check.run(copy.deepcopy(p), completeness=True, seam_hop="off")
    assert [i for i in R.items if i["level"] == "ERROR"] == [i for i in R0.items if i["level"] == "ERROR"]
    assert not [i for i in R0.items if i["check"] == "seam_hop"]


def test_limit_parameter():
    P, geo = _geo(copy.deepcopy(EX))
    assert all(r["over"] for r in seam_hop.seam_hops(P, geo, limit=100))
    assert not any(r["over"] for r in seam_hop.seam_hops(P, geo, limit=288))


def test_lane_end_uses_the_sink_internal_station():
    """t19 NW_io case: the last station of the source side sits at the seam pin, the sink's first station is inside."""
    p = copy.deepcopy(EX)
    P, geo = _geo(p)
    last = P.ports[P.lanes["x"]["ports"][-1]]["dst"]
    ptype = P.parts[last["part"]]["type"]
    pin = P.port_point(P.lanes["x"]["ports"][-1])
    po = P.parts[last["part"]]["origin_um"]
    near = [pin[0] - po[0], pin[1] - po[1]]
    assert not [r for r in seam_hop.seam_hops(P, geo) if r["dst"].startswith(last["part"])]   # no declared station
    for dx, want in ((300.0, 300.0), (800.0, 800.0)):
        q = copy.deepcopy(p)
        q["partition_types"][ptype]["internal_stations"] = [dict(
            conn=f"bus:{last['bus']}", from_um=near, to_um=[near[0] - 900, near[1]], regs_um=[[near[0] - dx, near[1]]],
            bits=1)]
        P2, geo2 = _geo(q)
        r = next(r for r in seam_hop.seam_hops(P2, geo2) if r["dst"].startswith(last["part"]))
        assert r["src"].startswith("pm2.") and r["dst"].endswith("[internal]")
        to_pin = abs(r["src_xy"][0] - r["pin_xy"][0]) + abs(r["src_xy"][1] - r["pin_xy"][1])
        assert abs(r["hop_um"] - (to_pin + want)) < 1.0                  # last station -> pin -> internal station
        assert r["over"] == (r["hop_um"] > 405) and (dx < 800 or r["over"])
