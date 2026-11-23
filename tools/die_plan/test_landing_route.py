from types import SimpleNamespace
import sys
import pytest
import landing_route


def fixture(monkeypatch, edges, uses=()):
    monkeypatch.setitem(sys.modules,'landing_contract',SimpleNamespace(check=lambda p:dict(errors=[])))
    types = {'src':{'clock':{'landing_contract':{'pins':[
        dict(name='fwd',dir='out',kind='clock',layer='M7',xy_um=[2,2])]} }},
        'dst':{'clock':{'landing_contract':{'pins':[
        dict(name='rx',dir='in',kind='clock',layer='M7',xy_um=[3,3]),
        dict(name='start',dir='in',kind='ctl',layer='M7',xy_um=[4,4])]} }}}
    return SimpleNamespace(types=types,parts={'a':{'type':'src'},'b':{'type':'dst'},
        'c':{'type':'dst'},'d':{'type':'src'}},clock={'landing_network':{'edges':edges,
        'start_tree':{'uses':list(uses)}}})


def edge(name,src,dst):
    return dict(id=name,src=dict(part=src,bus='fwd'),dst=dict(part=dst,bus='rx'))


def test_one_real_source_fanout_is_one_electrical_net(monkeypatch):
    p=fixture(monkeypatch,[edge('two','a','b'),edge('one','a','c')])
    n=landing_route.network(p)
    assert n['wires']==['landing_one']
    assert n['bindings']['a']['fwd']==n['bindings']['b']['rx']==n['bindings']['c']['rx']


def test_two_real_sources_cannot_be_shortened_together(monkeypatch):
    p=fixture(monkeypatch,[edge('one','a','b'),edge('two','d','b')])
    with pytest.raises(ValueError,match='2 drivers'):
        landing_route.network(p)


def test_start_boundary_is_explicit_provisional_not_tied(monkeypatch):
    p=fixture(monkeypatch,[edge('one','a','b')],[dict(part='b',pin='start',net='pst_b')])
    n=landing_route.network(p)
    assert n['provisional']==['pst_b'] and 'pst_b' not in n['wires']
    assert n['bindings']['b']['start']=='pst_b'


def test_start_boundary_cannot_replace_existing_receiver(monkeypatch):
    p=fixture(monkeypatch,[edge('one','a','b')],[dict(part='b',pin='rx',net='pst_b')])
    with pytest.raises(ValueError,match='conflicts'):
        landing_route.network(p)


def test_unknown_physical_endpoint_fails(monkeypatch):
    e=edge('one','a','b');e['dst']['bus']='missing'
    with pytest.raises(ValueError,match='unknown physical'):
        landing_route.network(fixture(monkeypatch,[e]))


def test_route_optin_connects_exact_scalar_pins_and_exposes_boundary(monkeypatch):
    import die_trial as DT
    p=fixture(monkeypatch,[edge('one','a','b')],[dict(part='b',pin='start',net='pst_b')])
    p.name='t';p.ports={}
    monkeypatch.setattr(DT,'standin_module_names',lambda p:{tn:'m_'+tn for tn in p.types})
    default,_=DT.route_netlist(p,{tn:{} for tn in p.types})
    assert 'landing_' not in default and 'pst_b' not in default
    active,_=DT.route_netlist(p,{tn:{} for tn in p.types},landing_infra=True)
    assert 'input pst_b;' in active and '.start(pst_b)' in active
    assert '.fwd(landing_one)' in active and '.rx(landing_one)' in active
    assert "1'b" not in active


def test_abstract_optin_has_exact_physical_pin_rectangle(monkeypatch):
    import die_trial as DT
    p=fixture(monkeypatch,[])
    p.layer_budget={'partition_signal_max':'M7'}
    p.types['src'].update(outline_um=[100,100],module='m')
    monkeypatch.setattr(DT.gen_phys,'type_pins',lambda p,t:[])
    monkeypatch.setattr(DT.gen_phys,'tap_pins',lambda p,t:[])
    default,_=DT.abstract_lef(p,'src')
    active,_=DT.abstract_lef(p,'src',landing_infra=True)
    assert 'PIN fwd' not in default
    assert 'PIN fwd' in active and 'DIRECTION OUTPUT' in active
    assert 'RECT 1.9600 1.7840 2.0400 2.2160' in active


def test_real_start_launch_is_output_boundary_not_an_input_driver(monkeypatch):
    import die_trial as DT
    p=fixture(monkeypatch,[],[dict(part='a',pin='fwd',net='rs_a'),
                            dict(part='b',pin='start',net='pst_b')])
    p.name='t';p.ports={}
    monkeypatch.setattr(DT,'standin_module_names',lambda p:{tn:'m_'+tn for tn in p.types})
    n=landing_route.network(p)
    assert n['boundary_outputs']==['rs_a'] and n['boundary_inputs']==['pst_b']
    v,_=DT.route_netlist(p,{tn:{} for tn in p.types},landing_infra=True)
    assert 'output rs_a;' in v and 'input rs_a;' not in v and '.fwd(rs_a)' in v


def test_real_child_and_virtual_start_fanout_share_single_output_connection(monkeypatch):
    import die_trial as DT
    p=fixture(monkeypatch,[edge('real_child','a','b')],
              [dict(part='a',pin='fwd',net='rs_a'),dict(part='c',pin='start',net='pst_c')])
    p.name='t';p.ports={}
    monkeypatch.setattr(DT,'standin_module_names',lambda p:{tn:'m_'+tn for tn in p.types})
    n=landing_route.network(p)
    assert n['boundary_aliases']=={'rs_a':'landing_real_child'}
    assert n['bindings']['a']=={'fwd':'landing_real_child'}
    v,_=DT.route_netlist(p,{tn:{} for tn in p.types},landing_infra=True)
    assert 'assign rs_a = landing_real_child;' in v and 'output rs_a;' in v
    assert v.count('.fwd(landing_real_child)')==1 and '.fwd(rs_a)' not in v
    assert 'input rs_a;' not in v


def test_monitor_route_uses_segments_and_exact_fixed_access_sites(monkeypatch):
    import die_trial as DT
    import sta_landing_top

    sites = [
        dict(id=f'rl_a_{index}', kind='fwd_clock_relay', xy_um=[x, 6.345])
        for index, x in enumerate((40.0, 80.0), 1)
    ]
    edges = [
        dict(id=f'cland_mon_{bus}__a', src=dict(part='a', bus=bus), dst=dict(part='b', bus=bus),
             kind='clock' if bus == 'clk' else 'ctl', relay_group='cland_mon__a', relays=sites)
        for bus in ('ready', 'fault', 'clk')
    ]
    plan = fixture(monkeypatch, edges)
    for typ, direction in (('src', 'out'), ('dst', 'in')):
        pins = plan.types[typ]['clock']['landing_contract']['pins']
        pins.extend(dict(name=bus, dir=direction) for bus in ('ready', 'fault', 'clk'))

    network = landing_route.network(plan)
    relays = network['monitor_relays']
    assert network['edges'] == 3
    assert len(network['wires']) == 9
    for bus in ('ready', 'fault', 'clk'):
        assert network['bindings']['a'][bus] == relays['u_cland_rl1_a']['bindings'][f'{bus}_i']
        assert relays['u_cland_rl1_a']['bindings'][f'{bus}_o'] == relays['u_cland_rl2_a']['bindings'][f'{bus}_i']
        assert relays['u_cland_rl2_a']['bindings'][f'{bus}_o'] == network['bindings']['b'][bus]
        assert network['bindings']['a'][bus] != network['bindings']['b'][bus]

    plan.name = 'example'
    plan.ports = {}
    monkeypatch.setattr(DT, 'standin_module_names', lambda p: {tn: 'm_' + tn for tn in p.types})
    routed, _ = DT.route_netlist(plan, {tn: {} for tn in plan.types}, landing_infra=True)
    assert routed.count('ot_landing_monitor_fwd_route u_cland_rl') == 2
    first = relays['u_cland_rl1_a']
    assert landing_route.monitor_route_origin(first) == pytest.approx((37.84, 6.21))
    lef = landing_route.monitor_route_lef({first['form']})
    assert 'SIZE 4.3200 BY 0.2700' in lef
    assert all(f'PIN {bus}_{suffix}' in lef for bus in ('ready', 'fault', 'clk') for suffix in ('i', 'o'))
    with pytest.raises(ValueError, match='actual mapped and clocked relay cells'):
        sta_landing_top.apply('', network, None)
