"""DIE-HBM-89 11-07: component proof reads the bind's recorded core-reset leaf (bind_core_resets.json), and the HBM
d44v as-built t13 maps the PART 34/38 sub-core parents to their composed as-built leaves."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind_component as BC  # noqa: E402

RTL = """module t (input wire clk, input wire arst_n);
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));
    wire rst_n_t0;
    wire rst_n_t1;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_n_t0));
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_root_n), .q(rst_n_t1));
    wire rst_n = rst_n_t0;
    leafm u_u_par_q0 (
        .clk(clk),
        .arg_rst_n(%s)
    );
endmodule
"""
META = {"types": {"t": {"entry": "relayed", "entry_stages": 1, "relays": 2, "depth_K": 1, "release_after_pin": 2,
                        "core_resets": [{"inst": "u_par__q0__arg", "pin": "rst_n", "tap": 0},
                                        {"inst": "u_par__q0__link0", "pin": "rst_n", "tap": 1}]}}}
BOUND = {"t": [{"inst": "u_par__q0__arg", "leaf": "u_u_par_q0", "pin": "arg_rst_n", "reset": "rst_n_t0"},
               {"inst": "u_par__q0__link0", "leaf": "u_u_par_q0", "pin": "arg_rst_n", "reset": "rst_n_t0"}]}


def run(conn, bound):
    errors = []
    rep = BC._reset(RTL % conn, "t", META, errors, 2, bound)
    return errors, rep


def test_recorded_shared_leaf_passes():
    errors, rep = run("rst_n_t0", BOUND)
    assert errors == [], errors
    assert [c["inst"] for c in rep["consumers"]] == ["u_u_par_q0", "u_u_par_q0"]


def test_recorded_leaf_wrong_net_fails():
    errors, _ = run("rst_n", BOUND)          # the type reset alias, not the recorded tap
    assert any("reset differs from recorded" in e for e in errors), errors


def test_recorded_leaf_must_exist():
    bound = {"t": [dict(BOUND["t"][0], leaf="u_u_missing"), BOUND["t"][1]]}
    errors, _ = run("rst_n_t0", bound)
    assert any("u_u_missing: expected one native reset leaf" in e for e in errors), errors


def test_without_record_plan_name_unchanged():
    errors, _ = run("rst_n_t0", None)
    assert sum("expected one native reset leaf" in e for e in errors) == 2, errors


def test_hbm_t13_manifest():
    root = HERE.parent.parent
    d = root / "physical/die_plan/hbm/bind/d44v"
    a = json.loads((d / "asbuilt_t13.json").read_text())
    base = (d / a["base"]).resolve()
    assert base == root.resolve()
    for f in a["netlist"] + a["files"]:
        assert (base / f).is_file(), f
    assert (d / a["map_file"]).is_file()
    comp = base / a["compose"]
    assert comp.is_file() or comp.with_name(comp.name + ".gz").is_file()
    scl = a["sub_core_leaf"]
    assert scl["u_sfucore_Q_ctl"] == "u_sfucore_Q_ctl"
    assert scl["u_hb_coll_Q_edge__q0"] == "hb_coll_NW.__cut_edge"
    assert scl["u_hb_coll_Q_body_core__q0"] == "hb_coll_NW.__cut_body"
    assert set(a["sub_core_leaf_pin"].values()) == {"arg_rst_n"}
    assert not any("results/die_hbm_1027" in json.dumps(v) for v in (a["files"], a["prefer"]))


def test_bind_reads_asbuilt_sub_core_leaf_pin():
    src = (HERE / "bind.py").read_text()
    assert '(self.ab.get("sub_core_leaf_pin") or {}).get(target["inst"], pin)' in src
    assert '"bind_core_resets.json"' in src
