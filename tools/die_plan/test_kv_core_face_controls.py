import importlib.util
import re
from pathlib import Path
p=Path(__file__).resolve().parents[2]/"physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py"
spec=importlib.util.spec_from_file_location("kvgenface",p)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def test_unused_second_clock_cannot_claim_data_flop():
    cj={"pin_class":{"s0__clk[0]":"clk","s1__clk[0]":"clk_unused","s1__pv2[9]":"in"}}
    expr=g.face_control_skip_re(cj,["s0__clk"],["s0__rst_n","s1__rst_n"])
    for n in ["s0__clk","s0__clk[0]","s1__clk[0]","s1__rst_n[0]"]:
        assert re.fullmatch(expr,n)
    assert not re.fullmatch(expr,"s1__pv2[9]")


def test_live_pv_alias_is_a_real_related_clock(tmp_path):
    import sys
    sys.path.insert(0,str(p.parent))
    import pv_pair_clock_contract
    (tmp_path/"kv3_pv_pair.sv").write_text("leaf s0 (.clk(s0__clk[0])); leaf s1 (.clk(s1__clk[0]));")
    cj={"module":"kv3_pv_pair","pin_class":{"s0__clk[0]":"clk","s1__clk[0]":"clk_unused"},"report":{"clk_unused":["s1__clk[0]"]}}
    cj=pv_pair_clock_contract.update(cj,tmp_path)
    assert g.core_clocks_resets(cj)[0]==["s0__clk","s1__clk"]
    assert cj["report"]["clk_unused"]==[]
    sdc=g.sdc(833,250,40,["s0__clk","s1__clk"],[],"pair")
    assert "[get_ports {s0__clk s1__clk}]" in sdc
    assert "all_inputs -no_clocks" in sdc


def test_pv_actual_s1_primary_demotes_disconnected_s0(tmp_path):
    import sys
    sys.path.insert(0,str(p.parent))
    import pv_pair_clock_contract
    (tmp_path/"kv3_pv_pair.sv").write_text("leaf s0 (.clk(s1__clk[0])); leaf s1 (.clk(s1__clk[0]));")
    cj={"module":"kv3_pv_pair","pin_class":{"s0__clk[0]":"clk","s1__clk[0]":"clk_unused"},"report":{"clk_unused":["s1__clk[0]"]}}
    cj=pv_pair_clock_contract.update(cj,tmp_path)
    assert g.core_clocks_resets(cj)[0]==["s1__clk"]
    assert cj["report"]["clk_unused"]==["s0__clk[0]"]
    assert cj["report"]["clock_nets"]=={"clk":"s1__clk[0]"}
