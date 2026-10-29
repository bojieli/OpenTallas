"""Synthetic source/packaging controls; no physical qualification is inferred."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools.die_plan import hbm_spb_native as H


def vehicle(tmp):
    (tmp/'plan.json').write_text('{}')
    bound=tmp/'rtl'/'spb.sv';bound.parent.mkdir()
    bound.write_text('''module spb(input clk,rst_n);
 ot_pdie_serdes u_lk_S0(.clk(clk),.rst(rst_n),.rx(rx),.tx(tx),.st(st));
 hfd_ep_static u_ep_S0(.clk(clk),.rst_n(rst_n),.sd_rx(rx),.sd_tx(tx),.sd_st(st));
endmodule
''')
    parts=['NW_spb0','NE_spb0'];cells=[];edges=[]
    for part in parts:
        cells += [dict(partition=part,plan_instance=i,module=m) for i,m in [('u_lk_S0','ot_pdie_serdes'),('u_ep_S0','hfd_ep_static')]]
        for src,sp,dst,dp,w in [('u_lk_S0','rx','u_ep_S0','sd_rx',512),('u_lk_S0','st','u_ep_S0','sd_st',2),('u_ep_S0','sd_tx','u_lk_S0','tx',512)]:
            edges.append(dict(src_partition=part,dst_partition=part,src_plan_instance=src,src_port=sp,dst_plan_instance=dst,dst_port=dp,width=w,bit_pairs=[[i,i] for i in range(w)]))
    (tmp/'graph.json').write_text(json.dumps(dict(cells=cells,edges=edges)))
    c=dict(schema='opentallas.hbm.spb0_contract.v1',lk_instance='u_lk_S0',ep_instance='u_ep_S0',lk_module='ot_pdie_serdes',ep_module='hfd_ep_static',lk_clock_port='clk',ep_clock_port='clk',lk_reset_port='rst',ep_reset_port='rst_n',clock_expression='clk',reset_expression='rst_n',rx_depth=4,tx_depth=4,prior_station_realization='NONE',partitions=parts,plan_sha256=H.digest(tmp/'plan.json'),placement_file='placement.json')
    entries=[dict(instance=inst,module='ot_hbm_spb0_regs',width=w,stage=s,sites_um=[[i*2.268,s*.27] for i in range(w)]) for inst,w in [('u_hbm_spb0_rx',514),('u_hbm_spb0_tx',512)] for s in range(4)]
    (tmp/'placement.json').write_text(json.dumps(dict(actual_graph_sha256=H.digest(tmp/'graph.json'),plan_sha256=c['plan_sha256'],entries=entries)))
    (tmp/'contract.json').write_text(json.dumps(c))
    b=SimpleNamespace(ab={'hbm_spb0_native':dict(types=['q_spb0'],graph='graph.json',contract='contract.json')},base=tmp,source_plan=tmp/'plan.json',parts={p:dict(type='q_spb0') for p in parts})
    return b,bound


def test_default_off_and_exact_scope(tmp_path):
    assert H.materialize(SimpleNamespace(ab={}), 'q_spb0', tmp_path/'absent')==[]
    b,f=vehicle(tmp_path)
    assert H.materialize(b,'other',f)==[]
    b.ab['hbm_spb0_native']['types']=['other']
    with pytest.raises(ValueError):H.materialize(b,'other',f)


def test_materialize_and_carry_complete_geometry_with_cycle_price(tmp_path):
    b,f=vehicle(tmp_path)
    original=f.read_text()
    rtl=H.materialize(b,'q_spb0',f)
    assert len(rtl)==1 and rtl[0].is_file()
    assert f.read_text()!=original and '.sd_rx(hbm_spb0_rx_q[511:0])' in f.read_text()
    kit=tmp_path/'kit';kit.mkdir();(kit/'istations.tcl').write_text('# existing stations\n')
    r=H.kit_geometry(tmp_path,'q_spb0',f.read_text(),kit)
    assert r['flops']==4104 and r['rtl_cycles_changed']=={'rx_st':4,'tx':4}
    assert r['model_cycles_changed']=={'rx_st':2,'tx':0}
    assert (kit/'istations.tcl').read_text().startswith('# existing stations')
    assert 'SPB expected exactly 4104' in (kit/'istations.tcl').read_text()
    with pytest.raises(ValueError):H.materialize(b,'q_spb0',f)
    rtl[0].write_text('mutated')
    with pytest.raises(ValueError):H.kit_geometry(tmp_path,'q_spb0',f.read_text(),kit)


@pytest.mark.parametrize('mutation',['plan','master','reset','replicas','graph','path'])
def test_wrong_production_contract_fails_closed(tmp_path,mutation):
    b,f=vehicle(tmp_path)
    if mutation=='plan': (tmp_path/'plan.json').write_text('changed')
    if mutation=='master':f.write_text(f.read_text().replace('ot_pdie_serdes','wrong_phy'))
    if mutation=='reset':f.write_text(f.read_text().replace('.rst(rst_n)','.rst(other)'))
    if mutation=='replicas':b.parts.pop('NE_spb0')
    if mutation=='graph':
        g=json.loads((tmp_path/'graph.json').read_text());g['edges'][0]['bit_pairs'][0]=[0,1];(tmp_path/'graph.json').write_text(json.dumps(g))
    if mutation=='path':b.ab['hbm_spb0_native']['graph']='../escape.json'
    with pytest.raises(ValueError):H.materialize(b,'q_spb0',f)
