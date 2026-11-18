"""Technology chain identity and actual consumed placement ordering/bounds."""
from types import SimpleNamespace
import copy,re,shutil,subprocess
import pytest
import pin_entry_delay as D
import gen_rtl as G
import reset_tree as R
from test_reset_pin_entry_fall import tree,wrapper


def spec(nr=64,ns=92):
    return dict(cell=D.CELL,reset=nr,start=ns,reset_sites_um=[[1+i*.54,10]for i in range(nr)],
                start_sites_um=[[1+i*.54,12]for i in range(ns)],max_hop_um=1.35)


def configured(s=None,t=None):
    p=SimpleNamespace(types={'t':{'outline_um':[100,100],'reset':{'pin_entry_delay':s or spec()}}})
    return D.configure(p,'t',t or tree(),R.ResetError)


def test_default_identity_counts_order_and_guards():
    t=tree();p=SimpleNamespace(types={'t':{'reset':{}}})
    assert D.configure(p,'t',t) is t
    new=configured();assert R.release_clocks(new)==R.release_clocks(t)
    text='\n'.join(R.rtl_lines(new))
    assert 'ot_dp_rrelay_delay #(.N(64)) u_rst_in' in text
    assert 'ot_dp_rrelay_delay #(.N(92)) u_run_in' in text
    price=D.summary(new)['pin_entry_delay'];assert price['buffers']==156 and price['added_flops']==price['added_whole_cycles']==0
    assert 'ot_pin_entry_delay_place u_rst_in 64' in D.placement_tcl(new)
    assert 'ot_pin_entry_delay_place u_run_in 92' in D.placement_tcl(new)
    for key,bad in [('cell','BUFx4f_ASAP7_75t_R'),('reset',True),('reset_sites_um',[]),('max_hop_um',float('nan'))]:
        s=spec();s[key]=bad
        with pytest.raises(R.ResetError):configured(s)
    for change in [dict(entry='sync'),dict(pin_entry_fall=True),dict(pin_root_copies={'copies':[]})]:
        q=tree();q.update(change)
        with pytest.raises(R.ResetError):configured(t=q)


BENCH=r'''
`timescale 1ps/1fs
module tb;
 reg clk=0,r=0,s=0;wire qr,qs,mr,ms;reg er,es;integer n=0,errors=0,mutants=0;
 always #5 clk=~clk;
 actual dut(clk,r,s,qr,qs);wrong mutant(clk,r,s,mr,ms);
 always @(negedge clk) begin n=n+1;r<=(n%4==1 || n%4==2);s<=(n%4==2 || n%4==3);end
 always @(posedge clk)begin
  er=r;es=s;#0.01;
  if(n>2)begin if(qr!==er || qs!==es)errors=errors+1;if(mr!==er || ms!==es)mutants=mutants+1;end
  if(n==100)begin $display("RESULT errors%0d mutants%0d",errors,mutants);if(errors||!mutants)$fatal(1,"identity/mutant");$finish;end
 end
endmodule
module BUFx4_ASAP7_75t_R(input A,output Y);
 assign Y=A;
 initial $display("TECH_CELL");
endmodule
'''


def test_production_two_bit_full_count_identity_and_wrong_polarity(tmp_path):
    if not shutil.which('iverilog'):pytest.skip('iverilog required')
    t=configured();rtl=D.CELL_RTL;mut=rtl.replace('ot_dp_rrelay_delay','ot_dp_rrelay_delay_wrong').replace('assign p[0]=d;','assign p[0]=~d;')
    w=wrapper(t,'actual');mw=wrapper(t,'wrong').replace('ot_dp_rrelay_delay #','ot_dp_rrelay_delay_wrong #')
    f=tmp_path/'bench.sv';f.write_text(G.CELLS+rtl+mut+w+mw+BENCH)
    for synth in [False,True]:
        c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim')]+(['-DSYNTHESIS']if synth else[])+[str(f)],capture_output=True,text=True)
        assert c.returncode==0,c.stderr
        p=subprocess.run(['vvp',str(tmp_path/'sim')],capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
        assert 'RESULT errors0 mutants' in p.stdout
        assert p.stdout.count('TECH_CELL')==(312 if synth else 0)


MOCK=r'''
set ff_dbu 1000;set ff_blk block
array set xpos {c0 100 c1 400 ff 900};array set ypos {c0 0 c1 0 ff 0};array set status {c0 PLACED c1 PLACED ff FIRM}
proc block {method args} {switch $method {getInsts {return {c0 c1 ff}} getRows {return row}}}
proc row {method args} {switch $method {getOrigin {return {0 0}} getSite {return site} getBBox {return rowbox} getOrient {return R0}}}
proc site {method args} {switch $method {getWidth {return 100} getHeight {return 270}}}
proc rowbox {method args} {switch $method {xMin {return 0} xMax {return 10000}}}
proc inst {id method args} {
 global xpos ypos status
 switch $method {
 getName {if {$id eq "ff"} {return {u_rst_in.q$_DFF_P_}};set k [expr {$id eq "c0"?0:1}];return [format {u_rst_in.g_delay\[%s\].u_delay} $k]}
 getMaster {return m_$id}
 getLocation {return [list $xpos($id) $ypos($id)]}
 setLocation {lassign $args xpos($id) ypos($id)}
 setOrient {}
 getPlacementStatus {return $status($id)}
 setPlacementStatus {set status($id) [lindex $args 0]}
 getBBox {return box_$id}
 findITerm {return p_${id}_[lindex $args 0]}
 }
}
proc master {id method args} {switch $method {getName {return [expr {$id eq "ff"?"DFFHQNx1_ASAP7_75t_R":"BUFx4_ASAP7_75t_R"}]} getWidth {return 100} getHeight {return 270} getType {return CORE}}}
proc box {id method args} {global xpos ypos;switch $method {xMin {return $xpos($id)} xMax {return [expr {$xpos($id)+100}]} yMin {return $ypos($id)} yMax {return [expr {$ypos($id)+270}]}}}
proc pin {id name method args} {global xpos ypos;if {$method eq "getAvgXY"} {return [list 1 [expr {$xpos($id)+($name eq "Y"?90:30)}] [expr {$ypos($id)+135}]]}}
foreach id {c0 c1 ff} {interp alias {} $id {} inst $id;interp alias {} m_$id {} master $id;interp alias {} box_$id {} box $id;foreach name {A Y D} {interp alias {} p_${id}_$name {} pin $id $name}}
'''


def test_tcl_consumes_exact_stage_order_and_actual_pin_hops(tmp_path):
    if not shutil.which('tclsh'):pytest.skip('tclsh required')
    for limit,ok in [(.4,True),(.1,False)]:
        f=tmp_path/'place.tcl';f.write_text(D.PLACE_TCL+MOCK+f'\not_pin_entry_delay_place u_rst_in 2 {{{{.2 0}} {{.5 0}}}} {limit} {{}}\nputs DONE\n')
        p=subprocess.run(['tclsh',str(f)],capture_output=True,text=True)
        assert (p.returncode==0)==ok,p.stdout+p.stderr
        if ok:assert 'ordered_max_hop_um 0.34' in p.stdout
        else:assert 'actual ordered hop' in p.stderr
