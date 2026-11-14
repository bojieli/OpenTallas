"""Directed, bit-precise parent-netlist connectivity; no co-input shortcuts."""
from pathlib import Path
import json
import sys
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import core_conns_netlist as CN


def lef(tmp, name, dirs):
    p = tmp / (name + '.lef')
    p.write_text('MACRO ' + name + '\n' + ''.join('PIN '+n+'\n DIRECTION '+d+' ;\nEND '+n+'\n' for n,d in dirs.items())+'END '+name+'\n')
    return str(p)


def fixture(tmp, text, dirs=None, buses=()):
    dirs = dirs or {'q':'OUTPUT','i':'INPUT'}
    f = lef(tmp, 'HC', dirs)
    plan = {'partition_types': {'T': {'module':'top','outline_um':[100,100],
        'hard_cores':[{'inst':'a','module':'HC','lef':f},{'inst':'b','module':'HC','lef':f},{'inst':'c','module':'HC','lef':f}],
        'buses':list(buses)}}}
    p = tmp/'netlist.v';p.write_text(text)
    return plan,p


STD = '''module AND2(input A, input B, output Y); endmodule
'''


def test_no_input_to_input_shortcut_but_real_output_path(tmp_path):
    plan,p = fixture(tmp_path, STD+'''module top(input x, output y);
wire na,nb,ny;
HC a (.q(na));
HC b (.i(nb));
HC c (.i(ny));
AND2 g (.A(na), .B(nb), .Y(ny));
endmodule
''')
    cc = CN.derive(plan,'T',p,top='top')['core_conns']['T']
    assert cc['a']['q'] == ['core:c.i']
    assert 'core:b.i' not in cc['a']['q']
    assert cc['b']['i'] == ['glue']
    assert cc['c']['i'] == ['core:a.q']


def test_unknown_blackbox_stops_without_false_glue(tmp_path):
    plan,p = fixture(tmp_path, '''module top(input x, output y);
wire na,ny;
HC a (.q(na));
HC c (.i(ny));
UNKNOWN g (.A(na),.Y(ny));
endmodule
''')
    r=CN.derive(plan,'T',p,cores=['a','c'],top='top')
    assert 'q' not in r['core_conns']['T'].get('a',{})
    assert not r['receipt']['qualified']
    assert any('UNKNOWN' in str(x) for x in r['receipt']['unresolved'])


def test_constant_position_in_concat_does_not_shift_alias(tmp_path):
    plan,p=fixture(tmp_path,'''module top(input [1:0] x, output y);
wire [2:0] pack;
assign pack = {x[1],1'b0,x[0]};
HC a (.i(pack[1]));
HC b (.i(pack[0]));
endmodule
''',buses=[{'name':'x','dir':'in','face':'W','width':2}])
    r=CN.derive(plan,'T',p,cores=['a','b'],top='top')['core_conns']['T']
    assert r['a']['i'] == ['glue']
    assert r['b']['i'] == ['bus:x']


def test_top_module_widths_not_overwritten_by_other_module(tmp_path):
    plan,p=fixture(tmp_path,'''module helper(input [15:0] x); endmodule
module top(input [1:0] x, output y);
wire [1:0] w;
assign w=x;
HC a (.i(w));
endmodule
''',buses=[{'name':'x','dir':'in','face':'W','width':2}])
    r=CN.derive(plan,'T',p,cores=['a'],top='top')
    assert r['core_conns']['T']['a']['i']==['bus:x']
    assert len(CN.parse(p,'top')[3][0][0])==2


def test_ambiguous_dropped_scope_never_overwrites_identity(tmp_path):
    h={'left.u_same':{'module':'HC'},'right.u_same':{'module':'HC'}}
    assert CN.match_cores(h,[('HC','u_bound.u_same',{})]) == {}
    assert CN.match_cores(h,[('HC','u_bound.left.u_same',{}),('HC','u_bound.right.u_same',{})]) == {'u_bound.left.u_same':'left.u_same','u_bound.right.u_same':'right.u_same'}


def test_hard_macro_direction_is_scoped_per_lef(tmp_path):
    a=lef(tmp_path,'SOURCE',{'p':'OUTPUT'});b=lef(tmp_path,'SINK',{'p':'INPUT'})
    plan={'partition_types':{'T':{'module':'top','hard_cores':[{'inst':'a','module':'SOURCE','lef':a},{'inst':'b','module':'SINK','lef':b}]}}}
    p=tmp_path/'netlist.v';p.write_text('''module top();
wire w;
SOURCE a (.p(w));
SINK b (.p(w));
endmodule
''')
    r=CN.derive(plan,'T',p,top='top')['core_conns']['T']
    assert r['a']['p']==['core:b.p'] and r['b']['p']==['core:a.p']


def test_liberty_actual_pin_directions(tmp_path):
    p=tmp_path/'cells.lib';p.write_text('library(x){cell(C){pg_pin(VDD){direction:input;} pin(A){direction:input;} pin(Y){direction:output;}}}')
    assert CN.liberty_directions([p]) == {'C':{'A':'INPUT','Y':'OUTPUT'}}


def test_depth_bound_is_unresolved_not_glue(tmp_path):
    plan,p=fixture(tmp_path,STD+'''module top();
wire na,ny;
HC a (.q(na));
HC c (.i(ny));
AND2 g (.A(na),.B(1'b0),.Y(ny));
endmodule
''')
    r=CN.derive(plan,'T',p,cores=['a'],depth=0,top='top')
    assert not r['core_conns']['T'].get('a',{})
    assert any('depth_bound' in str(x) for x in r['receipt']['unresolved'])


def test_one_unresolved_port_omits_entire_core_for_batch_callers(tmp_path):
    plan,p=fixture(tmp_path,'''module top(input x, output y);
wire z;
HC a (.q(y), .mystery(z));
endmodule
''',buses=[{'name':'y','dir':'out','face':'E','width':1}])
    r=CN.derive(plan,'T',p,cores=['a'],top='top')
    assert 'a' not in r['core_conns']['T']
    assert r['receipt']['unresolved']==[{'core':'a','port':'mystery','reason':'unknown_core_port_direction'}]


def test_instance_identity_is_case_sensitive():
    h={'u_A':{'module':'HC'}}
    assert CN.match_cores(h,[('HC','u_bound.u_a',{})]) == {}


def test_cli_reports_unresolved_nonzero_under_isolated_python(tmp_path):
    import subprocess
    plan,p=fixture(tmp_path,'''module top();
wire w;
HC a (.mystery(w));
endmodule
''')
    pp=tmp_path/'plan.json';pp.write_text(json.dumps(plan));out=tmp_path/'out.json'
    r=subprocess.run([sys.executable,'-I',CN.__file__,str(pp),'T',str(p),str(out),'--cores','a','--top','top'],capture_output=True,text=True)
    assert r.returncode==2,r.stderr
    assert not json.loads(out.read_text())['receipt']['qualified']
