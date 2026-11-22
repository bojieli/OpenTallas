import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("head_lep_parts_delta", Path(__file__).with_name("head_lep_parts_delta.py"))
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

P = {"CH_B": "4'b1111", "PAIR": 1, "KTX": "16'h1111", "KRX": "16'h2660", "TXI": "16'h2442", "PIN": 6, "POUT": 8,
     "RXH": 1, "KCRED": 28, "KTR": "16'h3112", "RFAN": 5}


def plan():
    groups = [dict(prefix=p, rect_um=[1, 1, 2, 2], tag="stage:a", match="cell") for p in (
        r"u_core\.u\.g_kl\\\[1\\\]\.g_rxf\.g_s\\\[2\\\][/.].*", r"u_core\.u\.g_kl\\\[1\\\]\.g_rxf\.g_s\\\[3\\\][/.].*",
        r"u_core\.u\.g_kl\\\[2\\\]\.g_rxr\.g_s\\\[2\\\][/.].*", r"u_core\.u\.g_kl\\\[2\\\]\.g_rxr\.g_s\\\[3\\\][/.].*",
        r"u_core\.u\.g_kl\\\[0\\\]\.g_txf\.g_s\\\[0\\\][/.].*", r"u_core\.u\.g_pin\.g_s\\\[0\\\][/.].*",
        r"u_core\.u\.u_lep\.u\.g_tx\\\[3\\\]\.g_txi\.g_s\\\[0\\\][/.].*", r"u_core\.u\.g_plw\.g_s\\\[0\\\][/.].*")]
    t = dict(contents=[dict(inst="u_core", module="ot_s81hd_lep0N_noidx_core", params=dict(P), bind={"ck": "clk", "rst_n": "rst_n"})],
             buses=[dict(name=n, leaf="u_core." + n) for n in ("coll_i0", "coll_o0", "coll_i1", "coll_o3", "lepk_i0", "fault_o0", "lw_o")],
             hard_cores=[dict(inst="u_core.u.g_pp[2].u_pair"), dict(inst="u_core.u.u_lep.u.g_tx[1].g_safe_write.u_m.g_bank[0].u_m"),
                         dict(inst="u_core.u.u_lep.u.g_rx[1].g_sa.g_true_sram.u_rx_mem.g_bank[0].u_m")],
             internal_stations=[dict(conn="bus:coll_i0", capture="u_core.coll_i0"), dict(conn="bus:coll_o3", launch="u_core.coll_o3")],
             relay_sites={"u_core.u.g_rfan.u_rfan.g_root.root_r": [1, 1]},
             clock=dict(taps=[dict(name="u_core.u.g_pp[2].u_pair.clk", kind="core")],
                        tap_group=dict(re=r"(u_core\.u\.u_lep\.u\.g_tx\\?\[[0-3]\\?\]\.g_safe_write\.u_m|u_core\.u\.g_plw\.g_s)"),
                        landing_contract=dict(native_stage_groups=dict(schema="opentallas.native_stage_groups.v1", content="u_core",
                                                                       module="ot_s81hd_lep0N_noidx_core", params=dict(P), groups=groups))))
    return dict(partition_types=dict(hd_lep0N=t))


def test_six_contents_nets_and_every_carried_path_renamed():
    out, rep = D.delta(plan())
    t = out["partition_types"]["hd_lep0N"]
    assert [c["inst"] for c in t["contents"]] == ["u_core", "u_io", "u_rg0", "u_rg1", "u_rg2", "u_rg3"]
    assert t["contents"][0]["module"] == "ot_s81hd_lep0N_noidx_hub" and t["contents"][0]["params"]["RXA"] == "16'h0330"
    assert t["contents"][3]["params"] == dict(K=1, CHB="1'b1", KCRED=28, IDX_EN=0, TXI="16'h2442", RXH=1, KT=1, KQ=1, KR=6, RA=3, RV=1)
    use = Counter(v for c in t["contents"] for v in c["bind"].values() if v.startswith("net:"))
    assert set(use) == {"net:" + n["name"] for n in t["nets"]} and set(use.values()) == {2}       # whole two-leaf nets
    assert set(rep["net_drivers"]) == {n["name"] for n in t["nets"]}
    assert [b["leaf"] for b in t["buses"]] == ["u_core.coll_i0", "u_core.coll_o0", "u_rg1.coll_i", "u_rg3.coll_o",
                                               "u_io.lepk_i0", "u_io.fault_o0", "u_core.lw_o"]
    assert [h["inst"] for h in t["hard_cores"]] == ["u_rg2.u_pair", "u_rg1.u_txl.g_tx[1].g_safe_write.u_m.g_bank[0].u_m",
                                                    "u_core.u.u_lep.u.g_rx[1].g_sa.g_true_sram.u_rx_mem.g_bank[0].u_m"]
    assert t["internal_stations"][1]["launch"] == "u_rg3.coll_o" and t["internal_stations"][0]["capture"] == "u_core.coll_i0"
    ck = t["clock"]
    assert ck["taps"][0]["name"] == "u_rg2.u_pair.clk"
    assert ck["tap_group"]["re"] == r"(u_rg[0-3]\.u_txl\.g_tx\\?\[[0-3]\\?\]\.g_safe_write\.u_m|u_core\.u\.g_plw\.g_s)"
    g = ck["landing_contract"]["native_stage_groups"]
    assert g["schema"] == "opentallas.native_stage_groups.v2"
    assert [h["content"] for h in g["contents"]] == ["u_core", "u_io", "u_rg0", "u_rg1", "u_rg2", "u_rg3"]
    # RX K leg of lanes 1, 2 (KR 6, RA 3): forward stages 0..2 and return stages 3..5 live in the region
    assert [r["prefix"] for r in g["groups"]] == [
        r"u_rg1\.g_rxf\.g_s\\\[2\\\][/.].*", r"u_core\.u\.g_kl\\\[1\\\]\.g_rxf\.g_s\\\[3\\\][/.].*",
        r"u_core\.u\.g_kl\\\[2\\\]\.g_rxr\.g_s\\\[2\\\][/.].*", r"u_rg2\.g_rxr\.g_s\\\[3\\\][/.].*",
        r"u_rg0\.g_txf\.g_s\\\[0\\\][/.].*", r"u_io\.u\.g_pin\.g_s\\\[0\\\][/.].*",
        r"u_rg3\.u_txl\.g_tx\\\[3\\\]\.g_txi\.g_s\\\[0\\\][/.].*", r"u_core\.u\.g_plw\.g_s\\\[0\\\][/.].*"]
    json.dumps(out)


def test_base_form_changes_fail_closed():
    for edit, match in ((lambda t: t["contents"][0].__setitem__("module", "x"), "base form changed"),
                        (lambda t: t.__setitem__("nets", [dict(name="a", width=1)]), "base form changed"),
                        (lambda t: t["buses"].append(dict(name="new", leaf="u_core.new")), "bus leaf"),
                        (lambda t: t["relay_sites"].__setitem__("u_core.u.g_pp[0].u_pair.x", [1, 1]), "relay sites in a region")):
        p = plan()
        edit(p["partition_types"]["hd_lep0N"])
        with pytest.raises(ValueError, match=match):
            D.delta(p)
    with pytest.raises(ValueError, match="RXA_i <= KRX_i"):
        D.delta(plan(), "16'h0003")
