"""dieclock_regeq --routed (REACH-FIX-2 11-12, COORD): the region-equalisation loop on ROUTED arrivals, with the abort
caps; build and route are stubbed (arrival = leaf base + 0.1 ps per um of leaf pad, routed overflow scripted)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dieclock_regeq as RQ  # noqa: E402

BASE = {"n10_0": 1000.0, "n10_1": 990.0, "n10_2": 960.0, "n10_3": 830.0}     # n10_3 needs ~1700 um > 1500


def _stubs(monkeypatch, overflow_at=None):
    calls = []

    def build(plan, d, pf, extra):
        d.mkdir(parents=True, exist_ok=True)
        pad = json.loads(Path(pf).read_text())
        taps = [dict(port="t_%s_%d" % (k, j), leaf=k) for k in BASE for j in range(2)]
        (d / "tree.json").write_text(json.dumps(dict(taps=taps, meta=dict(padding_um=0.0))))
        (d / "ctree.spef").write_text("*SPEF model\n")
        (d / "pad.json").write_text(json.dumps(pad))
        calls.append(("build", d.name, dict(pad)))

    def routed(d, kit, a, extra):
        pad = json.loads((d / "pad.json").read_text())
        res = dict(corners={})
        for c, f in (("TT", 1.0), ("FF", 0.8)):
            pd = d / "routed" / ("pd_%s" % c)
            pd.mkdir(parents=True, exist_ok=True)
            (pd / "x.spef").write_text("*SPEF routed\n")
            rows = ["T t_%s_%d %.3f %.3f 20" % (k, j, f * (b + 0.1 * pad.get(k, 0.0) + j * 0.5),
                                                f * (b + 0.1 * pad.get(k, 0.0))) for k, b in BASE.items() for j in range(2)]
            (pd / ("arr_%s.txt" % c)).write_text("\n".join(rows) + "\n")
            it = int(d.name[2:])
            ov = [0, 0, 3] if overflow_at is not None and it >= overflow_at else [0, 0, 0]
            res["corners"][c] = dict(arr=str(pd / ("arr_%s.txt" % c)), overflow=ov)
        calls.append(("route", d.name, kit))
        return res
    monkeypatch.setattr(RQ, "_build", build)
    monkeypatch.setattr(RQ, "_routed", routed)
    return calls


def test_routed_loop_converges_with_cap2_only_on_capped_leaves(tmp_path, monkeypatch):
    calls = _stubs(monkeypatch)
    out = tmp_path / "rq"
    rc = RQ.main(["plan.json", str(out), "--routed", "KIT", "--iters", "6", "--stop-ps", "2", "--cap2-um", "2000",
                  "--ndr", "4w", "--wide-levels", "10"])
    rq = json.loads((out / "regeq.json").read_text())
    h = [r for r in rq["history"] if "TT" in r]
    assert rc == 0 and h[0]["TT"]["spread"] == 170.5 and h[-1]["TT"]["spread"] <= 2.0, [r["TT"] for r in h]
    assert all(r["overflow"] == {"TT": [0, 0, 0], "FF": [0, 0, 0]} for r in h)
    assert all(c[2] == "KIT" for c in calls if c[0] == "route")
    pads = json.loads((out / ("leafpad%d.json" % h[-1]["it"])).read_text())
    assert 1500.0 < pads["n10_3"] <= 2000.0 and max(v for k, v in pads.items() if k != "n10_3") <= 1500.0
    # model SPEFs are dropped in routed mode; only the best iteration keeps its routed SPEFs
    assert not list(out.glob("it*/ctree.spef"))
    keep = {p.parts[-4] for p in out.glob("it*/routed/**/*.spef")}
    assert keep == {"it%d" % rq["best_it"]}


def test_routed_loop_without_cap2_stalls_at_the_cap(tmp_path, monkeypatch):
    _stubs(monkeypatch)
    out = tmp_path / "rq"
    RQ.main(["plan.json", str(out), "--routed", "KIT", "--iters", "8", "--stop-ps", "2"])
    h = [r for r in json.loads((out / "regeq.json").read_text())["history"] if "TT" in r]
    assert h[-1]["TT"]["spread"] > 15.0 and h[-1].get("stop") == "no gain"           # 830 + 150 < 990: 1500 um cap


def test_routed_overflow_stops_the_loop(tmp_path, monkeypatch):
    _stubs(monkeypatch, overflow_at=1)
    out = tmp_path / "rq"
    RQ.main(["plan.json", str(out), "--routed", "KIT", "--iters", "6", "--stop-ps", "2", "--cap2-um", "2000"])
    h = json.loads((out / "regeq.json").read_text())["history"]
    assert h[-1]["it"] == 1 and h[-1]["stop"].startswith("routed overflow")


def test_start_pad_and_total_pad_abort(tmp_path, monkeypatch):
    calls = _stubs(monkeypatch)
    sp = tmp_path / "sp.json"
    sp.write_text(json.dumps({"n10_3": 100.0}))
    out = tmp_path / "rq"
    rc = RQ.main(["plan.json", str(out), "--routed", "KIT", "--start-pad", str(sp), "--max-leafpad-m", "0.0005"])
    assert calls[0] == ("build", "it0", {"n10_3": 100.0})
    h = json.loads((out / "regeq.json").read_text())["history"]
    assert rc == 2 and "abort" in h[-1] and "leaf pad" in h[-1]["abort"]


def test_route_step_combo_and_overflow(tmp_path):
    import dieclock_route_step as RS
    log = tmp_path / "g.log"
    log.write_text("Layer Resource Demand Usage (%) Max H / Max V / Total Congestion\n"
                   "Total        1379710619       4847160            0.35%             0 /  2 /  2\n")
    assert RS.overflow(log) == [0, 2, 2]
    K, C, O = tmp_path / "kit", tmp_path / "clk", tmp_path / "o"
    (K / "grt").mkdir(parents=True)
    C.mkdir()
    (K / "grt" / "route.v").write_text("module die_route (a, b);\n  input a;\n  output b;\n  assign b = a;\nendmodule\n")
    (K / "grt" / "grt.tcl").write_text("read_verilog /work/grt/route.v\nlink_design die_route\nsource /work/grt/obs.tcl\n")
    (C / "ctree.v").write_text("module ctree (root, t_x);\n  input root;\n  output t_x;\n  wire w_n0;\n"
                               "  BUFx24_ASAP7_75t_R n0 (.A(root), .Y(w_n0));\n"
                               "  HB4xp67_ASAP7_75t_R lh_n0 (.A(w_n0), .Y(t_x));\nendmodule\n")
    (C / "ctree_ck89.tcl").write_text("place_pin -pin_name root -layer M9 -location {1 2} -pin_size {0.04 0.32}\n"
                                      "place_inst -name n0 -location {5 5} -status PLACED\n")
    r = RS.combo(str(K), str(C), str(O), "TT", ndr_src="/out/ndr.tcl")
    v, t = (O / "combo.v").read_text(), (O / "combo.tcl").read_text()
    assert r["insts"] == 1 and "HB4xp67_ASAP7_75t_R ck_lh_n0 (.A(ck_w_n0), .Y(t_x));" in v
    assert "link_design die_combo" in t and "place_inst -name ck_n0" in t
    assert t.index("source /out/ndr.tcl") < t.index("global_route") and t.count("estimate_parasitics -global_routing\n") == 1
