"""Mapped admission tests; real Liberty directions/functions, no cell-name waiver."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_census as N
import pre_route_gate as P

LIB = '''library(test) {
 cell(FF) { ff(IQ, IQN) {clocked_on:"CK"; next_state:"D";}
 pin(CK) {direction:input; clock:true;} pin(D) {direction:input;}
 pin(RN) {direction:input;} pin(Q) {direction:output; function:"IQ";} }
 cell(TRANSPARENT) {pin(A) {direction:input;} pin(Y) {direction:output; function:"!A";} }
 cell(CONSTANT) {pin(Y) {direction:output; function:"0";} }
 cell(MACRO) {pin(CK) {direction:input; clock:true;}
 pin(D) {direction:input;} pin(Q) {direction:output; function:"D";} }
 cell(AND) {pin(A) {direction:input;} pin(B) {direction:input;}
 pin(Y) {direction:output; function:"A&B";} }
}'''


def run(tmp_path, n=32, source='port', pin='D', macro=False, buffered=False, extra=''):
    lib = tmp_path/'roles.lib'; lib.write_text(LIB)
    roles, _ = N.liberty_roles([str(lib)])
    text = 'module top(ck,d,rst_n,y); input ck,d,rst_n; output y; wire root, branch;\n'
    if source == 'tie': text += 'CONSTANT tie0(.Y(root));\n'
    elif source == 'ff': text += 'FF launch(.CK(ck),.D(d),.RN(rst_n),.Q(root));\n'
    else: text += 'assign root = d;\n'
    if buffered:
        text += 'TRANSPARENT b(.A(root),.Y(branch));\n'
    for i in range(n):
        net = 'branch' if buffered else 'root'
        data = net if pin == 'D' else "1'b0"
        reset = net if pin == 'RN' else "1'b1"
        text += (f'MACRO m{i}(.CK(ck),.D({net}),.Q(q{i}));\n' if macro else
                 f'FF f{i}(.CK(ck),.D({data}),.RN({reset}),.Q(q{i}));\n')
    text += extra + '\nassign y=q0; endmodule'
    g, _ = N.TL.flatten(N.TL.parse_verilog(text), 'top')
    return N.census(g, roles)


def test_32_pass_33_refuse_and_reset_is_dynamic(tmp_path):
    for source in ['port', 'ff']:
        assert run(tmp_path,32,source)['status']=='PASS'
        assert run(tmp_path,33,source)['violations'][0]['loads']==33
    assert run(tmp_path,33,pin='RN')['status']=='FAIL'


def test_transparent_cells_and_macro_contacts(tmp_path):
    assert run(tmp_path,33,buffered=True)['status']=='FAIL'
    # MACRO uses a sequential timing model here to prevent combinational bypass.
    assert run(tmp_path,33,macro=True)['status']=='FAIL'


def test_complementary_30_direct_plus_30_through_inv_is_60(tmp_path):
    lib=tmp_path/'roles.lib';lib.write_text(LIB);roles,_=N.liberty_roles([str(lib)])
    text='module top(ck,d); input ck,d; wire inv; TRANSPARENT i(.A(d),.Y(inv));\n'
    for i in range(60):
        text+=f'FF f{i}(.CK(ck),.D({"d" if i<30 else "inv"}),.RN(1\'b1),.Q(q{i}));\n'
    text+='endmodule'
    g,_=N.TL.flatten(N.TL.parse_verilog(text),'top')
    r=N.census(g,roles)
    assert r['violations'][0]['loads']==60


def test_only_real_constant_and_clock_pin_exempt(tmp_path):
    assert run(tmp_path,100,source='tie')['status']=='PASS'
    # The same clock root also drives dynamic D pins; those must still count.
    assert run(tmp_path,33,extra='assign d=ck;')['status']=='FAIL'


def test_nested_attributes_never_become_pin_roles_and_bus_bits_are_explicit(tmp_path):
    assert N.attr('timing() { clock:true; function:"0"; direction:output; }', 'clock') is None
    assert N.attr('timing() { function:"0"; } function:"!A";', 'function') == '!A'
    p=tmp_path/'bus.lib'
    p.write_text('''library(L) {cell(BUS) {bus(D) {direction:input;
      timing() {clock:true; function:"0";}
      pin(D[1]) {clock:true;} pin(D[0]) {clock:false;}
    } pin(Q) {direction:output; function:"D[0]";} }}''')
    roles,_=N.liberty_roles([str(p)])
    assert not roles['BUS']['pins']['D']['clock']
    assert roles['BUS']['pins']['D[1]']['clock']
    assert not roles['BUS']['pins']['D[0]']['clock']
    g=N.TL.Graph();a=g.net('a');clk=g.net('ck');g.ports={'d':('input',a),'ck':('input',clk)}
    g.cells=[('BUS',f'b{i}',{'D':[clk,a],'Q':[g.net(f'q{i}')]}) for i in range(33)]
    r=N.census(g,roles)
    assert r['violations'][0]['loads']==33
    assert r['driver_counts']==[{'driver':'d','driver_role':'input_port','net':'a','loads':33}]


def test_endpoint_reconvergence_not_double_counted(tmp_path):
    g=N.TL.Graph();a=g.net('a');b=g.net('b');c=g.net('c');out=g.net('out');one=g.net("1'1")
    g.ports={'d':('input',a),'ck':('input',c)}
    g.cells=[('TRANSPARENT','b0',{'A':[a],'Y':[b]}),('TRANSPARENT','b1',{'A':[a],'Y':[b]}),
             ('FF','f',{'CK':[c],'D':[b],'RN':[one],'Q':[out]})]
    p=tmp_path/'roles.lib';p.write_text(LIB);roles,_=N.liberty_roles([str(p)])
    # Multiple native drivers refuse instead of laundering a reconvergent net.
    assert N.census(g,roles)['role_errors']
    g.cells.pop(1)
    assert N.census(g,roles)['max_dynamic_loads']==1


def test_missing_cell_pin_and_lib_fail_closed(tmp_path):
    p=tmp_path/'roles.lib';p.write_text(LIB)
    roles,_=N.liberty_roles([str(p)])
    g=N.TL.Graph();x=g.net('x');g.cells=[('UNKNOWN','u',{'A':[x]})]
    assert 'missing Liberty cell' in N.census(g,roles)['role_errors'][0]
    g.cells=[('FF','u',{'UNKNOWN':[x]})]
    assert 'missing Liberty pin' in N.census(g,roles)['role_errors'][0]
    try:N.liberty_roles([])
    except ValueError:pass
    else:assert False


def test_gate_requires_pinned_receipt_and_no_legacy_threshold_escape():
    assert 'export OT_GATE_NATIVE_CENSUS=1' in P.REMOTE_SH
    g=P.Gate();assert not P.check_native_census(g,'')
    report=dict(schema='opentallas.pre_gate_native_census.v1',status='PASS',limit=32,
                liberty=[{'sha256':'a'*64}],netlist={'sha256':'b'*64},role_errors=[],violations=[],max_dynamic_loads=32)
    assert P.check_native_census(P.Gate(),'GATE_NATIVE_CENSUS_RESULT '+json.dumps(report))
    report['limit']=256
    assert not P.check_native_census(P.Gate(),'GATE_NATIVE_CENSUS_RESULT '+json.dumps(report))


def test_cli_outputs_hashed_provenance(tmp_path):
    lib=tmp_path/'roles.lib';lib.write_text(LIB)
    net=tmp_path/'top.v';net.write_text('module top(ck,d,y); input ck,d; output y; FF f(.CK(ck),.D(d),.RN(1\'b1),.Q(y)); endmodule')
    out=tmp_path/'result.json'
    r=subprocess.run([sys.executable,N.__file__,'--netlist',str(net),'--top','top','--liberty',str(lib),'--out',str(out)],capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
    d=json.loads(out.read_text());assert len(d['netlist']['sha256'])==64 and len(d['liberty'][0]['sha256'])==64
