"""Opt-in output state remains dedicated to its own D-feedback cone."""
import json
import pytest
import face_guard as F
NET='''module top(clk,a,en,o);
input clk;input a;input en;output o;wire n;
DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(n),.QN(o));
MUX2x1_ASAP7_75t_R hold(.A(o),.B(a),.S(en),.Y(n));
endmodule'''
def run(net=NET,held=('o',)):
 return F.guard(net,skip_re=r'^(clk|a|en)$',hold_outputs=held)
def test_only_opted_in_own_D_feedback_passes():
 assert run()['verdict']=='PASS'
 assert run()['registered_hold_bits']==1
 assert run(held=())['verdict']=='FAIL'
@pytest.mark.parametrize('extra',[
 'DFFHQNx1_ASAP7_75t_R other(.CLK(clk),.D(o),.QN());',
 'DFFHQNx1_ASAP7_75t_R other(.CLK(o),.D(a),.QN());',
 'DFFHQNx1_ASAP7_75t_R other(.CLK(clk),.D(a),.RESETN(o),.QN());',
 'arbitrary_macro other(.A(o),.Z());',
 'INVx1_ASAP7_75t_R other(.A(o),.Y(dead));',
 'output leak; assign leak=o;',
])
def test_other_consumers_never_exempted(extra):
 net=NET.replace('endmodule',extra+'\nendmodule')
 if extra.startswith('output leak'):net=net.replace('top(clk,a,en,o)','top(clk,a,en,o,leak)')
 assert run(net)['verdict']=='FAIL'
def test_feedback_cycle_refused():
 net=NET.replace('endmodule','INVx1_ASAP7_75t_R x(.A(o),.Y(t)); INVx1_ASAP7_75t_R y(.A(t),.Y(t)); endmodule')
 assert run(net)['verdict']=='FAIL'
def test_unregistered_output_not_exempted():
 assert run(NET.replace('DFFHQNx1_ASAP7_75t_R ff(.CLK(clk),.D(n),.QN(o));','assign o=a;'))['verdict']=='FAIL'
def test_declared_input_or_missing_output_rejected():
 for held in [('a',),('missing',)]:assert run(held=held)['verdict']=='FAIL'
@pytest.mark.parametrize('rows',[['o','o'],['o.*'],'o',[5]])
def test_profile_requires_exact_unique_bus_names(tmp_path,rows):
 (tmp_path/'freeze.json').write_text(json.dumps(dict(source_profile=dict(registered_hold_outputs=rows))))
 with pytest.raises(ValueError):F.kit_hold_outputs(tmp_path)
