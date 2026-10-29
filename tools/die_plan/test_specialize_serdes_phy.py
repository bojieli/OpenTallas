import json
from pathlib import Path

import pytest

import specialize_serdes_phy as S


def provider(name, width="W", parameter=True):
    param = "#(parameter integer W=522)" if parameter else ""
    return f"""(* blackbox *)
module {name} {param} (
 input wire clk, rst_n, output wire tx_up, input wire tx_v,
 input wire [{width}-1:0] tx_flit, output wire rx_v,
 output wire [{width}-1:0] rx_flit);
endmodule
"""


def fixture(tmp, width=522):
    kit, views = tmp / "kit", tmp / "views"
    kit.mkdir(); views.mkdir()
    bound = kit / "bound.sv"
    bound.write_text(f"module bound;\n {S.WRAPPER} #(.W({width})) u_core ( );\nendmodule\n")
    raw = kit / "raw_bb.v"
    raw.write_text(provider(S.LOGICAL))
    for w in (521, 522):
        master = S.LOGICAL + f"_w{w}"
        d = views / master; d.mkdir()
        (d / f"{master}_bb.v").write_text(provider(master, str(w), False))
        for suffix in (".lef", "_tt.lib", "_ff.lib"):
            (d / (master + suffix)).write_text("modeled fixture")
    (kit / "kit_rtl.json").write_text(json.dumps(dict(bound_module="bound", files=[str(bound), str(raw)], hard_macros={})))
    return kit, views, raw


def test_exact_width_dispatcher_preserves_original_source_and_publishes_real_master(tmp_path):
    kit, views, raw = fixture(tmp_path, 521)
    original = raw.read_bytes()
    record = S.specialize(kit, views)
    assert raw.read_bytes() == original
    assert record["parameters"] == {"W": 521}
    assert record["physical_master"].endswith("_w521")
    assert record["expected_physical_instance"] == "u_bound.u_core.u_phy.g_native.u_macro"
    assert record["added_cycles"] == record["added_state"] == 0
    man = json.loads((kit / "kit_rtl.json").read_text())
    assert list(man["hard_macros"]) == [record["physical_master"]]
    assert S.header_ports(S.dispatcher(521, record["physical_master"]), S.LOGICAL, 521) == S.ports(521)


def test_wrong_parameter_is_rejected_before_kit_mutation(tmp_path):
    kit, views, _ = fixture(tmp_path, 520)
    with pytest.raises(ValueError, match="literal W"):
        S.specialize(kit, views)
    assert not (kit / "physical_specialization").exists()


def test_wrong_physical_port_width_is_rejected_before_kit_mutation(tmp_path):
    kit, views, _ = fixture(tmp_path)
    master = S.LOGICAL + "_w522"
    p = views / master / f"{master}_bb.v"
    p.write_text(p.read_text().replace("[522-1:0] tx_flit", "[521-1:0] tx_flit"))
    with pytest.raises(ValueError, match="ABI differs"):
        S.specialize(kit, views)
    assert not (kit / "physical_specialization").exists()
