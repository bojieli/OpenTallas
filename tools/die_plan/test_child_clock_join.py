import json
from pathlib import Path
import pytest
import child_clock_join as C


def fixture(tmp_path):
    native = tmp_path/'native'; native.mkdir()
    (native/'6_final.v').write_text('module hist(input clk, input [1:0] i, output o); endmodule\n')
    parent = tmp_path/'parent.v'
    parent.write_text('module parent(input ck, input [1:0] d, output q); hist u_h(.clk(ck),.i(d),.o(q)); endmodule\n')
    libs = {}
    for c in ('tt','ff'):
        p = tmp_path/(c+'.lib'); p.write_text(c); libs[c] = str(p)
    q = dict(graph_identity=dict(status='PASS',master='hist',clock_pin='clk',
        corners={c:dict(selected_liberty_sha256=C.sha(libs[c])) for c in libs}),
        source_qualification=dict(status='NOT RUN'))
    return native,parent,libs,q


def test_actual_instance_join_does_not_expand_internal_graph(tmp_path):
    native,parent,libs,q = fixture(tmp_path)
    result = C.join_parent(q,parent,'parent','u_h','ck',libs,native)
    assert result['status']=='PASS' and result['interface_bits']==4
    assert result['parent_coverage']=='UNEXPANDED_CHILD_ETM'
    assert result['parent_consumption']=='SELECTED_INPUTS_ONLY_NOT_STA'
    assert result['source_qualification']=='NOT RUN'


@pytest.mark.parametrize('mutation',['root','instance','lib','graph','width'])
def test_parent_join_mismatches_refused(tmp_path,mutation):
    native,parent,libs,q = fixture(tmp_path)
    root,inst = 'ck','u_h'
    if mutation=='root': root='other_ck'
    if mutation=='instance': inst='u_other'
    if mutation=='lib': Path(libs['ff']).write_text('changed')
    if mutation=='graph': q['graph_identity']['status']='NOT RUN'
    if mutation=='width': parent.write_text(parent.read_text().replace('.i(d)','.i(d[0])'))
    r=C.join_parent(q,parent,'parent',inst,root,libs,native)
    assert r['status']=='NOT RUN' and r['parent_coverage']=='UNEXPANDED_CHILD_ETM'


def test_legacy_eq_path_string_cannot_qualify_source(tmp_path):
    p=tmp_path/'lec.json'; p.write_text(json.dumps(dict(verdict='EQUIVALENT',netlist='/work/6_final.v')))
    with pytest.raises(ValueError,match='no exact retained input identity'):
        C.source_identity(None,C.load(p),{'6_final.v':'a'*64},p)


def test_official_bound_proof_checks_source_and_result(tmp_path):
    net=tmp_path/'6_final.v';net.write_text('exact native netlist')
    lec=tmp_path/'lec.json';lec.write_text('{"verdict":"EQUIVALENT"}')
    tool=tmp_path/'lec.py';tool.write_text('official proof driver')
    files={str(net):C.sha(net),str(tool):C.sha(tool)}
    r=dict(schema='opentallas.lec_input_identity.v1',lec_sha256=C.sha(lec),
           netlist=str(net),netlist_sha256=C.sha(net),before=files,after=files,
           exit_code=0,image_id='sha256:'+'0'*64,
           command=['python3',str(tool),'--netlist',str(net),'--image','sha256:'+'0'*64])
    receipt=tmp_path/'identity.json';receipt.write_text(json.dumps(r))
    assert C.source_identity(receipt,C.load(lec),{'6_final.v':C.sha(net)},lec)['status']=='PASS'
    net.write_text('different native netlist')
    with pytest.raises(ValueError,match='input changed'):
        C.source_identity(receipt,C.load(lec),{'6_final.v':r['netlist_sha256']},lec)


def test_boundary_maps_keep_every_capture_and_buffer_polarity(tmp_path):
    n=tmp_path/'6_final.v'
    n.write_text('''module hist(input clk, input i, output o);
wire ni; wire q0; wire q1;
INVx1_ASAP7_75t_R u_inv(.A(i),.Y(ni));
DFFHQNx1_ASAP7_75t_R f0(.CLK(clk),.D(ni),.QN(q0));
DFFHQNx1_ASAP7_75t_R f1(.CLK(clk),.D(ni),.QN(q1));
assign o=q0;
endmodule
''')
    endpoints=[dict(reference=f,clock_pin=f+'/CLK',clock='clk',edge='rise') for f in ('f0','f1')]
    r=C.boundary_maps(tmp_path,'hist',endpoints,['clk'])
    assert r['status']=='COMPLETE_DIRECT_BUFFER_MAPS'
    assert {x['reference'] for x in r['maps']['inputs']['i']}=={'f0','f1'}
    assert all(x['inversions']==1 and x['buffer_chain'][0]['instance']=='u_inv' for x in r['maps']['inputs']['i'])
    assert r['maps']['outputs']['o'][0]['reference']=='f0'
    assert r['parent_coverage']=='UNEXPANDED_CHILD_ETM'
    n.write_text(n.read_text().replace('INVx1_ASAP7_75t_R','UNKNOWN_GATE'))
    r=C.boundary_maps(tmp_path,'hist',endpoints,['clk'])
    assert r['status']=='INCOMPLETE' and r['missing'][0]['port']=='i'
