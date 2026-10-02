import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_D1_native_join as m

def good():return dict(verdict='PASS_OBJECT_SHARD_ONLY',exit_code=0,missing_targets=[],source_head=m.SOURCE,node='VM',runtime_authorized=False,argv=['make','D1_VM_SHARD'],input_hashes_verified=4353)
@pytest.mark.parametrize('field,value',[('verdict','ACTIVE'),('exit_code',1),('missing_targets',['a.o']),('source_head','wrong'),('node','local'),('runtime_authorized',True),('argv',['make','__ALL.a']),('input_hashes_verified',0)])
def test_terminal_or_source_failure_rejects_before_join(field,value):
 r=good();r[field]=value
 with pytest.raises(ValueError):m.receipt_valid(r,'VM')
def test_correct_receipt():m.receipt_valid(good(),'VM')
def test_implicit_cpp_basename_and_explicit_output():
 assert m.compiler_targets('/usr/bin/g++-11 -O0 -c first.cpp\n/usr/bin/g++-11 -O0 -c second.cpp -o second.o')==['first.o','second.o']
@pytest.mark.parametrize('line',['g++-11 -x c++-header -c pch.h','g++-11 -shared lib.a'])
def test_pch_or_unknown_compile_rejected(line):
 with pytest.raises(ValueError):m.compiler_targets(line)
def test_original_order_not_worker_completion_order():
 names=['Vtb___024root__0.o','Vtb_ot_hdc_v41x_attn_tile__0.o','Vtb___024root__0__Slow.o'];a={names[0]:Path('local')};b={names[2]:Path('slow'),names[1]:Path('attn')}
 assert [x[0] for x in m.join_inventory(names,a,b)]==names
@pytest.mark.parametrize('mutation',['missing','foreign','duplicate_owner'])
def test_incomplete_or_wrong_ownership_rejected(mutation):
 names=['Vtb___024root__0.o','Vtb_ot_hdc_v41x_attn_tile__0.o'];a={names[0]:Path('local')};b={names[1]:Path('remote')}
 if mutation=='missing':b.clear()
 if mutation=='foreign':b['alien.o']=Path('alien')
 if mutation=='duplicate_owner':b[names[0]]=Path('duplicate')
 with pytest.raises(ValueError):m.join_inventory(names,a,b)
