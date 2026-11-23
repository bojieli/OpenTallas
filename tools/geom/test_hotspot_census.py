"""tests for tools/geom/hotspot_census.py (HOTSPOT-CENSUS)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hotspot_census as HC  # noqa: E402


def _marker(d, x, y, ov, cap=10, nets="net:u_bound.u_a.q[1] net:net5"):
    t = "Horizontal" if d == "H" else "Vertical"
    return (f"violation type: {t} congestion\n\tsrcs: {nets}\n\tcomment: capacity:{cap} usage:{cap + ov} congestion:{ov}\n"
            f"\tbbox = ({x:.4f}, {y:.4f}) - ({x + 0.57:.4f}, {y + 0.57:.4f}) on Layer -\n")


def _write_cong(tmp):
    txt = ""
    for i in range(10):            # H cluster A: 10 gcells x 40 = 400 ovfl next to a channel between two macros
        txt += _marker("H", 100 + 0.57 * i, 50.0, 40)
    for i in range(3):             # H speck: 3 ovfl, < 50 and < 1% -> dropped
        txt += _marker("H", 300 + 0.57 * i, 300.0, 1)
    for i in range(30):            # V cluster on a macro (gap of 1 gcell is closed)
        txt += _marker("V", 400.0, 400 + 1.14 * i, 2)
    p = tmp / "congestion.rpt"
    p.write_text(txt)
    return p


def _write_geom(tmp):
    rows = ["D\t0\t0\t600\t600", "R\t2\t2\t598\t598",
            "C\t1\tM\tcoreA\t60\t20\t100\t80\tu_bound/u_a",
            "C\t2\tM\tcoreB\t106\t20\t160\t80\tu_bound/u_b",
            "C\t3\tM\tcoreC\t380\t380\t450\t460\tu_bound/u_c"]
    k = 10
    for i in range(40):
        rows.append(f"C\t{k}\tL\tNAND2x1\t{101 + 0.2 * (i % 20):.2f}\t{49 + 0.3 * (i // 20):.2f}\t"
                    f"{101.2 + 0.2 * (i % 20):.2f}\t{49.3 + 0.3 * (i // 20):.2f}\tu_bound.u_x/g{i}")
        k += 1
    rows.append("P\t0\tclk\tINPUT\tCLOCK\tM5\t300\t0")
    p = tmp / "geom.tsv"
    p.write_text("\n".join(rows) + "\n")
    return p


STA = """Startpoint: u_bound.u_a/r_q[3]$_DFF_P_
            (rising edge-triggered flip-flop clocked by clk)
Endpoint: u_bound.u_b/s_q[3]$_DFF_P_
          (rising edge-triggered flip-flop clocked by clk)
Path Group: clk
Path Type: max

  Delay    Time   Description
---------------------------------------------------------
   0.00    0.00   clock clk (rise edge)
 400.00  400.00   clock network delay (propagated)
   0.00  400.00 ^ u_bound.u_a/r_q[3]$_DFF_P_/CLK (DFFHQNx1_ASAP7_75t_R)
  60.00  460.00 v u_bound.u_a/r_q[3]$_DFF_P_/QN (DFFHQNx1_ASAP7_75t_R)
 300.00  760.00 v buf1/Y (BUFx4_ASAP7_75t_R)
 300.00 1060.00 v buf2/Y (BUFx4_ASAP7_75t_R)
        1060.00   data arrival time

 833.00  833.00   clock clk (rise edge)
 200.00 1033.00   clock network delay (propagated)
        1000.00   data required time
---------------------------------------------------------
         -60.00   slack (VIOLATED)


Startpoint: u_bound.u_c/x$_DFF_P_
            (rising edge-triggered flip-flop clocked by clk)
Endpoint: u_bound.u_d/y$_DFF_P_
          (rising edge-triggered flip-flop clocked by clk)
Path Group: clk
Path Type: min

  Delay    Time   Description
---------------------------------------------------------
   0.00    0.00   clock clk (rise edge)
 100.00  100.00   clock network delay (propagated)
  20.00  120.00 v u_bound.u_c/x$_DFF_P_/QN (DFFHQNx1_ASAP7_75t_R)
         120.00   data arrival time

   0.00    0.00   clock clk (rise edge)
 150.00  150.00   clock network delay (propagated)
         150.00   data required time
---------------------------------------------------------
         -30.00   slack (VIOLATED)
"""


def test_clusters_threshold_and_context(tmp_path):
    cong = _write_cong(tmp_path)
    geom = _write_geom(tmp_path)
    (tmp_path / "sta.rpt").write_text(STA)
    out = tmp_path / "o"
    res = HC.main(["analyze", "--out", str(out), "--name", "t", "--geom", str(geom), "--cong", str(cong),
                   "--sta", str(tmp_path / "sta.rpt")])
    cl = res["clusters"]
    assert [c["d"] for c in cl] == ["H", "V"]            # speck dropped, V gap closed into one cluster
    h, v = cl
    assert h["ov"] == 400 and v["ov"] == 60 and v["gcells"] == 30
    assert h["ctx"]["channel"].startswith("6.0um")
    assert h["cause"] == "MACRO-CHANNEL"
    assert v["cause"] == "OVER-MACRO"
    assert res["totals"]["H"]["overflow"] == 403
    assert sum(1 for ln in (out / "census.tsv").read_text().splitlines() if ln.startswith("t\tC")) == 2
    assert json.loads((out / "census.json").read_text())["name"] == "t"


def test_timing_classes_skew_and_reach(tmp_path):
    (tmp_path / "sta.rpt").write_text(STA)
    paths = HC.parse_sta(str(tmp_path / "sta.rpt"))
    assert len(paths) == 2
    s = [p for p in paths if p["type"] == "max"][0]
    assert s["lat_launch"] == 400.0 and s["lat_capture"] == 200.0 and s["slack"] == -60.0
    tc = HC.timing_classes(paths, bound_ps=250)
    st = [t for t in tc if t["kind"] == "setup"][0]
    assert st["skew"] == -200.0 and st["insertion_share"] == 1.0 and st["cause"] == "CLOCK-SKEW"
    assert st["start_grp"] == "u_a" and st["end_grp"] == "u_b"
    assert HC._norm_grp("u_bound.g_u_lf3_u_vp_driver_xr2_q") == "g_u_lfN_u_vp"
    ho = [t for t in tc if t["kind"] == "hold"][0]
    assert ho["skew"] == 50.0 and ho["cause"] == "HOLD-SKEW"


def test_kit_sources_picks_latest_nonempty(tmp_path):
    base = tmp_path / "run" / "results" / "asap7" / "d" / "base"
    rep = tmp_path / "run" / "reports" / "asap7" / "d" / "base"
    base.mkdir(parents=True); rep.mkdir(parents=True)
    (base / "5_1_grt.odb").write_text("")                 # 0-byte stub is skipped
    (base / "4_cts.odb").write_text("x")
    (rep / "congestion.rpt").write_text("x")
    (rep / "4_cts_final.rpt").write_text("x")
    (rep / "4_cts_post_hook.rpt").write_text("x")
    (tmp_path / "core_latency.json").write_text('{"target_ps": 250.0}')
    s = HC.kit_sources(str(tmp_path))
    assert s["stage"] == "4_cts.odb" and s["sta"][0].endswith("4_cts_post_hook.rpt") and s["bound_ps"] == 250.0


def test_gaps_and_probe_pass_check(tmp_path):
    cov = tmp_path / "VIS-COVERAGE.tsv"
    cov.write_text("# hdr\ndie\ttype\tfamily\tvis_lane\trender_paths\tverdict\tcause_class\tstructural_row\trow_status\tupdated\n"
                   "S81\ts81sl_leaf__t44\tleaf\tLEAF-ROUTE-CBC\t-\tv\tLANE-JUNCTION\tJ9-LEAF-LANECH+EDGESTRIP\tDRAFT\tx\n")
    res = dict(name="s81__s81sl_leaf__t44__clf4ea6d4b",
               clusters=[dict(id=1, d="V", ov=900, frac=0.9, bbox=(1, 2, 3, 4), cause="MACRO-CHANNEL", also=[])],
               timing=[dict(kind="hold", start_grp="a", end_grp="b", path_group="clk", count=3, worst=-70.0, skew=100.0,
                            cause="HOLD-SKEW"),
                       dict(kind="setup", start_grp="a", end_grp="b", path_group="clk", count=1, worst=-20.0, skew=0.0,
                            cause="REACH")])           # setup -20 is above -42: not an item
    cj = tmp_path / "census.json"
    cj.write_text(json.dumps(res))
    gp = tmp_path / "GAPS.tsv"
    out = HC.main(["gaps", "--coverage", str(cov), "--out", str(gp), str(cj)])
    rows = [r.split("\t") for r in out[1:]]
    assert len(rows) == 2
    assert rows[0][6] == "J9-LEAF-LANECH+EDGESTRIP" and rows[0][7] == "LEAF-ROUTE-CBC"   # channel cluster covered
    assert rows[1][6] == "NONE" and rows[1][5] == "HOLD-SKEW"                            # tap skew not covered
    assert HC.main(["check", "--gaps", str(gp), "--type", "s81sl_leaf__t44"]) == 1
    assert HC.main(["check", "--gaps", str(gp), "--type", "s81sl_leaf__t99"]) == 2


def test_load_gcells_layer_mix(tmp_path):
    g = tmp_path / "gcells.json"
    g.write_text(json.dumps(dict(markers=[["H", 0, 0, 0.57, 0.57, 10, 70, 60, {"M4": 40, "M6": 20}]],
                                 totals={"H": 60, "V": 0}, hot90={"H": 5, "V": 0})))
    ms, _ = HC.load_gcells(str(g))
    cl, tot = HC.clusters(ms)
    assert tot["H"]["overflow"] == 60 and cl[0]["layers"] == {"M4": 40, "M6": 20}


def test_flow_findings(tmp_path):
    lg = tmp_path / "5_1_grt.log"
    lg.write_text("[WARNING GRT-0273] Clock net clk_t3 NDR dropped\n[WARNING GRT-0273] Clock net clk_t4 NDR dropped\n"
                  "[WARNING STA-1212] noise\n[ERROR RSZ-0060] max buffer count reached\n")
    ff = {x["code"]: x for x in HC.flow_findings([str(lg)])}
    assert ff["GRT-0273"]["count"] == 2 and ff["GRT-0273"]["cause"] == "CLOCK-NDR-DROP"
    assert ff["RSZ-0060"]["cause"] == "REPAIR-CAP" and "STA-1212" not in ff


def test_check_probe_vs_baseline(tmp_path):
    gp = tmp_path / "G.tsv"
    gp.write_text("die\ttype\tfamily\titem\tsize\tcause\tcovering_row\towner_lane\tcensus\n"
                  "s81\ts81sl_leaf__t4\tleaf\tC1\t9\tMACRO-CHANNEL\tROW1\tL\tx\n")
    b = tmp_path / "b.json"; b.write_text(json.dumps(dict(totals={"H": {"overflow": 1000}, "V": {"overflow": 0}}, clusters=[1])))
    p = tmp_path / "p.json"; p.write_text(json.dumps(dict(totals={"H": {"overflow": 50}, "V": {"overflow": 0}}, clusters=[])))
    q = tmp_path / "q.json"; q.write_text(json.dumps(dict(totals={"H": {"overflow": 200}, "V": {"overflow": 0}}, clusters=[])))
    base = ["check", "--gaps", str(gp), "--type", "s81sl_leaf__t4", "--baseline", str(b)]
    assert HC.main(base + ["--probe", str(p)]) == 0
    assert HC.main(base + ["--probe", str(q)]) == 1
