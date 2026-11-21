"""station_route_spread.py (OPUS-FIX-KV-PV-R3 11-20): stations bunched next to the face are re-sited on the placed driver -> sink
route around hard macros, every hop <= reach, stations added only when the route needs them, plan order (incl. reversed) kept."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import geom_rules  # noqa: E402
import station_route_spread as SRS  # noqa: E402


def _geom(tmp, n=3, src=(100.0, 900.0), macro=(300.0, 300.0, 700.0, 1000.0), sta_x=980.0):
    """die 1000x1000, a hard macro in the middle, launch flop at src, n stations bunched at x sta_x y 100, out pin (1000,100)"""
    L = ["D\t0\t0\t1000\t1000", "R\t0\t0\t1000\t1000"]
    L.append("C\t1\tS\tDFF\t%f\t%f\t%f\t%f\tu_bound.u_src.fault$_DFF_P_" % (src[0], src[1], src[0] + 1, src[1] + 1))
    L.append("C\t2\tM\tCORE\t%f\t%f\t%f\t%f\tu_bound.u_core" % macro)
    for k in range(n):
        x = sta_x - 10 * (n - 1 - k)
        L.append("C\t%d\tS\tDFF\t%f\t100\t%f\t101\tu_bound.u_ist_o_f_%d.q$_DFF_P_" % (10 + k, x, x + 1, k))
    L.append("C\t50\tB\tBUF\t500\t50\t501\t51\tbuf_x")
    L.append("P\t0\to_f\tOUTPUT\tSIGNAL\tM4\t1000\t100")
    L.append("N\tn0\ti1\ti50")
    L.append("N\tn1\ti50\ti10")
    for k in range(n - 1):
        L.append("N\ts%d\ti%d\ti%d" % (k, 10 + k, 11 + k))
    L.append("N\tsq\ti%d\tp0" % (10 + n - 1))
    L.append("N\tclk\t-\t" + "\t".join("i%dc" % (10 + k) for k in range(n)) + "\ti1c")
    g = tmp / "geom.tsv"
    g.write_text("\n".join(L) + "\n")
    return g


def _plan(n=3, rev=False):
    regs = [[980.0 - 10 * (n - 1 - k), 100.5] for k in range(n)]
    if rev:
        regs = regs[::-1]
    return {"partition_types": {"T": {"internal_stations": [
        {"conn": "bus:o_f", "from_um": regs[0], "to_um": [1000.0, 100.0], "regs_um": regs, "bits": 1, "launch": "leaf"},
        {"conn": "bus:o_g", "regs_um": [[1, 1]], "bits": 1}]}}}


def test_spreads_bunched_stations_on_the_route(tmp_path):
    D = geom_rules.Design(str(_geom(tmp_path)))
    p = _plan()
    rows = SRS.type_delta("T", p["partition_types"]["T"], D, reach=300.0)
    r = rows[0]
    assert r["hop_before_um"] > 1000
    assert r["stations_new"] >= r["stations"] and r["hop_after_um"] <= 300.0
    regs = p["partition_types"]["T"]["internal_stations"][0]["regs_um"]
    assert len(regs) == r["stations_new"] and r["added_cycles"] == len(regs) - 3
    # route goes around the macro: no station inside it
    assert not any(300 < x < 700 and 300 < y < 1000 for x, y in regs)
    # chain order: driver end first, hops along the chain within reach (Manhattan, small grid slack)
    pts = [tuple(r["driver_um"])] + [tuple(v) for v in regs] + [tuple(r["sink_um"])]
    assert max(SRS.md(a, b) for a, b in zip(pts, pts[1:])) <= 300.0 + 15.0
    assert "STATION-ROUTE-SPREAD" in p["partition_types"]["T"]["internal_stations"][0]["note"]
    assert rows[1].get("skip")   # o_g has no placed stations: untouched


def test_keep_count_and_reversed_order(tmp_path):
    D = geom_rules.Design(str(_geom(tmp_path)))
    p = _plan(rev=True)
    rows = SRS.type_delta("T", p["partition_types"]["T"], D, reach=300.0, keep=True)
    regs = p["partition_types"]["T"]["internal_stations"][0]["regs_um"]
    assert rows[0]["reversed"] and rows[0]["added_cycles"] == 0 and len(regs) == 3
    # reversed plan: regs[-1] is station 0, the one nearest the driver
    d = tuple(rows[0]["driver_um"])
    assert SRS.md(tuple(regs[-1]), d) < SRS.md(tuple(regs[0]), d)


def test_in_reach_chain_untouched(tmp_path):
    D = geom_rules.Design(str(_geom(tmp_path, src=(960.0, 120.0))))
    p = _plan()
    before = json.dumps(p)
    rows = SRS.type_delta("T", p["partition_types"]["T"], D, reach=300.0)
    assert rows[0]["hop_before_um"] <= 300 and "stations_new" not in rows[0]
    assert json.dumps(p) == before


def test_cli_keeps_plan_format(tmp_path):
    g = _geom(tmp_path)
    pl = tmp_path / "p.json"
    pl.write_text(json.dumps(_plan(), separators=(",", ":")) + "\n")
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    assert SRS.main([str(pl), "T", str(g), str(out), str(rep)]) == 0
    txt = out.read_text()
    assert "\n" not in txt[:-1] and json.loads(txt)["partition_types"]["T"]["internal_stations"][0]["regs_um"] != _plan()["partition_types"]["T"]["internal_stations"][0]["regs_um"]
    assert json.loads(rep.read_text())["rows"][0]["hop_after_um"] <= 300
