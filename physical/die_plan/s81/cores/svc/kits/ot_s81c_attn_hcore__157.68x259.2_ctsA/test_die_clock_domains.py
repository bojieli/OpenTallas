"""Full PHY PG domains must alter the real clock netlist/RC, not only its picture."""
from types import SimpleNamespace
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import re
import pytest
import die_clock as D
import clock_corridor as C


def fixture():
    P=SimpleNamespace(W=100.,H=100.,parts={},types={},die={'pg':{'domains':[{'name':'phy','rect_um':[40,0,60,65]}]}})
    T=D.Tree();T.ports=[('input','root'),('output','tap')]
    T.cell('n0',10,50,'node',0);T.cell('n1',90,50,'node',1)
    T.nets=[dict(name='root',drv='port:root',branches=[(.001,'M8','n0',0)]),
            dict(name='leg',drv='n0',branches=[(80,'M8','n1',80)]),
            dict(name='tap',drv='n1',branches=[(30,'M9','port:tap',30)])]
    tree=dict(meta={'root_um':[10,50]},root_node='n0',nodes={
        'n0':dict(path=['n0'],xy=[10,50],kids=[['n1',[['leg',0]]]]),
        'n1':dict(path=['n0','n1'],xy=[90,50],kids=[])},
        taps=[dict(port='tap',xy=[90,80],path=['n0','n1'],pad_nets=[['tap',0]])])
    return P,T,tree


def test_corridor_changes_real_topology_and_mixed_layer_rc(tmp_path):
    P,T,tree=fixture()
    D.route_domain_tree(T,tree,P,clear_um=2,rep_um=20)
    assert tree['meta']['domain_corridors']['changed_edges']>0
    assert tree['meta']['domain_corridors']['repeaters']>0
    assert len(tree['taps'][0]['path'])>2
    box=(38,-2,62,67)
    assert all(not C.inside((c['x'],c['y']),box) for c in T.cells.values())
    assert all(not C.intersects(a,b,box) for n in T.nets for route in n['routes'] for a,b in zip(route,route[1:]))
    names={n['name'] for n in T.nets}
    assert len(names)==len(T.nets)
    assert all(nn in names for nd in tree['nodes'].values() for _,targets in nd['kids'] for nn,_ in targets)
    D.write_verilog(T,tmp_path/'ctree.v');D.write_spef(T,tmp_path/'ctree.spef')
    cap=sum(float(x) for x in re.findall(r'^\*D_NET \S+ ([0-9.]+)',(tmp_path/'ctree.spef').read_text(),re.M))
    assert cap>110*min(D.layer_rc('M8')[1],D.layer_rc('M9')[1])
    E,st=D.expand_pads(T,{('tap',0):1000})
    assert st>0
    assert all('routes' in n for n in E.nets)
    assert sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for n in E.nets for route in n['routes'] for a,b in zip(route,route[1:]))==pytest.approx(
        sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for n in T.nets for route in n['routes'] for a,b in zip(route,route[1:])))
    D.write_spef(E,tmp_path/'padded.spef')


def test_fixed_port_in_domain_fails_closed():
    P,T,tree=fixture();tree['taps'][0]['xy']=[50,50]
    with pytest.raises(ValueError,match='fixed clock ports'):
        D.route_domain_tree(T,tree,P,clear_um=2,rep_um=20)


def test_uniform_type_clock_keepout_is_transformed_per_instance():
    # A PHY window is wider than its analog core; keep all die clock buffers out
    # of the reserved region even on rotated copies of a shared partition type.
    P=SimpleNamespace(parts={'rot':{'type':'t'}},types={'t':{'clock':{'keepouts_um':[[1,2,11,22]]}}},die={})
    P.to_die=lambda part, xy:(100-xy[1],200+xy[0])
    assert D.keepouts(P)==[(78,201,98,211,'rot/clock_keepout_0')]
