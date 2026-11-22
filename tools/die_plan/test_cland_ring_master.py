"""KV-RINGMAC-R1: cland_ring_master.py reproduces the signed CLAND-MACRO-1 ring masters and binds param_wrap's wrapper."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cland_ring_master as C  # noqa: E402
import param_wrap  # noqa: E402

P7 = dict(DEPTH=4, STATUS_REG=1, GUARD_REG=1, WFALL=1, WREG=1, DSREP=8, WRITE_CHUNK=16)


def _p(W, R, **kw):
    p = dict(W=W, **P7, RSTREP=R, PLACEREP=1)
    p.update(kw)
    return p


# signed views (signed-export-1114 / kv-plan-r2 d27b hubc_rk): outline + spot pins of the mkmacro output
SIGNED = [
    (_p(145, 7), "ew", [41.04, 37.152], {"d[0]": ("W", 0.042, 4.524), "fclk": ("W", 0.042, 18.348),
                                         "d[144]": ("W", 0.042, 32.556), "q[0]": ("E", 40.998, 3.084),
                                         "clk": ("E", 40.998, 16.908), "fault": ("E", 40.998, 19.98),
                                         "q[144]": ("E", 40.998, 33.996)}),
    (_p(129, 7), "ew", [41.04, 34.128], {}),
    (_p(144, 7), "ew", [41.04, 37.152], {}),
    (_p(175, 7), "ew", [41.04, 43.2], {}),
    (_p(300, 11), "ew", [41.04, 67.824], {}),
    (_p(259, 11), "ns", [46.656, 49.68], {"d[0]": ("S", 4.572, 0.048), "fclk": ("S", 23.148, 0.048),
                                          "t_rst_n": ("S", 23.292, 0.048), "d[258]": ("S", 42.012, 0.048),
                                          "q[0]": ("N", 3.228, 49.632), "rst_xn[10]": ("N", 23.532, 49.632),
                                          "q[258]": ("N", 43.404, 49.632)}),
]


def test_signed_outlines_and_pins():
    for p, o, ol, spots in SIGNED:
        assert C.outline(p, o) == ol, (p["W"], o, C.outline(p, o))
        pj = C.pins("m", p, o)
        by = {x["name"]: x for x in pj["pins"]}
        for n, (f, x, y) in spots.items():
            assert (by[n]["face"], by[n]["x"], by[n]["y"]) == (f, x, y), (p["W"], n, by[n])


def test_full_pin_tables_match_signed_files():
    """when the signed pins.json files are on this host, every pin must match (name, face, x, y, layer, dir)"""
    roots = {(145, "ew"): "/home/ubuntu/signed-export-1114/qwen_kvsys/kv_cland_w145_ew_7d736/pins.json",
             (129, "ew"): "/home/ubuntu/signed-export-1114/qwen_kvsys/kv_cland_w129_ew_0361f/pins.json",
             (144, "ew"): "/home/ubuntu/signed-export-1114/qwen_kvsys/kv_cland_w144_ew_e06e6/pins.json",
             (175, "ew"): "/home/ubuntu/signed-export-1114/qwen_kvsys/kv_cland_w175_ew_e5c30/pins.json"}
    for (W, o), f in roots.items():
        if not Path(f).exists():
            continue
        ref = json.loads(Path(f).read_text())
        p = next(s[0] for s in SIGNED if s[0]["W"] == W and s[1] == o)
        got = C.pins(ref["module"], p, o)
        key = lambda x: (x["name"], x["face"], x["x"], x["y"], x["layer"], x["dir"])  # noqa: E731
        assert sorted(map(key, got["pins"])) == sorted(map(key, ref["pins"])), W
        assert got["outline_um"] == ref["outline_um"]


def test_narrow_rstrep0_has_no_rst_xn_and_wrapper_is_param_wrap(tmp_path):
    p = dict(W=33, DEPTH=4, STATUS_REG=1, GUARD_REG=1, WFALL=1, NARROW=1)
    d, q = C.face_ports(p)
    assert not any(n.startswith("rst_xn") for n in d + q)
    assert len(q) == 33 + 10 and len(d) == 35
    g = dict(master=C.master_name("kv", p, "ew"), params=p, orient="ew", uses=[("u_cland_ft0_i", "E")])
    rk = C.prep(g, tmp_path)
    assert (rk / f"{g['master']}.sv").read_text() == param_wrap.wrapper_sv(g["master"], C.BASE, p)
    spec = json.loads((rk / "spec.json").read_text())
    assert spec["reset_ports"] == ["rst_n", "t_rst_n"]
    cfg = json.loads((rk / "config.json").read_text())
    assert cfg["uses"] == [["kv3_hub_C", "u_bound.u_cland_ft0_i", "MY"]]
    assert cfg["param_text"] == "#(.W(33), .DEPTH(4), .STATUS_REG(1), .GUARD_REG(1), .WFALL(1), .NARROW(1))"
    pl = json.loads((rk / "plan.json").read_text())
    assert pl["partition_types"]["private_cland_child"]["hard_cores"][0]["outline_um"] == C.outline(p, "ew")


def test_scan_select_groups_exact_params_by_face_class():
    sv = """
    ot_dp_clk_landing_cas #(.W(32), .DEPTH(4), .STATUS_REG(1), .GUARD_REG(1), .WFALL(1), .NARROW(1)) u_cland_i_a_vo (
        .fclk(f), .d(x));
    ot_dp_clk_landing_cas #(.W(32), .DEPTH(4), .STATUS_REG(1), .GUARD_REG(1), .WFALL(1), .NARROW(1)) u_cland_i_b_vo (
        .fclk(f), .d(x));
    ot_dp_clk_landing_cas #(.W(32), .DEPTH(4), .STATUS_REG(1), .GUARD_REG(1), .WFALL(1), .NARROW(1)) u_cland_i_c_vo (
        .fclk(f), .d(x));
    ot_dp_clk_landing_cas #(.W(2), .DEPTH(4), .STATUS_REG(1), .GUARD_REG(1), .WFALL(1), .NARROW(1), .LITE(1)) u_cland_l (
        .fclk(f));
    ot_dp_clk_landing_cas #(.W(145), .DEPTH(4), .WREG(1), .RSTREP(7), .NARROW(1)) u_cland_i_h (.fclk(f));
    """
    faces = {"i_a_vo": {"N"}, "i_b_vo": {"S"}, "i_c_vo": {"E"}, "l": {"W"}, "i_h": {"W"}}
    gs = C.select(C.scan(sv), faces)
    got = {(g["params"]["W"], g["orient"]): sorted(i for i, _ in g["uses"]) for g in gs}
    assert got == {(145, "ew"): ["u_cland_i_h"], (32, "ns"): ["u_cland_i_a_vo", "u_cland_i_b_vo"],
                   (32, "ew"): ["u_cland_i_c_vo"]}
    assert len({g["master"] for g in gs}) == 3
    assert C.select(C.scan(sv), faces, widths={145})[0]["params"]["RSTREP"] == 7


def test_master_name_depends_on_params_and_orient():
    a = C.master_name("kv", _p(145, 7), "ew")
    assert a.startswith("kv_cland_w145_ew_")
    assert a != C.master_name("kv", _p(145, 7, NARROW=1), "ew")
    assert a != C.master_name("kv", _p(145, 7), "ns")
