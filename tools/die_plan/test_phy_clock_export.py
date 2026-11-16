"""Actual PHY tap binding changes source identity, never clock policy."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import face_guard as FG
import pad_clock as PC
import sdc_lint as SL
from test_pad_clock import plan

NET = """module top(clk, clk_t2, a, y, pma_tck, fclk_out_coll_o0);
input clk; input clk_t2; input a; output y; output pma_tck; output fclk_out_coll_o0;
wire mid;
DFFHQNx1_ASAP7_75t_R q_in(.CLK(clk),.D(a),.QN(mid));
DFFHQNx1_ASAP7_75t_R q_out(.CLK(clk),.D(mid),.QN(y));
BUFx2_ASAP7_75t_R p(.A(clk_t2),.Y(pma_tck));
BUFx2_ASAP7_75t_R f(.A(clk),.Y(fclk_out_coll_o0));
endmodule"""

def test_actual_export_guard_rejects_stale_and_blindly_rebased_sources():
    def guard(pma, fwd):
        return FG.guard(NET, clocks=["clk","clk_t2"],
                        exports=[("pma_tck",pma),("fclk_out_coll_o0",fwd)])
    assert guard("clk_t2","clk")["verdict"] == "PASS"
    assert guard("clk","clk")["fail_counts"].get("clock_export")
    assert guard("clk_t2","clk_t2")["fail_counts"].get("clock_export")

def test_owned_hook_is_typed_and_not_a_general_source_escape(tmp_path):
    p=plan();text=PC.sdc(p,"mid","unchanged\n")
    # Use the complete generated SDC and existing strict role/CDC policy.
    import gen_phys as GP
    text=GP.sdc(p,"mid",GP.type_pins(p,"mid"))
    ctx=SL.kit_context(p,"mid")
    assert not SL.lint(text,**ctx)
    assert SL.lint(text.replace("source /work/phy_clock_export_source.tcl",
                               "source /work/arbitrary.tcl"),**ctx)
    PC.write_contract(p,"mid",tmp_path)
    assert (tmp_path/"phy_clock_export_source.tcl").exists()
    assert (tmp_path/"phy_clock_export.tcl").read_bytes()==(HERE/"phy_clock_export.tcl").read_bytes()
    keep=tmp_path/"unrelated.tcl";keep.write_text("unchanged")
    p.types["mid"]["clock"].pop("pad_clock");PC.write_contract(p,"mid",tmp_path)
    assert keep.read_text()=="unchanged"
    assert not (tmp_path/"phy_clock_export_source.tcl").exists()

@pytest.mark.parametrize("actual,propagated", [("clk_t2",0),("clk_t2",1),("clk",1),("alias",1)])
def test_realized_tcl_mapping_and_propagated_state(tmp_path,actual,propagated):
    tcl=shutil.which("tclsh")
    if not tcl:pytest.skip("tclsh unavailable")
    script=r"""
namespace eval ord {}
proc ord::get_db_block {} {return block}
proc block {m args} {return target}
proc target {m args} {switch $m {getNet {return outnet} getIoType {return OUTPUT} getName {return {pma_tck[0]}}}}
proc outnet {m args} {switch $m {getBTerms {return target} getITerms {return outpin}}}
proc outpin {m args} {switch $m {getIoType {return OUTPUT} getInst {return buf}}}
proc buf {m args} {switch $m {getMaster {return master} getName {return pma_buf} getITerms {return {inpin outpin}}}}
proc master {m args} {return BUFx2_ASAP7_75t_R}
proc inpin {m args} {switch $m {getIoType {return INPUT} getSigType {return SIGNAL} getNet {return srcnet}}}
proc srcnet {m args} {
 global actual
 switch $m {getBTerms {if {$actual eq "alias"} {return {rawroot taproot}};return root} getITerms {return {}}}
}
proc root {m args} {global actual;switch $m {getIoType {return INPUT} getName {return $actual}}}
proc rawroot {m args} {switch $m {getIoType {return INPUT} getName {return clk}}}
proc taproot {m args} {switch $m {getIoType {return INPUT} getName {return clk_t2}}}
proc get_clocks {args} {if {[lindex $args end] eq "pma_tck"} {return G};return M}
proc get_ports {args} {return [lindex $args end]}
proc get_full_name {p} {return $p}
proc get_property {clock prop} {
 global propagated
 switch $prop {is_generated {return 1} period {return 833} sources {return {clk clk_t1 clk_t2 clk_t3 clk_t4 clk_t5 clk_t6 clk_t7 clk_t8 clk_t9 clk_t10 clk_t11 clk_t12 clk_t13 clk_t14 clk_t15 clk_t16 clk_t17 clk_t18 clk_t19 clk_t20 clk_t21}} is_propagated {return $propagated}}
}
set calls {}
proc create_generated_clock {args} {global calls propagated;lappend calls $args;set propagated 0}
proc set_propagated_clock {args} {global propagated;set propagated 1}
proc unset_propagated_clock {args} {global propagated;set propagated 0}
"""
    script+=f"set actual {actual}\nset propagated {propagated}\n"
    script+=f"set ::env(RESULTS_DIR) {{{tmp_path}}}\nsource {{{HERE/'phy_clock_export.tcl'}}}\n"
    script+="ot_phy_export_rebind [dict create target {pma_tck[0]} clock pma_tck master clk declared_source clk period 833 period_ps 833]\n"
    script+='puts "STATE $propagated CALLS [llength $calls]"\n'
    result=subprocess.run([tcl],input=script,text=True,capture_output=True,check=True)
    assert not result.stderr,result.stderr
    ledger=json.loads((tmp_path/"phy_clock_export_binding.json").read_text())
    want="clk_t2" if actual=="clk_t2" else "clk"
    assert ledger["realized_source"]==want
    assert ledger["status"]==("REBOUND" if want!="clk" else "UNCHANGED")
    assert f"STATE {propagated} CALLS {int(want!='clk')}" in result.stdout
