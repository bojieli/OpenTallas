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
