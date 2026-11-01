"""Two package receivers in a partition need separate physical top input pins."""
from types import SimpleNamespace
import bind


def test_same_pin_names_are_leaf_specific():
    b = bind.Binder.__new__(bind.Binder)
    b.members = {'glue': [0, 1], 'phy': [2]}
    b.parts = {'glue': {'type': 'glue'}, 'phy': {'type': 'phy'}}
    c = lambda inst: {'inst': inst, 'module': 'pad', 'bump_ports': [dict(pin='pad_i', dir='input', width=1)]}
    b.types = {'glue': {'contents': [c('u_bump_fwd_epoch'), c('u_bump_fwd_lrst')]},
               'phy': {'contents': [c('u_phy')]}}
    b.F = SimpleNamespace(cells=[SimpleNamespace(module='pad', ports={}, path=n)
        for n in ('bump_fwd_epoch', 'bump_fwd_lrst', 'phy')])
    b.G = SimpleNamespace(kind={0:'leaf',1:'leaf',2:'leaf'})
    b.rel_of = lambda ci: b.F.cells[ci].path
    got = b.bump_pins()
    assert [x['dport'] for x in got['glue']] == ['glue_bump_fwd_epoch_pad_i','glue_bump_fwd_lrst_pad_i']
    assert got['phy'][0]['dport'] == 'phy_pad_i'  # Existing unique physical input name stays unchanged.
    assert got['glue'][0]['pport'] != got['glue'][1]['pport']
    assert b.bump_pins() is got


def test_explicit_model_default_only():
    import pytest
    c = SimpleNamespace(module='pad', path='bump_fwd_epoch', ports={'o':[12], 'pad_i':['0']})
    F = SimpleNamespace(cells=[c])
    R = SimpleNamespace(part_of=lambda _: 'glue', local_of=lambda _: 'bump_fwd_epoch')
    entry = dict(inst='u_bump_fwd_epoch', module='pad', bump_ports=[dict(pin='pad_i',dir='input',width=1,model_default=0)])
    p = dict(partitions=[dict(name='glue',type='glue')], partition_types={'glue':dict(contents=[entry])})
    assert bind.detach_bump_model_defaults(F,R,p)[0]['model_default'] == 0
    assert 'pad_i' not in c.ports and c.ports['o']==[12]
    for bad in (['1'],[15]):
        c.ports['pad_i']=bad
        with pytest.raises(bind.BindError,match='model default mismatch'):
            bind.detach_bump_model_defaults(F,R,p)
    del entry['bump_ports'][0]['model_default']
    assert bind.detach_bump_model_defaults(F,R,p)==[] and c.ports['pad_i']==[15]


def test_two_signal_pads_have_physical_sites_without_macro(tmp_path):
    import json
    import gen_phys
    entries = [dict(inst='u_bump_fwd_'+n,module='pad',bump_ports=[dict(pin='pad_i',dir='input',width=1)]) for n in ('epoch','lrst')]
    ports=['bump_bump_fwd_'+n+'_pad_i' for n in ('epoch','lrst')]
    P=SimpleNamespace(types={'glue':dict(contents=entries,outline_um=[100,200],
        pads=[dict(name=n,dir='in',width=1,layer='M7',sites_um=[[17.28,34.56+i*69.12]]) for i,n in enumerate(ports)])},
        layers={'M7':dict(dir='V',pitch_um=.064,offset_um=.032)})
    report=dict(bump_ports=[dict(partition='glue',leaf='glue.'+e['inst'],pin='pad_i',dir='input',width=1,part_port=n)
        for e,n in zip(entries,ports)])
    (tmp_path/'bind_report.json').write_text(json.dumps(report))
    (tmp_path/'kit_rtl.json').write_text(json.dumps(dict(bind_out=str(tmp_path),instances=['glue'],
        bound_only_pins=[dict(port=n,dir='input',width=1) for n in ports])))
    assert gen_phys.kit_bump_ports(P,'glue',tmp_path/'kit_rtl.f')==[]
    sites=gen_phys.signal_pad_sites(P,'glue')
    assert len(sites)==2 and sites[0][:3]==(ports[0],0,'M7')
    assert sites[0][3]==17.312  # actual M7 track (never an invented macro pin)
    # Existing hard macro declarations still retain the physical macro-pin path.
    P.types['glue']['pads']=[]
    assert len(gen_phys.kit_bump_ports(P,'glue',tmp_path/'kit_rtl.f'))==2
