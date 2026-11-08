"""EP-MOD-1108: NW_io endpoints declare the as-built modules with port-exact pin tables."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delta_ep_mod_1108 as D

BASE_HDR = """module hfd_ep_static #(parameter integer IDLE_K = 204) (
    input  wire clk, input wire rst_n, input wire [3:0] tx_frame, output wire [3:0] rx_pin_flit,
    output wire [1:0] sd_tx, input wire [1:0] sd_rx, input wire [1:0] sd_st, output reg fault
);"""
VC_HDR = """module hfd_ep_static_vc2 #(parameter integer IDLE_K = 204, parameter integer HQ = 4) (
    input  wire clk, input wire rst_n, input wire [3:0] tx_frame, output wire [3:0] rx_pin_flit,
    output reg fault,
    input wire h_tx_v, input wire [3:0] h_tx_frame, output reg h_rx_v, output reg [3:0] h_rx_frame,
    output reg h_up, output reg [2:0] h_cause,   // comment
    output wire [1:0] sd_tx, input wire [1:0] sd_rx, input wire [1:0] sd_st
);
endmodule
module hfd_ep_host_vc #(parameter integer MUT = 0) (
    input  wire clk, input wire rst_n, input wire [3:0] tx_frame, output wire [3:0] rx_pin_flit,
    output reg fault,
    output reg vc_tx_v, output reg [3:0] vc_tx_frame, input wire vc_rx_v, input wire [3:0] vc_rx_frame,
    input wire vc_up, input wire [2:0] vc_cause
);"""
W, H = 60.0, 40.0


def base_pins():
    pins = [dict(name="clk", layer="M5", x=30.024, y=20.0), dict(name="rst_n", layer="M5", x=10.008, y=0.096),
            dict(name="fault", layer="M5", x=20.04, y=H - 0.096)]
    pins += [dict(name=f"tx_frame[{i}]", layer="M4", x=0.096, y=5.0 + i) for i in range(4)]
    pins += [dict(name=f"rx_pin_flit[{i}]", layer="M4", x=W - 0.096, y=5.0 + i) for i in range(4)]
    pins += [dict(name=f"{n}[{i}]", layer="M5", x=40.008 + 0.192 * (2 * k + i), y=0.096)
             for k, n in enumerate(("sd_tx", "sd_rx", "sd_st")) for i in range(2)]
    return pins


def plan():
    hc = lambda inst, o: dict(inst=inst, module=D.BASE, origin_um=o, outline_um=[W, H], pins_file="cores/ep.json",
                              obs_max="M5")
    t = dict(hard_cores=[hc("u_ep_N0", [100.0, 100.0]), hc("u_host_ep", [117.28, 200.0])],
             contents=[dict(inst="u_ep_N0", module=D.BASE), dict(inst="u_host_ep", module=D.BASE)],
             clock=dict(taps=[dict(name="u_ep_N0", budget_owner=D.BASE), dict(name="u_host_ep.clk", budget_owner=D.BASE),
                              dict(name="u_other", budget_owner="x")]))
    other = dict(hard_cores=[hc("u_ep_N2", [0, 0])], contents=[dict(inst="u_ep_N2", module=D.BASE)])
    return dict(die={}, partition_types={"NW_io": t, "NE_io": other})


def run(p=None):
    ports = lambda m, txt: D.module_ports(txt, m)
    return D.apply(p or plan(), base_pins(), ports("hfd_ep_static_vc2", VC_HDR), ports("hfd_ep_host_vc", VC_HDR),
                   ports(D.BASE, BASE_HDR))


def test_modules_pins_and_only_nw_io_change():
    p = plan()
    new, tables, ch = run(p)
    t = new["partition_types"]["NW_io"]
    assert {h["inst"]: h["module"] for h in t["hard_cores"]} == D.SWAP
    assert {c["inst"]: c["module"] for c in t["contents"]} == D.SWAP
    assert [tp["budget_owner"] for tp in t["clock"]["taps"]] == ["hfd_ep_static_vc2", "hfd_ep_host_vc", "x"]
    assert D.changed_types(p, new) == (["NW_io"], [])
    assert p["partition_types"]["NW_io"]["hard_cores"][0]["module"] == D.BASE          # input untouched
    for h in t["hard_cores"]:
        assert h["outline_um"] == [W, H] and h["pins_file"].endswith("__epmod1108.json")
    vc2, host = tables["hfd_ep_static_vc2"], tables["hfd_ep_host_vc"]
    assert len(vc2) == len(base_pins()) + 1 + 4 + 1 + 4 + 1 + 3
    assert not any(p_["name"].startswith("sd_") for p_ in host)
    keep = {q["name"]: q for q in base_pins()}
    for q in vc2:                                 # shared pins keep their site
        if q["name"] in keep:
            assert q == keep[q["name"]]
    hv = {q["name"]: q for q in host}
    dx = 17.28
    for a, b in D.PAIRS:                          # VC1 pairs: same die x, ep N face / host S face
        for q in vc2:
            if q["name"].split("[")[0] == a:
                r = hv[q["name"].replace(a, b, 1)]
                assert q["y"] == pytest.approx(H - 0.096) and r["y"] == pytest.approx(0.096)
                assert q["x"] - dx == pytest.approx(r["x"])
                assert round(q["x"] / 0.048 - 0.5, 6) % 1 == 0     # pin lattice 0.024 + k 0.048


def test_port_mismatch_fails_closed():
    bad = VC_HDR.replace("output reg h_up,", "output reg h_up, output reg h_extra,")
    with pytest.raises(ValueError, match="vc2 ports"):
        D.apply(plan(), base_pins(), D.module_ports(bad, "hfd_ep_static_vc2"), D.module_ports(VC_HDR, "hfd_ep_host_vc"),
                D.module_ports(BASE_HDR, D.BASE))


def test_already_applied_or_other_module_fails_closed():
    new, _, _ = run()
    with pytest.raises(ValueError, match="is not hfd_ep_static"):
        run(new)


def test_side_files():
    ce = {"NW_io": {"u_ep_N0": dict(module=D.BASE), "u_host_ep": dict(module=D.BASE)}, "NE_io": {"u_ep_N2": dict(module=D.BASE)}}
    cm = dict(cores={D.BASE: dict(status="KNOWN", macros=[1])})
    ccr = dict(modules={D.BASE: dict(instances=6)})
    ce2, cm2, ccr2, _ = D.side_files(ce, cm, ccr)
    assert ce2["NW_io"]["u_ep_N0"]["module"] == "hfd_ep_static_vc2" and ce2["NE_io"] == ce["NE_io"]
    assert cm2["cores"]["hfd_ep_host_vc"]["macros"] == [1] and cm2["cores"]["hfd_ep_host_vc"]["status"] == "KNOWN"
    assert ccr2["modules"][D.BASE]["instances"] == 4 and ccr2["modules"]["hfd_ep_static_vc2"]["instances"] == 1
    assert ccr["modules"][D.BASE]["instances"] == 6
