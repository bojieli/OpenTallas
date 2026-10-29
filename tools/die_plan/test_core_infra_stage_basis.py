"""DIE-KV-14b opt-in core_tree.stage_basis = "total": a planned macro leaf chain sits at the same TOTAL stage count
(planned node depth + declared CTS-built stages) as the CTS-open register leaves; the default keeps the legacy check.
    python3 -m pytest -q tools/die_plan/test_core_infra_stage_basis.py"""
import copy

import pytest
import core_infra as CI
from test_core_infra import sample


def macro_chain_tree(n_chain=3, cts_stages=2):
    s = sample()
    s["pg_obstructions_um"] = {}
    nodes = [dict(name="br", master="BUFx12f_ASAP7_75t_R", xy_um=[432, 432], parent="port:ck"),
             dict(name="isl", master="BUFx12f_ASAP7_75t_R", xy_um=[216, 432], parent="br")]
    par = "br"
    for k in range(n_chain):
        nodes.append(dict(name=f"mac{k}", master="BUFx24_ASAP7_75t_R", xy_um=[216, 400 + k], parent=par))
        par = f"mac{k}"
    s["core_tree"] = {"clock_port": "ck", "stage_basis": "total", "nodes": nodes,
                      "leaves": [dict(node="isl", sinks=["a/CLK", "b/CLK"], cts_open=True, domain_sinks=7429,
                                      cts_stages=cts_stages),
                                 dict(node=par, sinks=["m0/clk", "m1/clk"], load_class="macro")]}
    return s


def test_total_basis_accepts_equal_total_stage_macro_chain():
    p = CI.compile_slice(macro_chain_tree())["core_tree"]
    assert p["depth"] == 4 and p["cts_open"] == ["isl"] and p["stage_basis"] == "total"
    tcl = CI.emit_tcl(macro_chain_tree())
    assert "ot_ci_tree_open {isl}" in tcl and "ot_ci_tree_sink {mac2} {m0/clk}" in tcl


def test_total_basis_refuses_unequal_or_undeclared_stages():
    with pytest.raises(CI.InfraError, match="unequal stage counts"):
        CI.compile_slice(macro_chain_tree(n_chain=3, cts_stages=3))
    bad = macro_chain_tree(); del bad["core_tree"]["leaves"][0]["cts_stages"]
    with pytest.raises(CI.InfraError, match="cts_stages"):
        CI.compile_slice(bad)
    bad = macro_chain_tree(); bad["core_tree"]["stage_basis"] = "wild"
    with pytest.raises(CI.InfraError, match="stage_basis"):
        CI.compile_slice(bad)


def test_default_basis_is_the_legacy_node_depth_check():
    s = macro_chain_tree(); del s["core_tree"]["stage_basis"]
    with pytest.raises(CI.InfraError, match="unequal stage counts"):
        CI.compile_slice(s)
    s["core_tree"]["leaves"][0].pop("cts_stages")
    s["core_tree"]["nodes"] = s["core_tree"]["nodes"][:2]
    s["core_tree"]["leaves"][1]["node"] = "isl"         # the legacy form: macro leaf on the island node
    p = CI.compile_slice(s)["core_tree"]
    assert p["depth"] == 2 and "stage_basis" not in p
