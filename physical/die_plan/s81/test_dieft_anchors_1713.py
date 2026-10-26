import ast
from pathlib import Path
import pytest


def layout():
    tree=ast.parse((Path(__file__).parent/'delta_dieft_1713.py').read_text())
    ns={'MARGIN':6.144,'FILL':.88}
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['layout','anchored_layout']]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'anchored-layout','exec'),ns)
    return ns['anchored_layout']


def test_leaf_contract_anchored_transit_spread_and_capacity_negative():
    ports=[{'id':n,'width':w,'layers':['M5','M7']}for n,w in [('ft0',1104),('leafdn',597),('ft1',668),('ft2',276)]]
    items=[(p,(p['width']+2)//2)for p in ports]
    preferred={'ft0':[6.144,240.],'leafdn':[450.,600.],'ft1':[250.,445.],'ft2':[610.,700.]}
    out=layout()(items,1000.,{'leafdn':preferred['leafdn']},preferred)
    assert out[1]==preferred['leafdn']
    for i,(a,b)in enumerate(out):
        assert 6.144<=a<b<=993.856
        if i!=1:assert (ports[i]['width']+1)/(b-a)<=5.81
    for i,(a,b)in enumerate(out):
        for c,d in out[i+1:]:assert min(b,d)-max(a,c)<=0
    with pytest.raises(ValueError,match='no leaf-anchored'):
        layout()(items,1000.,{'leafdn':[10.,990.]},preferred)
