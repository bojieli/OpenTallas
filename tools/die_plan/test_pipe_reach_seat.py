import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipe_reach_seat as PR

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def _plan(tmp):
    pins = {"pins": [{"name": f"n_y[{b}]", "x": 0.0, "y": 500.0 + b} for b in range(4)] +
                    [{"name": f"n_a[{b}]", "x": 0.0, "y": 500.0 + b} for b in range(4)] +
                    [{"name": f"tap[{b}]", "x": 400.0, "y": 300.0 + b} for b in range(4)]}
    (tmp / "pins.json").write_text(json.dumps(pins))
    core = lambda inst, x, y: {"inst": inst, "origin_um": [x, y], "outline_um": [400.0, 1000.0], "orient": "R0",
                               "pins_file": "pins.json", "module": "a0"}
    t = {"outline_um": [1000.0, 2300.0], "hard_cores": [core("u_t00", 60.0, 60.0), core("u_t01", 60.0, 1200.0)],
         "relay_sites": {"u_d4_u_t_0_0_n_y.r[0][0]": [250.0, 700.0]}}          # a buried old seat
    return {"partition_types": {"cbx": t}}


def _run(tmp, D, extra=None):
    plan = _plan(tmp)
    (tmp / "plan.json").write_text(json.dumps(plan))
    topo = {"cbx": [{"inst": f"u_d{D}_u_t_0_0_n_y", "W": 4, "D": D, "src": "u_u_t_0_0.n_y",
                     "cons": ["u_pc_nk_u_t_0_1_n_a", "u_cland_collect_rst_root_n.d"]}]}
    kseg = {"cbx": {f"u_d{D}_u_t_0_0_n_y": [[f"u_d{D}_u_t_0_0_n_y", D, 0, 4]]}}
    (tmp / "topo.json").write_text(json.dumps(topo))
    (tmp / "kitseg.json").write_text(json.dumps(kseg))
    args = [str(tmp / "plan.json"), str(tmp / "kitseg.json"), str(tmp / "topo.json"), str(tmp), str(tmp / "out")]
    assert PR.main(args) == 0
    return (json.loads((tmp / "out" / "cbx" / "pipereach_sites.json").read_text()),
            json.loads((tmp / "out" / "report.json").read_text())["cbx"])


def test_pipe_seated_on_street_route_all_hops_in_reach(tmp_path):
    sites, rep = _run(tmp_path, 4)
    pr = rep["pipes"]["u_d4_u_t_0_0_n_y"]
    assert pr["bucket"] == "ok" and pr["bits_over"] == 0 and pr["buried"] == 0
    assert len(sites) == 4 * 4                                           # r[0..2] + q for 4 bits
    assert "u_d4_u_t_0_0_n_y.q[3]" in sites and "u_d4_u_t_0_0_n_y.r[2][0]" in sites
    bx = PR.grown(_plan(tmp_path)["partition_types"]["cbx"], 6.0)
    for b in range(4):
        ch = [(60.0, 560.0 + b)] + [sites[f"u_d4_u_t_0_0_n_y.r[{j}][{b}]"] for j in range(3)] + \
             [sites[f"u_d4_u_t_0_0_n_y.q[{b}]"]] + [(60.0, 1700.0 + b)]
        assert all(L1(ch[i], ch[i + 1]) <= 405.0 for i in range(len(ch) - 1))
        assert not any(PR.inside(p, bx) for p in ch[1:-1])
    assert len({tuple(v) for v in sites.values()}) == len(sites)          # no duplicate seats


def test_short_pipe_reports_needed_stages(tmp_path):
    _sites, rep = _run(tmp_path, 1)
    pr = rep["pipes"]["u_d1_u_t_0_0_n_y"]
    assert pr["route_um"] > 2 * 405.0 - 300 and pr["need_extra"] >= 1 and pr["bucket"] == "b"


def test_topology_parses_bound_pipe():
    src = ("module cbx (input clk);\n  ot_dp_dly #(.W(4), .D(4)) u_d4_u_t_0_0_n_y (.clk(clk), .d(w_a), .q(w_b));\n"
           "  a0 u_u_t_0_0 (\n    .n_y(w_a)\n  );\n  lk u_pc_nk_u_t_0_1_n_a (\n    .d(w_b[3:0])\n  );\nendmodule\n")
    r = PR.topology(src)
    assert r == [dict(inst="u_d4_u_t_0_0_n_y", W=4, D=4, src="u_u_t_0_0.n_y", cons=["u_pc_nk_u_t_0_1_n_a.d"])]
