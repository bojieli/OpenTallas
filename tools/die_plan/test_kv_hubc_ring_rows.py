import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import kv_hubc_ring_rows as R

RTL = """
 ot_dp_clk_landing_cas #(.W(300), .DEPTH(4), .STATUS_REG(1), .PLACEREP(1)) u_cland_ft14_i (.x(a));
 ot_dp_clk_landing_cas #(.W(33), .DEPTH(4), .STATUS_REG(1)) u_cland_ft0_i (.x(a));
 ot_dp_clk_landing_cas #(.W(523), .DEPTH(4)) u_cland_i_dNd_kv_srx (.x(a));
"""


def mk(tmp, params, axis, name):
    d = os.path.join(tmp, name); os.makedirs(d)
    json.dump(dict(params=params, orient=axis), open(d + "/config.json", "w"))
    json.dump(dict(outline_um=[60.0, 40.0], pins=[]), open(d + "/pins.json", "w"))


def plan():
    return dict(partition_types={"T": dict(outline_um=[1000.0, 800.0], hard_cores=[dict(origin_um=[400, 300], outline_um=[200, 200])])})


def test_parse_and_filter():
    r = R.parse_rings(RTL)
    assert [x[2]["W"] for x in r] == [300, 33, 523]


def test_rows_ok_and_no_master_and_no_pin():
    with tempfile.TemporaryDirectory() as tmp:
        mk(tmp, dict(W=300, DEPTH=4, STATUS_REG=1, PLACEREP=1), "ew", "kv_cland_w300_ew_x")
        res = R.rows(plan(), R.parse_rings(RTL), "T", R.load_masters(tmp),
                     {"ft14_i": [1000.0, 100.0], "i_dNd_kv_srx": [0.0, 500.0]})
        st = {r["inst"]: r for r in res}
        assert len(res) == 2                                   # W 33 is under min-w
        a = st["u_cland_ft14_i"]
        assert a["status"] == "OK" and a["face"] == "E" and a["orient"] == "MY"
        o = a["origin_um"]; assert 8.64 <= o[0] and o[0] + 60 <= 1000 - 8.64
        assert not R.hit((o[0], o[1], o[0] + 60, o[1] + 40), (396, 296, 604, 504))   # clear of the hard core + halo
        assert st["u_cland_i_dNd_kv_srx"]["status"] == "NO_MASTER"
        p = R.apply(plan(), "T", res)
        hc = p["partition_types"]["T"]["hard_cores"]
        assert len(hc) == 2 and hc[1]["physical_inst"] == "u_bound.u_cland_ft14_i" and hc[1]["param_wrap"]["params"]["W"] == 300


def test_no_pin():
    res = R.rows(plan(), R.parse_rings(RTL), "T", {}, {})
    assert {r["status"] for r in res} == {"NO_PIN"}
