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
