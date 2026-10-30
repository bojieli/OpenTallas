"""Fail-closed hardware boundaries for the default-off ordinary DATA buffer recipe."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import start_data_emit as D


def manifest():
    n = D.ident('p','s','start')+'_b0'
    e = dict(src_region='p',dst_region='s',signal='start',
        source_inv=dict(master=D.INV['start'],instance='origin/inv',ff_instance='origin/s2',
            xy_um=[0,0],ff_xy_um=[0,0],orient='R0',qn_pin_um=[0,0],input_pin_um=[.1,0],
            output_pin_um=[0,0],outgoing_edges=1,all_output_sinks=[n+'/A']),
        cells=[dict(instance=n,master=D.BUF,xy_um=[1.08,0],orient='R0')],
        capture_pin_um=[20,0],routes_um=[[[0,0],[1.08,0]],[[1.728,0],[20,0]]])
    return dict(schema=D.SCHEMA,library_source_sha256='a'*64,
        cell_library={D.BUF:dict(size_um=[.648,.27],pins_um={'A':[0,0],'Y':[.648,0]})},
        site_grid_um=[.054,.27],edges=[e])


def test_literal_complete_graph_no_clock_or_flop_change():
    m=manifest()
    doc=dict(stages=[dict(region='s',id='s',root=False,parent='p')],die_outputs=[],direct_ports=[])
    sv='module t;\n ot_dp_landing_origin u_st_s (.clk(clk), .p_start(rs_p));\nendmodule\n'
    out,text=D.apply(doc,sv,m)
    assert '.clk(clk)' in text and '.p_start(rs_p)' not in text
    assert text.count(D.BUF)==1 and out['data_buffers']['added_flops']==0
    assert D.placement_tcl(m).count('source not actual QN-to-INV')==1
    with pytest.raises(D.DataError,match='unbuffered'):
        D.apply(dict(doc,stages=doc['stages']+[dict(region='x',id='x',root=False,parent='p')]),sv,m)


@pytest.mark.parametrize('mutant', ['extra_cycle','first_wire','diagonal','overlap','source_fanout','missing_anchor'])
def test_unpriced_hardware_rejected(mutant):
    m=manifest(); e=m['edges'][0]
    if mutant=='extra_cycle': m['added_register_cycles']=1
    if mutant=='first_wire': e['routes_um'][0]=[[0,0],[0,2],[1.08,2],[1.08,0]]
    if mutant=='diagonal': e['routes_um'][1]=[[1.728,0],[10,1],[20,0]]
    if mutant=='overlap': m['occupied_rects_um']=[[1,0,2,.3]]
    if mutant=='source_fanout': e['source_inv']['outgoing_edges']=2
    if mutant=='missing_anchor': del e['source_inv']['xy_um']
    with pytest.raises((D.DataError,KeyError)):
        D.validate(m)
