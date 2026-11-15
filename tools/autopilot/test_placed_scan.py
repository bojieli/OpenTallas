import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import placed_scan as PS  # noqa: E402


def dump(path, dist):
    # flop A (x 10) -> 2 buffers -> flop B (x 10+dist); flop C -> flop D 100 um apart; strap flop pair far apart
    rows = ["D\t0\t0\t2000\t100"]
    def c(i, kind, x, name):
        rows.append(f"C\t{i}\t{kind}\tM\t{x}\t10\t{x + 1}\t11\t{name}")
    c(1, "S", 10, "u_a_q[0]"); c(2, "B", 20, "b1"); c(3, "B", 30, "b2"); c(4, "S", 10 + dist, "u_b_q[0]")
    c(5, "S", 10, "u_c"); c(6, "S", 110, "u_d")
    c(7, "S", 10, "u_strap_s"); c(8, "S", 1900, "u_strap_e")
    rows += ["N\tSIGNAL\ti1\ti2", "N\tSIGNAL\ti2\ti3", "N\tSIGNAL\ti3\ti4", "N\tSIGNAL\ti5\ti6", "N\tSIGNAL\ti7\ti8"]
    Path(path).write_text("\n".join(rows) + "\n")


def run(tmp, dist):
    g = tmp / "geom.tsv"
    dump(g, dist)
    out = tmp / "o"
    rc = PS.main([str(g), "--out", str(out), "--top", "0"])
    return rc, json.loads((out / "placed_scan.json").read_text())


def test_need_station(tmp_path, capsys):
    rc, j = run(tmp_path, 900)
    assert rc == 0                                   # advisory
    assert j["groups_need_station"] == 1
    g = j["groups"][0]
    assert (g["src"], g["end"], g["cls"]) == ("u_a", "u_b", "NEED-STATION")
    assert "AP_PLACED_SCAN NEED-STATION" in capsys.readouterr().out


def test_reach_only_and_strap_skipped(tmp_path):
    _, j = run(tmp_path, 500)
    assert [g["cls"] for g in j["groups"]] == ["REACH"]   # strap pair (1890 um) is not a bus group


def test_ok_and_strict(tmp_path, capsys):
    rc, j = run(tmp_path, 100)
    assert j["groups"] == [] and "AP_PLACED_SCAN OK" in capsys.readouterr().out
    g = tmp_path / "geom.tsv"
    dump(g, 900)
    assert PS.main([str(g), "--strict", "--top", "0"]) == 1


def test_plan_row(tmp_path):
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps({"partition_types": {"T": {"internal_stations": [
        {"conn": "bus:u_a", "from_um": [0, 0], "regs_um": [[300, 0]], "to_um": [600, 0]}]}}}))
    assert PS.plan_rows(str(plan), "T") == [("u_a", 1, 300.0)]
    assert PS.row_for([("u_busname", 2, 300.0)], "x_u_busname_y", "e") == "2/300um"
    assert PS.row_for([("u_busname", 2, 300.0)], "x", "e") == "none"
    assert PS.row_for(None, "x", "e") == "NA"


def test_station_rows(tmp_path):
    _, j = run(tmp_path, 900)
    r = json.loads((tmp_path / "o" / "placed_scan_rows.json").read_text())["rows"]
    assert len(r) == 1 and r[0]["stations"] == 2 and len(r[0]["regs_um"]) == 2
    assert r[0]["hop_um"] <= 405 and r[0]["conn"] == "group:u_a->u_b"
