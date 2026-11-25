"""pure-helper tests for tools/autopilot/post_place_review.py (no OpenROAD needed)"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import post_place_review as P  # noqa: E402

REPORT = """Startpoint: a/r1 (rising edge-triggered flip-flop clocked by clk)
Endpoint: b/r2 (rising edge-triggered flip-flop clocked by clk)
Path Group: clk
Path Type: max

   0.000    0.000   clock clk (rise edge)
   0.000    0.000   clock network delay (ideal)
   0.000    0.000 ^ a/r1/CLK (DFFHQNx1_ASAP7_75t_R)
  30.000   30.000 v a/r1/QN (DFFHQNx1_ASAP7_75t_R)
  12.000   42.000 v u\\[1\\]/Y (BUFx2_ASAP7_75t_R)
   5.000   47.000 ^ b/r2/D (DFFHQNx1_ASAP7_75t_R)
          47.000   data arrival time

   0.000    0.000 ^ b/r2/CLK (DFFHQNx1_ASAP7_75t_R)
          -9.500   slack (VIOLATED)

Startpoint: in0 (input port clocked by clk)
Endpoint: c/r3 (rising edge-triggered flip-flop clocked by clk)
Path Group: clk
Path Type: max

   0.000    0.000 ^ in0 (in)
   8.000    8.000 ^ c/r3/D (DFFHQNx1_ASAP7_75t_R)
           8.000   data arrival time
           3.250   slack (MET)
"""
PINS = ("pin\tx\ty\tnet\tnet_hpwl_um\tfanout\n"
        "a/r1/CLK\t0\t0\tclk\t100\t9\na/r1/QN\t0\t0\tn1\t10\t2\nu\\[1\\]/Y\t10\t0\tn2\t4\t2\nb/r2/D\t10\t5\tn2\t4\t2\n"
        "in0\t0\t20\tn3\t30\t2\nc/r3/D\t30\t20\tn3\t30\t2\n")


def test_parse_paths():
    p = P.parse_paths(REPORT)
    assert [x["start"] for x in p] == ["a/r1", "in0"]
    assert [x["end"] for x in p] == ["b/r2", "c/r3"]
    assert p[0]["slack"] == -9.5 and p[1]["slack"] == 3.25
    assert [x[0] for x in p[0]["pins"]] == ["a/r1/CLK", "a/r1/QN", "u\\[1\\]/Y", "b/r2/D"]  # capture clock pin excluded
    assert p[1]["pins"][0] == ("in0", "^", "in")


def test_hpwl():
    assert P.hpwl([]) == 0 and P.hpwl([(1, 1)]) == 0
    assert P.hpwl([(0, 0), (3, 4), (1, 2)]) == 7


def test_path_rows_join_and_tsv():
    rows = P.path_rows(P.parse_paths(REPORT), P.read_pin_table(PINS), top=50)
    assert [r["rank"] for r in rows] == [1, 2] and rows[0]["slack"] == -9.5
    r = rows[0]
    assert (r["sx"], r["sy"], r["ex"], r["ey"]) == (0, 0, 10, 5)
    assert r["manhattan_um"] == 15 and r["n_cells"] == 3
    assert r["path_wl_um"] == 100 + 10 + 4 and r["nets"] == 3  # n2 counted once
    assert rows[1]["path_wl_um"] == 30
    assert len(P.path_rows(P.parse_paths(REPORT), P.read_pin_table(PINS), top=1)) == 1
    t = P.paths_tsv(rows).splitlines()
    assert t[0].split("\t") == P.PATH_COLS and len(t) == 3


def test_rudy_conserves_demand_and_localises():
    die = (0, 0, 100, 100)
    g = P.rudy_grid([(10, 10, 30, 20)], die, 10, 10)
    tot = sum(v for r in g for v in r) * 100  # bin area 100 um2
    assert abs(tot - (20 + 10)) < 1e-6  # (w+h)/(w*h) * area = w+h
    assert g[0][0] == 0 and g[1][1] > 0 and g[9][9] == 0
    assert P.rudy_grid([], die, 4, 4) == [[0.0] * 4 for _ in range(4)]


def test_pg_overlaps():
    mac = P.read_macros("name\tmaster\tx0\ty0\tx1\ty1\thl\thb\thr\tht\nm1\tRAM\t10\t10\t20\t20\t2\t2\t2\t2\n")
    assert mac[0]["halo_box"] == (8, 8, 22, 22)
    pins = [("m1", "A", "M5", (10, 12, 11, 13))]
    straps = [("VDD", "M5", 0, 8.5, 9, 9.5), ("VDD", "M5", 9.5, 12, 15, 12.5), ("VSS", "M5", 50, 50, 60, 51), ("VDD", "M4", 9.5, 12, 15, 12.5)]
    hits, st = P.pg_overlaps(straps, mac, pins)
    kinds = sorted((h["kind"], h["layer"]) for h in hits)
    assert kinds == [("halo", "M4"), ("halo", "M5"), ("pin", "M5")] or ("pin", "M5") in kinds
    assert st["straps"] == 4 and st["pin_hits"] == 1 and st["halo_hits"] >= 1


def test_queue_row_format():
    r = P.queue_row(1795608007.9, "ppr", "QC", "PLACE-GP", "epyc12", "/x/review", "rendering", "STAGE-PLATEAU", "/kit")
    f = r.split("\t")
    assert len(f) == 9 and r.count("\n") == 0
    assert f == ["1795608007", "ppr", "QC", "PLACE-GP", "epyc12:/x/review", "rendering", "STAGE-PLATEAU", "/kit", "LOG"]
    assert len(P.VIS_QUEUE_HEADER.split("\t")) == 9


def test_tcl_text_and_scripts(tmp_path):
    assert P.tcl_wrapper("run/results/b/3_3_place_gp.odb").splitlines()[0] == "read_db /kit/run/results/b/3_3_place_gp.odb"
    tcl = (Path(P.__file__).parent / "post_place_review.tcl").read_text()
    for needle in ("estimate_parasitics -placement", "report_checks -path_delay max", "unset_propagated_clock", "layout_dump.tcl", "nets.tsv"):
        assert needle in tcl
    sh = P.run_script("/k it", "r.odb", tmp_path / "rev", "img:1", 12, "ID", 50)
    assert "-v '/k it':/kit:ro" in sh and "--memory 12g" in sh and "--finish" in sh and "openroad -exit /rev/run.tcl" in sh


def test_launch_dry_and_errors(tmp_path):
    kit = tmp_path / "kit"
    (kit / "run").mkdir(parents=True)
    odb = kit / "run" / "3_3_place_gp.odb"
    odb.write_bytes(b"x")
    assert P.launch(str(kit), str(tmp_path / "x.odb"), "img")[0] == "odb-not-in-kit"
    assert P.launch(str(kit), str(kit / "nope.odb"), "img")[0] == "no-odb"
    odb.write_bytes(b"")
    assert P.resolve_odb(str(odb))[0] == ""
    (kit / "run" / "3_place.odb").write_bytes(b"y")
    assert P.resolve_odb(str(odb)) == (str(kit / "run" / "3_place.odb"), "3_3_place_gp.odb empty/missing, used 3_place.odb")
    odb.write_bytes(b"x")
    st, rev = P.launch(str(kit), str(odb), "img", rid="t1", dry=True)
    assert st == "dry-run" and rev == str(kit / "review")
    assert json.loads((Path(rev) / "review.json").read_text())["odb"] == str(odb)
    assert (Path(rev) / "run.sh").is_file() and (Path(rev) / "tools" / "post_place_review.tcl").is_file()
    calls = []
    st, rev = P.launch(str(kit), str(odb), "img", rid="t1", popen=lambda argv, **k: calls.append(argv), ot_run="/bin/ot-run")
    assert st == "rendering" and calls[0][:3] == ["nice", "-n", "10"] and "--direct" in calls[0] and "--no-spill" in calls[0]
    assert calls[0][-2:] == ["bash", str(Path(rev) / "run.sh")]


def test_finish_writes_products(tmp_path):
    lay = {"top": "t", "die": [0, 0, 100, 100], "pg": [["VDD", "M5", 0, 8.5, 9, 9.5]],
           "density": {"nx": 2, "ny": 2, "grid": [0.1, None, 0.9, 0.5]}}
    (tmp_path / "layout.json").write_text(json.dumps(lay))
    (tmp_path / "paths_ideal_raw.txt").write_text(REPORT)
    (tmp_path / "pins.tsv").write_text(PINS)
    (tmp_path / "nets.tsv").write_text("x0\ty0\tx1\ty1\tpins\n1\t1\t30\t20\t3\n")
    (tmp_path / "macros.tsv").write_text("name\tmaster\tx0\ty0\tx1\ty1\thl\thb\thr\tht\nm1\tRAM\t10\t10\t20\t20\t2\t2\t2\t2\n")
    (tmp_path / "macro_pins.tsv").write_text("macro\tpin\tlayer\tx0\ty0\tx1\ty1\n")
    s = P.finish(tmp_path)
    assert (tmp_path / "paths_ideal.tsv").is_file() and (tmp_path / "paths_ideal.txt").is_file()
    assert {"density", "rudy", "flight_lines", "macro_pg_overlay"} <= {f.split(".")[0] for f in s["files"]}
    assert all((tmp_path / f).stat().st_size > 0 for f in s["files"])
    assert s["paths"]["n"] == 2 and s["paths"]["worst_slack_ps"] == -9.5


DRC_RPT = ("violation type: Short\n\tsrcs: a b\n\tbbox = (10.0, 10.0) - (10.2, 10.2) on Layer M2\n"
           "violation type: Lef58EolKeepOut\n\tsrcs: c\n\tbbox = (50.0, 60.0) - (50.4, 60.2) on Layer M3\n")


def test_read_drt_marks_and_find_report(tmp_path):
    m = P.read_drt_marks(DRC_RPT)
    assert [(round(x, 1), round(y, 1), layer, t) for x, y, layer, t in m] == [(10.1, 10.1, "M2", "Short"), (50.2, 60.1, "M3", "Lef58EolKeepOut")]
    d = tmp_path / "run/reports/asap7/dp/base"
    d.mkdir(parents=True)
    (d / "5_route_drc.rpt-5.rpt").write_text(DRC_RPT)
    assert P.find_drt_report(str(tmp_path)).endswith("5_route_drc.rpt-5.rpt") and P.find_drt_report(str(tmp_path / "none")) == ""
    assert P.slack_label(-123.4) == "-123"


def test_flight_lines_carry_slack_labels_and_drt_markers(tmp_path):
    """COORD 06:2x: every render drew 0 failing paths; the kit now labels each of the top paths with its slack and overlays the DRT violations"""
    kit = tmp_path / "kit"
    d = kit / "run/reports/asap7/dp/base"
    d.mkdir(parents=True)
    (d / "5_route_drc.rpt").write_text(DRC_RPT)
    rev = tmp_path / "rev"
    rev.mkdir()
    (rev / "review.json").write_text(json.dumps({"kit": str(kit)}))
    (rev / "layout.json").write_text(json.dumps({"top": "t", "die": [0, 0, 100, 100], "pg": [], "density": {"nx": 1, "ny": 1, "grid": [0.5]}}))
    (rev / "paths_ideal_raw.txt").write_text(REPORT)
    (rev / "pins.tsv").write_text(PINS)
    (rev / "macros.tsv").write_text("name\tmaster\tx0\ty0\tx1\ty1\thl\thb\thr\tht\n")
    s = P.finish(rev)
    assert s["drt_report"]["marks"] == 2
    fl = next(f for f in s["files"] if f.startswith("flight_lines"))
    assert (rev / fl).stat().st_size > 0
    if fl.endswith(".svg"):
        txt = (rev / fl).read_text()
        assert "<text" in txt and "-9" in txt and "DRT violations" in txt
    (d / "5_route_drc.rpt").unlink()
    s3 = P.finish(rev)
    assert any("no 5_route_drc report" in n for n in s3["notes"]) and "drt_report" not in s3
