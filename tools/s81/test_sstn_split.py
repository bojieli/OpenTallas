import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from s81 import sstn_split as split


def fixture():
    ports={k:v for k,v in split.BASE_PORTS.items() if k not in ('c1','e1','si','nf')}
    ports.update(x2i=('input',536),x2=('output',536))
    station=SimpleNamespace(name='t0_0',master='dsfd_sstn',kind='sstn',x=100.,y=200.,w=172.776,h=30.216,orient='R0')
    buses=[]
    for p,(direction,width) in ports.items():
        e=[('t0_0',p),('peer',p)] if direction=='output' else [('peer',p),('t0_0',p)]
        buses.append((p,'col_clock' if p=='ck' else 'col_reset' if p=='rs' else 'x_lane',width,e))
    role=dict(logical_parent='dsfd_sstn_e0c0_x2',base_role_straps={p:f"{split.BASE_PORTS[p][1]}'b0" for p in ('c1','e1','si','nf')})
    mapping=dict(schema='s81-sstn-two-leaf-map-v1',parent_outline=[172.8,30.24],
                 leaves=dict(base=dict(master='ot_s81_sstn_base566',origin=[0,0],outline=[84.24,30.24]),
                             payload=dict(master='ot_s81_sstn_payload536',origin=[86.4,0],outline=[86.4,25.92])),roles=[role])
    views={r['master']:dict(w=r['outline'][0],h=r['outline'][1]) for r in mapping['leaves'].values()}
    return dict(insts=[station],buses=buses),{'t0_0':ports},mapping,views


def test_graph_preserves_all_active_nets_and_uses_per_instance_neutral_straps():
    model,usage,mapping,views=fixture();original=copy.deepcopy(model['buses'])
    assert split.expand(model,usage,mapping,views)
    assert [(b[0],b[1],b[2]) for b in model['buses']]==[(b[0],b[1],b[2])for b in original]
    buses={b[0]:b for b in model['buses']}
    assert buses['x2i'][3]==[('peer','x2i'),('t0_0__payload','i')]
    assert buses['x2'][3]==[('t0_0__payload','o'),('peer','x2')]
    assert buses['ck'][3]==[('peer','ck'),('t0_0','ck'),('t0_0__payload','ck')]
    assert model['neutral_role_inputs']=={'t0_0':mapping['roles'][0]['base_role_straps']}
    base,payload=model['insts'];assert (base.x,base.y,base.w,base.h)==(100,200,84.24,30.24)
    assert (payload.x,payload.y,payload.w,payload.h)==(186.4,200,86.4,25.92)
    assert not split.expand(model,usage,mapping,views)


@pytest.mark.parametrize('fault',['missing_view','wrong_width','active_nf_mask','clock_role','posthoc'])
def test_missing_physical_or_changed_function_refused(fault):
    model,usage,mapping,views=fixture()
    if fault=='missing_view':views.pop('ot_s81_sstn_payload536')
    elif fault=='wrong_width':usage['t0_0']['x2i']=('input',535)
    elif fault=='active_nf_mask':usage['t0_0']['nf']=('input',1)
    elif fault=='clock_role':model['insts'][0].orient='MY'
    elif fault=='posthoc':model['bound_views']={'legacy':{}}
    with pytest.raises(ValueError):split.expand(model,usage,mapping,views)


def test_netlist_emits_exact_role_pads_only(tmp_path,monkeypatch):
    import dsrom_s81_fulldie as gen
    model,usage,mapping,views=fixture();split.expand(model,usage,mapping,views)
    # Peer is an explicitly declared input/output source boundary in this unit.
    model['insts'].append(SimpleNamespace(name='peer',master='peer',kind='boundary'))
    monkeypatch.setattr(gen,'real_ports',lambda:{})
    monkeypatch.setattr(gen,'real_lef',lambda p:dict(name='cfg',pins={}))
    monkeypatch.setattr(gen,'die_master_params',lambda m:{})
    monkeypatch.setattr(gen,'RTL_BIND',False)
    path=tmp_path/'die.v';gen.write_netlist(model,1,path)
    text=path.read_text();assert '.nf(1\'b0)' in text and '.x2i(' not in text.split('ot_s81_sstn_payload536')[1].split(';')[0]
    pads=json.loads(Path(str(path)+'.pads.json').read_text())['instances']
    assert set(pads)=={'t0_0'}
    assert {k:v['logical_width']for k,v in pads['t0_0']['ports'].items()}=={'c1':0,'e1':0,'nf':0,'si':0}
    # A live role input cannot acquire a neutral permission.
    assert not {'xai','cci','c0','e0'} & set(pads['t0_0']['ports'])
