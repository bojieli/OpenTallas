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


def test_unused_abi_output_has_no_invented_terminal_or_net():
    model, usage, mapping, views = fixture()
    usage['t0_0'].pop('cc')
    model['buses'] = [b for b in model['buses'] if b[0] != 'cc']
    original = copy.deepcopy(model['buses'])
    split.expand(model, usage, mapping, views)
    assert [b[:3] for b in model['buses']] == [b[:3] for b in original]
    assert not any(n == 't0_0' and p.split('[')[0] == 'cc' for b in model['buses'] for n, p in b[3])
    record = model['sstn_split']['roles'][0]
    assert record['absent_unused_outputs'] == ['cc']
    assert model['sstn_split']['source_abi']['base']['ports']['cc'] == ('output', 15)


def test_sparse_used_output_bits_keep_exact_offsets_and_order():
    model, usage, mapping, views = fixture()
    model['buses'] = [b for b in model['buses'] if b[0] != 'x2']
    partial = [('low', 'x_lane', 7, [('t0_0', 'x2[17:23]'), ('peer', 'low')]),
               ('high', 'x_lane', 8, [('t0_0', 'x2[200:207]'), ('peer', 'high')])]
    model['buses'].extend(partial)
    usage['t0_0']['x2'] = ('output', 208)
    split.expand(model, usage, mapping, views)
    assert model['buses'][-2:] == [
        ('low', 'x_lane', 7, [('t0_0__payload', 'o[17:23]'), ('peer', 'low')]),
        ('high', 'x_lane', 8, [('t0_0__payload', 'o[200:207]'), ('peer', 'high')])]
    assert model['sstn_split']['roles'][0]['used_output_ranges']['x2'] == [(17, 23), (200, 207)]


@pytest.mark.parametrize('fault', ['dropped_active_output_usage', 'dropped_required_input_bit',
                                  'mixed_width', 'oversized_output', 'mixed_direction', 'duplicate_terminal'])
def test_bit_census_negatives_are_atomic(fault):
    model, usage, mapping, views = fixture()
    if fault == 'dropped_active_output_usage':
        usage['t0_0'].pop('cc')  # Actual cc endpoints still exist: it is active.
    elif fault == 'dropped_required_input_bit':
        model['buses'] = [b for b in model['buses'] if b[0] != 'xai']
        model['buses'].extend([
            ('ai_low', 'x_lane', 281, [('peer', 'low'), ('t0_0', 'xai[0:280]')]),
            ('ai_high', 'x_lane', 1, [('peer', 'high'), ('t0_0', 'xai[282:282]')])])
    elif fault == 'mixed_width':
        b = next(b for b in model['buses'] if b[0] == 'xai')
        b[3][1] = ('t0_0', 'xai[0:281]')  # 282 bits on a 283-bit net.
    elif fault == 'oversized_output':
        usage['t0_0']['xa'] = ('output', 284)
    elif fault == 'mixed_direction':
        usage['t0_0']['xa'] = ('input', 283)
    elif fault == 'duplicate_terminal':
        b = next(b for b in model['buses'] if b[0] == 'xai')
        b[3].append(('t0_0', 'xai'))
    original = copy.deepcopy(model)
    with pytest.raises(ValueError):
        split.expand(model, usage, mapping, views)
    assert model == original


def test_late_invalid_station_does_not_mutate_first_station_or_power():
    model, usage, mapping, views = fixture()
    first = model['insts'][0]; first.power_w = 1.0
    second = copy.copy(first); second.name = 't0_1'; second.orient = 'MY'
    model['insts'].append(second)
    usage['t0_1'] = copy.deepcopy(usage['t0_0'])
    second_buses = [(bid + '_second', cls, width,
                     [('t0_1' if n == 't0_0' else n, p) for n, p in eps])
                    for bid, cls, width, eps in model['buses']]
    model['buses'].extend(second_buses)
    original = copy.deepcopy(model)
    with pytest.raises(ValueError, match='instance=t0_1 role=dsfd_sstn_e0c0_x2 absent_outputs='):
        split.expand(model, usage, mapping, views)
    assert model == original
    assert first is model['insts'][0] and first.power_w == 1.0


def test_existing_output_fanout_to_distinct_nets_is_preserved():
    model, usage, mapping, views = fixture()
    extra = ('xa_extra_readers', 'x_lane', 10, [('t0_0', 'xa[0:9]'), ('other_peer', 'xa')])
    model['buses'].append(extra)
    split.expand(model, usage, mapping, views)
    assert model['buses'][-1] == extra
    assert sum(1 for b in model['buses'] for n, p in b[3] if n == 't0_0' and p.split('[')[0] == 'xa') == 2


def actual_t3_9_fixture():
    root = Path(__file__).resolve().parents[2]
    receipt = json.loads((root/'results/arch/s81_sstn_split_1552/current_t3_9_fixture.json').read_text())
    model = dict(insts=[SimpleNamespace(**receipt['station'])],
                 buses=[(bid, cls, width, [tuple(ep) for ep in eps]) for bid, cls, width, eps in receipt['buses']])
    usage = {n: {p: tuple(sig) for p, sig in ports.items()} for n, ports in receipt['usage'].items()}
    return model, usage, receipt['mapping'], receipt['views'], receipt


def test_actual_current_t3_9_legacy_rejection_preserves_unused_cc_and_every_live_net():
    model, usage, mapping, views, evidence = actual_t3_9_fixture()
    assert evidence['legacy_predicate_match']['instance'] == 't3_9'
    assert evidence['legacy_predicate_match']['role'] == 'dsfd_sstn_e0c0_x2'
    assert evidence['legacy_predicate_match']['absent_outputs'] == ['cc']
    assert 'cc' not in usage['t3_9']
    original = copy.deepcopy(model['buses'])
    split.expand(model, usage, mapping, views)
    assert [b[:3] for b in model['buses']] == [b[:3] for b in original]
    assert model['sstn_split']['roles'][0]['absent_unused_outputs'] == ['cc']
    assert model['sstn_split']['source_abi']['base']['ports']['cc'] == ('output', 15)
    for old, new in zip(original, model['buses']):
        before = [ep for ep in old[3] if ep[0] != 't3_9']
        after = [ep for ep in new[3] if not ep[0].startswith('t3_9')]
        assert before == after
    assert not any(n.startswith('t3_9') and p.split('[')[0] == 'cc' for b in model['buses'] for n, p in b[3])


@pytest.mark.parametrize('fault', ['dropped_active_bit', 'mixed_width', 'duplicate_terminal'])
def test_actual_t3_9_conservation_negatives_are_atomic(fault):
    model, usage, mapping, views, evidence = actual_t3_9_fixture()
    b = next(b for b in model['buses'] if ('t3_9', 'xai') in b[3])
    if fault == 'dropped_active_bit':
        # Make the transport syntactically valid but omit its active bit 281.
        model['buses'].remove(b)
        source = b[3][0]
        model['buses'].extend([
            (b[0]+'_low', b[1], 281, [(source[0], source[1]+'[0:280]'), ('t3_9', 'xai[0:280]')]),
            (b[0]+'_high', b[1], 1, [(source[0], source[1]+'[282:282]'), ('t3_9', 'xai[282:282]')])])
    elif fault == 'mixed_width':
        b[3][-1] = ('t3_9', 'xai[0:281]')
    else:
        b[3].append(('t3_9', 'xai'))
    original = copy.deepcopy(model)
    with pytest.raises(ValueError):
        split.expand(model, usage, mapping, views)
    assert model == original
