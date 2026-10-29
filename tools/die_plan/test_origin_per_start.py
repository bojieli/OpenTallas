"""A static tree selector must not mix independent ring STARTs at a sampler D pin."""
from clock_landings import Landings
from clock_landing_verify import Verification
from types import SimpleNamespace
from test_face_guard import _X, _rs, _rs_net


def origin_body(buses=("hd_i", "hu_i"), root=False):
    obj = Landings.__new__(Landings)
    obj.reset_placements = {}
    extra = []
    logic, raw = obj._origin_strap_rtl(
        "spn", ("strap", list(buses), 2, 40, root),
        {b: f"raw_{i}" for i, b in enumerate(buses)}, extra, lambda _: "root_raw")
    return "\n".join(logic), extra, raw, obj.reset_placements


def test_each_start_is_sampled_before_static_selection():
    body, extra, _, metadata = origin_body()
    assert body.count("ot_dp_landing_origin_s #") == 2
    assert ".rst_raw_n(raw_0), .p_start(cland_fstart_in_hd_i)" in body
    assert ".rst_raw_n(raw_1), .p_start(cland_fstart_in_hu_i)" in body
    assert "assign cland_start = (strap_ca_tsel == 1'd0) ? cland_start_t0 : cland_start_t1;" in body
    assert "cland_pstart" not in body
    assert metadata["spn"]["count_origin"]["per_bus_origins"] == ["u_cland_origin_t0", "u_cland_origin_t1"]


def test_single_bus_keeps_existing_origin_and_root_selection():
    body, _, raw, metadata = origin_body(buses=("hd_i",), root=True)
    assert "u_cland_origin (" in body and "u_cland_origin_t" not in body
    assert ".rst_raw_n(raw_0), .p_start(cland_fstart_in_hd_i)" in body
    assert "assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;" in body
    assert raw == "cland_raw_sel" and "per_bus_origins" not in metadata["spn"]["count_origin"]


def test_invalid_selector_retains_last_bus_fallback():
    body, extra, _, _ = origin_body(buses=("a", "b", "c"))
    assert "    input wire [1:0] strap_ca_tsel" in extra
    assert "assign cland_start = (strap_ca_tsel == 2'd0) ? cland_start_t0 : (strap_ca_tsel == 2'd1) ? cland_start_t1 : cland_start_t2;" in body


def test_graph_verifier_follows_static_selected_sampler_and_legacy_form():
    v = Verification.__new__(Verification)
    v.table = {"count_aligned": {"strap_form": True}}
    v.parts = {"p": {"type": "B"}}
    v._strap = {"types": {"B": {"origin": {"tree_buses": ["a", "b", "c"]}}},
                "instances": {"p": {"values": {"strap_ca_tsel": 1}}}}
    v.F = SimpleNamespace(cells=[SimpleNamespace(path="p.u_cland_origin_t0"),
                               SimpleNamespace(path="p.u_cland_origin_t1"),
                               SimpleNamespace(path="p.u_cland_origin_t2")])
    assert v._origin_path("p") == "p.u_cland_origin_t1"
    v._strap["instances"]["p"]["values"]["strap_ca_tsel"] = 3
    assert v._origin_path("p") == "p.u_cland_origin_t2"
    v.F.cells = [SimpleNamespace(path="p.u_cland_origin")]
    assert v._origin_path("p") == "p.u_cland_origin"


def _forwarded_multistart(wrong_selected_origin=False):
    """Actual kept-module graph: two independent origins and one forwarded START face flop."""
    v = Verification.__new__(Verification)
    v.table = {"count_aligned": {"strap_form": True}}
    v.parts = {"p": {"type": "B"}}
    v.region = {"p": "r1"}
    v._strap = {"types": {"B": {"origin": {"tree_buses": ["a", "b"]}}},
                "instances": {"p": {"values": {"strap_ca_tsel": 1}}}}
    cells = [SimpleNamespace(path=f"p.u_cland_origin_t{i}", module="ot_dp_landing_origin_s", kind="opaque",
                             ports={"clk": [1], "rst_raw_n": [2], "start_d": [4+i], "start": [6+i]})
             for i in range(2)]
    cells.append(SimpleNamespace(path="p.u_cland_fstart_x", module="ot_dp_landing_relay",
                                 ports={"clk": [1], "rst_raw_n": [2],
                                        "d": [4 if wrong_selected_origin else 5], "q": [8]}))
    v.F = SimpleNamespace(cells=cells)
    v.G = SimpleNamespace(drv={4: [(0, "start_d", 0)], 5: [(1, "start_d", 0)], 8: [(2, "q", 0)]},
                          top_in={1: ("clk_region_r1", 0), 2: ("raw_reset", 0)})
    v.byname = {c.path: c for c in cells}
    v.checks = 0
    v.memo = {}
    v.errors = []
    v.expected = set()
    v._fstart_checked = set()
    assert v.fstart_net("p", "x") == ("pin", "p.u_cland_fstart_x", "q", 0)
    return v.errors


def test_forwarded_start_verifies_selected_origin_and_catches_wrong_d():
    assert _forwarded_multistart() == []
    bad = _forwarded_multistart(wrong_selected_origin=True)
    assert len(bad) == 1 and "u_cland_fstart_x.d:" in bad[0]


def _two_start_net(shared=False):
    net = _rs_net(extra_in="st2", top_extra=["ot_ring u_cland_d2 (.fclk(fclk), .d(d2), .st(st2));"],
                  outs="")
    # Add a second landing input with its own writer and origin; both origins use the same local clock.
    net = net.replace("input st2;", "input st2; input d2;").replace("rst_n, st2);", "rst_n, st2, d2);")
    if shared:
        net = net.replace(".st(st), .efall", ".st(mixed_start), .efall")
        net = net.replace(" ot_origin u_cland_origin", f" AND2x2{_X} mix (.A(st), .B(st2), .Y(mixed_start));\n ot_origin u_cland_origin")
    else:
        net = net.replace("u_cland_origin (", "u_cland_origin_t0 (")
        at = net.rfind("endmodule")
        net = net[:at] + " ot_origin u_cland_origin_t1 (.clk(clk), .st(st2), .efall(strap_efall), .rq(rq));\n" + net[at:]
    return net


def test_face_guard_separate_origins_pass_and_shared_origin_mutant_fails():
    land = {"d": {"D": 4, "form": "hold_mux"}, "d2": {"D": 4, "form": "hold_mux"},
            "st": {"form": "ring_start", "ring": "d"}, "st2": {"form": "ring_start", "ring": "d2"}}
    good = _rs(_two_start_net(), land=land)
    assert good["verdict"] == "PASS", good["fails"]
    assert good["ring_start"]["st"]["sampler_flops"] == ["u_cland_origin_t0/s0", "u_cland_origin_t0/sf"]
    assert good["ring_start"]["st2"]["sampler_flops"] == ["u_cland_origin_t1/s0", "u_cland_origin_t1/sf"]
    bad = _rs(_two_start_net(shared=True), land=land)
    assert bad["verdict"] == "FAIL" and "land_slot" in bad["fail_counts"]
