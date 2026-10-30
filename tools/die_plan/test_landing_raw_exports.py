"""Typed raw outputs use explicit per-copy use/open inventory; inputs never do."""
import copy
import json
import sys
from pathlib import Path

import pytest
import landing_contract as L
import reset_tree as R
import schema as S
from test_landing_start_tree import _plan,_decl,SIDE
sys.path.insert(0,str(Path(__file__).parents[1]/'s81_head'))
import head_raw_start_contract as H


@pytest.fixture
def raw(monkeypatch):
    p=_plan(_decl())
    row=dict(port='raw_port',instance='real_relay',net='raw_q',xy_um=[1.,1.])
    t=p.types['t_lnc'];t['reset_start_raw_exports']=[row]
    t['clock']['landing_contract']['pins'].append(dict(name='raw_port',dir='out',kind='ctl',epoch=False,
        layer='M5',xy_um=[1.,1.],source_instance='real_relay',source_net='raw_q',source_registered=True))
    monkeypatch.setattr(R,'for_type',lambda *args:dict(relays=[dict(name='real_relay',q='raw_q',xy=(1.,1.))]))
    side=copy.deepcopy(SIDE)
    side['count_aligned']['start_pins']['reset_inputs']=[dict(src_part='lnc',src_port='raw_port',net='wr_lnc__raw_port')]
    tmap={tn:{x['name']:x['dir'] for x in ty['clock']['landing_contract']['pins']} for tn,ty in p.types.items()}
    edges={(e[q]['part'],e[q]['bus']) for e in p.clock['landing_network']['edges'] for q in ('src','dst')}
    p.clock['landing_network']['start_tree']=L.start_declaration(side['count_aligned']['start_pins'],
        {pn:x['type'] for pn,x in p.parts.items()},tmap,edges,{'t_lnc':{'raw_port'}})
    return p,side


def test_typed_output_inventory_proves_real_source_and_sidecar(raw):
    p,side=raw;r=L.check(p,side)
    assert not r['errors'] and r['start_tree']['open']==2
    assert dict(part='cp',pin='raw_port') in p.clock['landing_network']['start_tree']['open']


@pytest.mark.parametrize('mutation',['input','clock','unregistered','instance','net','xy','used_open','missing_used','wrongwire','undeclared'])
def test_no_prefix_exemption_or_used_as_open(raw,mutation):
    p,side=raw;t=p.types['t_lnc'];pin=t['clock']['landing_contract']['pins'][-1];row=t['reset_start_raw_exports'][0]
    st=p.clock['landing_network']['start_tree']
    if mutation=='input':pin['dir']='in'
    if mutation=='clock':pin['kind']='clock'
    if mutation=='unregistered':pin['source_registered']=False
    if mutation in ('instance','net'):row[mutation]='invented'
    if mutation=='xy':row['xy_um']=[2.,1.]
    if mutation=='used_open':st['open'].append(dict(part='lnc',pin='raw_port'))
    if mutation=='missing_used':st['uses']=[u for u in st['uses'] if u['pin']!='raw_port']
    if mutation=='wrongwire':next(u for u in st['uses'] if u['pin']=='raw_port')['net']='invented'
    if mutation=='undeclared':t.pop('reset_start_raw_exports')
    assert L.check(p,side)['errors']


def test_head_enrichment_matches_actual_provider_connections_and_rejects_missing_inventory(raw,monkeypatch):
    p,side=raw
    # Preserve fixture Plan so this tests source enrichment without an unrelated full die.
    monkeypatch.setattr(S,'Plan',lambda plan,path=None:p)
    top='''module top();
 m org (
 .o(x)
 );
 m lnc (
 .raw_port(wr_lnc__raw_port)
 );
 m cp (
 .raw_port(wr_cp__raw_port)
 );
 ot_die_start_stages u_die_start_stages (
 .reset_actual(wr_lnc__raw_port)
 );
endmodule'''
    source=dict(part='lnc',type='t_lnc',port='raw_port',instance='real_relay',net='raw_q')
    stages=dict(reset_ports=dict(reset_actual=source),stages=[dict(reset_port='reset_actual',reset_source=source)])
    plan=dict(partition_types=p.types,partitions=[dict(name=pn,**v) for pn,v in p.parts.items()],clock=p.clock)
    new,ns,r=H.enrich(plan,side,stages,top)
    assert (r['used_raw_outputs'],r['open_raw_outputs'])==(1,1)
    for broken in [dict(reset_ports={},stages=[]),dict(reset_ports=dict(renamed=source),stages=[])]:
        with pytest.raises(ValueError,match='inventory'):H.enrich(plan,side,broken,top)
    with pytest.raises(ValueError,match='wired'):
        H.enrich(plan,side,stages,top.replace('.reset_actual(wr_lnc__raw_port)','.reset_actual(wr_cp__raw_port)'))


def test_private_same_cycle_output_must_copy_exact_raw_source(raw):
    p,side=raw;t=p.types['t_lnc'];t['private_reset_start_exports']=True
    pin=t['clock']['landing_contract']['pins'][-1]
    pin.update(source_net='raw_port',source_copy_from_net='raw_q',source_output_pin='export_q')
    assert not L.check(p,side)['errors']
    pin['source_copy_from_net']='wrong'
    assert L.check(p,side)['errors']
