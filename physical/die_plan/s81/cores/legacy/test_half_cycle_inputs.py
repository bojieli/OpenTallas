import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).with_name("gen_core_kit_legacy.py")
s=importlib.util.spec_from_file_location("half_gen",p);G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
base=lambda n:n.split("[")[0]
names=["ck","rst_n","in_w[0]","out_res[0]"]
dirs={n:("OUTPUT" if n.startswith("out_res") else "INPUT") for n in names}
def bounds(selected):return G.half_cycle_input_bounds(selected,names,dirs,["ck"],["rst_n"],base,833.,20.)
def test_absent_default_identical():
 assert bounds(None)==({}, {})
 assert G.sdc(833,250,20,["ck"],[],"m")==G.sdc(833,250,20,["ck"],[],"m",half_max={})
def test_real_data_only_bounds():
 mn,mx=bounds(["in_w"]);assert mn=={"in_w":396.5};assert mx=={"in_w":666.4}
 txt=G.sdc(833,250,20,["ck"],["rst_n"],"m",mn,mx)
 assert "set_input_delay -max 666.4000 -clock vclk [get_ports {in_w[*]}]" in txt
 assert "set_input_delay -min 396.5000 -clock vclk [get_ports {in_w[*]}]" in txt
 assert "-min 396.5000 -clock vclk $non_clk_in" not in txt
@pytest.mark.parametrize("bad",["ck","rst_n","out_res","missing"])
def test_not_data_refused(bad):
 with pytest.raises(SystemExit,match="DATA inputs only"):bounds([bad])
def test_duplicate_refused():
 with pytest.raises(SystemExit,match="repeats"):bounds(["in_w","in_w"])
