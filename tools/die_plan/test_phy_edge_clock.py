import json,subprocess
from pathlib import Path
import pytest
import gen_phys as G
import schema as S
HERE=Path(__file__).parent
def plan(edge):
 p=json.loads((HERE/"examples/tiny_plan.json").read_text())
 p["partition_types"]["mid"]["clock"]["edge_clocks"]=[edge]
 return p
def edge(**kw):return dict(port="clk_clk_phy",tap_um=[10,10],**kw)
def test_explicit_period_layer_and_port_contract():
 p=S.Plan(plan(edge(period_ps=1043,layer="M5",cdc_contract="ot_fdi_phy_cdc")))
 s=G.sdc(p,"mid",[])
 assert "1043.0000" in s and "ot_fdi_phy_cdc_constraints clk clk_clk_phy" in s
 assert "set_clock_groups" not in s
 assert any(n=="clk_clk_phy" for n,x,y in G.tap_pins(p,"mid"))
 assert "place_pin -pin_name clk_clk_phy -layer M5" in G.io_tcl(p,"mid",[])
def test_legacy_multiplier_unchanged():
 p=S.Plan(plan(edge(period_mult=6)))
 assert G.edge_clock_pins(p,"mid")[0][3]==6
 assert f"{G.t_lib(6*p.die['period_ps']):.4f}" in G.edge_clock_sdc(p,"mid")
@pytest.mark.parametrize("attrs",[dict(period_ps=0),dict(period_ps=1043,period_mult=1),dict(cdc_contract="ot_fdi_phy_cdc")])
def test_bad_contract_rejected(attrs):
 raw=plan(edge(**attrs))
 assert S.validate(raw)
 with pytest.raises(ValueError):G.edge_clock_pins(S.Plan(raw),"mid")
def test_exact_cdc_fences_and_missing_class_fail_closed():
 regs=["u_bound.u_core.u_fdi_cdc.u_rx.wr_gray_r1[0]","u_bound.u_core.u_fdi_cdc.u_tx.rd_gray_w1[0]",
 "u_bound.u_core.u_fdi_cdc.u_rx.mem[0][0]","u_bound.u_core.u_fdi_cdc.u_tx.mem[0][0]",
 "u_bound.u_core.u_fdi_cdc.up_s[0]","u_bound.u_core.u_fdi_cdc.u_prs.reset_pipe[0]",
 "u_bound.u_core.u_fdi_cdc.up_s[1]","unrelated.u_rx.wr_gray_r1[0]"]
 pre="set regs {"+ " ".join("{"+r+"}" for r in regs)+"}\n"+"""
proc all_registers {args} {global regs;return $regs}
proc get_full_name {c} {return $c}
proc get_clocks {c} {return $c}
proc set_max_delay {args} {puts "MAX $args"}
proc set_false_path {args} {puts "FALSE $args"}
"""
 script=pre+(HERE/"fdi_phy_cdc.tcl").read_text()+"\not_fdi_phy_cdc_constraints clk clk_clk_phy 833 1043 60\n"
 r=subprocess.run(["tclsh"],input=script,text=True,capture_output=True)
 assert not r.stderr,r.stderr
 assert "416.5" in r.stdout and "773" in r.stdout and "983" in r.stdout
 assert "up_s[1]" not in r.stdout and "unrelated" not in r.stdout
 bad=script.replace("{u_bound.u_core.u_fdi_cdc.u_rx.mem[0][0]}","")
 r=subprocess.run(["tclsh"],input=bad,text=True,capture_output=True)
 assert "missing exact native register class rx_mem" in r.stderr
