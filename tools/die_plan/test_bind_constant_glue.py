"""Actual keybuf pbase mux + lane add, with runtime/X/signed controls."""
from types import SimpleNamespace as N
import pytest
from tools.die_plan.bind import Graph, Rules


def make(base, lane, runtime=False, signed=False):
    cells=[]
    if runtime:
        cells.append(N(path='dynamic',module='leaf',kind='leaf',ports={'q':[99]},dirs={'q':'output'},params={}))
    mux=N(path='base',module='$mux',kind='glue',ytype='$mux',yparams={},params={},dirs={'A':'input','B':'input','S':'input','Y':'output'},ports={'A':['0']*3,'B':['0','0','1'],'S':[99 if runtime else str(base//4)],'Y':[10,11,12]})
    add=N(path='lane',module='$add',kind='glue',ytype='$add',yparams={'A_SIGNED':'1' if signed else '0','B_SIGNED':'1' if signed else '0'},params={},dirs={'A':'input','B':'input','Y':'output'},ports={'A':[10,11,12],'B':list(reversed(f'{lane:03b}')),'Y':[20,21,22,23]})
    cells += [mux,add]
    errors=[]
    return Graph(N(cells=cells,const_drivers={},top_ports={}),Rules({}),errors), errors


@pytest.mark.parametrize('base,lane',[(b,l) for b in (0,4) for l in range(4)])
def test_exact_static_mux_add_identity(base,lane):
    g,errors=make(base,lane)
    assert not errors
    assert sum(int(g.source(20+i)[1])<<i for i in range(4)) == base+lane


def test_runtime_or_unknown_selector_is_never_an_id_constant():
    for runtime,select in ((True,None),(False,'x')):
        g,_=make(4,2,runtime)
        if select is not None:g.F.cells[0].ports['S']=[select]
        assert all(g.source(20+i)[0]=='pin' for i in range(4))


def test_both_signed_inputs_extend_and_result_truncates():
    g,_=make(4,1,signed=True) # 3-bit -4 + 1 = 4-bit -3
    assert sum(int(g.source(20+i)[1])<<i for i in range(4))==13
    g,_=make(4,1,signed=True)
    g.F.cells[1].yparams['B_SIGNED']='0' # mixed operands zero-extend
    assert sum(int(g.source(20+i)[1])<<i for i in range(4))==5


def test_unknown_add_input_cannot_fold():
    g,_=make(4,1)
    g.F.cells[1].ports['B'][0]='x'
    assert g.source(20)[0]=='pin'
