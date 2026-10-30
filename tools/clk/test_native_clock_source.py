import copy
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('native_clock_source',Path(__file__).with_name('native_clock_source.py'))
N=importlib.util.module_from_spec(spec);spec.loader.exec_module(N)

TEXT='''module ctree(input root, output t_p__clk);
 CKINVDCx16_ASAP7_75t_R b99 (.A(root), .Y(n99));
 CKINVDCx16_ASAP7_75t_R r7_hash (.A(n99), .Y(n7));
 assign t_p__clk = n7;
endmodule
'''
TREE=dict(sites={'b99':[1.08,2.16],'r7_hash':[3.24,2.16]},taps=[dict(port='t_p__clk',part='p',tap='clk',xy=[5,6])])

def test_new_ids_are_built_from_graph_without_old_id_inventory():
 t=copy.deepcopy(TREE);g=N.clock_graph(TEXT,t)
 assert t==TREE
 assert g['cells']['b99']['inst']=='ck_b99'
 assert g['nets']['n99']['loads']==[dict(inst='ck_r7_hash',pin='A')]
 assert g['nets']['n7']['loads']==[dict(inst='p',pin='clk',port='t_p__clk')]
 assert g['aliases']=={'t_p__clk':'n7'}

@pytest.mark.parametrize('fault',['missing_site','extra_site','unknown_alias','duplicate_alias','unused','cycle','wrong_pin','two_drivers'])
def test_mismatched_or_invalid_graphs_fail_before_native_mutation(fault):
 text=TEXT;t=copy.deepcopy(TREE)
 if fault=='missing_site':del t['sites']['b99']
 if fault=='extra_site':t['sites']['old_b0']=[1,2]
 if fault=='unknown_alias':text=text.replace('assign t_p__clk','assign unknown')
 if fault=='duplicate_alias':text=text.replace('endmodule','assign t_p__clk = n7;\nendmodule')
 if fault=='unused':text=text.replace('.A(n99)', '.A(root)')
 if fault=='cycle':text=text.replace('.A(root)', '.A(n7)')
 if fault=='wrong_pin':text=text.replace('.Y(n99)', '.Q(n99)')
 if fault=='two_drivers':text=text.replace('.Y(n7)', '.Y(n99)')
 with pytest.raises(ValueError):N.clock_graph(text,t)

def test_native_row_legalization_keeps_graph_and_exact_anchors():
    tree=dict(sites={'a':[.027,0.0],'b':[.054,0.0]},node_buf={'0':'a','1':'b'},
              nodes={'0':dict(x=.027,y=0.0),'1':dict(x=.054,y=0.0)},parent_of={'b':'a'},meta={})
    graph=dict(cells={n:dict(xy_um=xy,width_dbu=108) for n,xy in tree['sites'].items()})
    before=copy.deepcopy(tree)
    rows=[dict(x0=0,y=y,x1=1000,spacing=54) for y in [0,540]]
    out,report=N.legalize_sites(graph,tree,rows,1000)
    assert tree==before
    assert out['sites']['b']==[.054,0.0]
    assert out['sites']['a']==[.162,0.0]
    assert out['nodes']['0']['x']==.162
    assert out['parent_of']==tree['parent_of']
    assert report['added_cells']==report['cycles_added']==0
    assert report['moved']==1


def test_legalized_tcl_requires_exact_graph_coverage():
    text='place_inst -name a -location {.027 0.0} -status PLACED\n'
    out=N.rewrite_clock_tcl(text,{'a':[.162,0.]})
    assert '-location {0.162 0.000}' in out
    with pytest.raises(ValueError):N.rewrite_clock_tcl(text,{'a':[.162,0.],'missing':[0.,0.]})
