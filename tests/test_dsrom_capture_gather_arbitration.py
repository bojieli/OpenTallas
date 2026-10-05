import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_gather_arbitration as G
import dsrom_capture_physical_shard_paths as P

def test_static_runs_all_ordered_rows():
 a=G.Arbiter((1,2,3))
 for row in range(576):assert a.accept(row,P.owner(row)['physical_shard'],(1,2,3),True,True,True,True)
 assert a.next_row==576
 assert G.runs()==[{'shard':0,'first_row':0,'last_row':127},{'shard':1,'first_row':128,'last_row':255},{'shard':0,'first_row':256,'last_row':383},{'shard':1,'first_row':384,'last_row':511},{'shard':0,'first_row':512,'last_row':575}]

@pytest.mark.parametrize('fault',['row','shard','ctx','rawvalid','seat'])
def test_alias_or_optimistic_return_refused(fault):
 x=[0,0,(1,),True,True,True,True]
 if fault=='row':x[0]=1
 if fault=='shard':x[1]=1
 if fault=='ctx':x[2]=(2,)
 if fault=='rawvalid':x[4]=False
 if fault=='seat':x[5]=False
 a=G.Arbiter((1,))
 with pytest.raises(ValueError):a.accept(*x)
 assert a.next_row==0

def test_hold_does_not_retire_or_choose_capacity():
 a=G.Arbiter((1,));assert not a.accept(0,0,(1,),True,True,True,False);assert a.next_row==0
 m=G.build();assert m['credit_capacity_C'] is None
 assert m['gross_arbiter_minimum_state']['cell_body_um2']>0
 assert m['gross_arbiter_minimum_state']['containment_or_replacement_in_prior1483_control_bits'] is None
 assert not m['contextual_PR_admitted']
