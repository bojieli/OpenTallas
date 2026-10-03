import ast,importlib.util,json,types
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('review',Path(__file__).resolve().parents[1]/'tools/ds_r68_physical_admission_review.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def actual_source_guard(proof):
    """Compile only archived actual page_proof; injected metadata IO, no provider."""
    class Meta:
        def __init__(self,value):self.value=value
        def read_bytes(self):return json.dumps(self.value).encode()
        def read_text(self):return 'device / ext4 rw 0 0\n'
    def path(value):
        if value=='/proof.json':return Meta(proof)
        if value=='/proc/mounts':return Meta(None)
        return Path(value)
    namespace={'Path':path,'json':json,'remote':types.SimpleNamespace(fresh_admission=lambda plan:{'available_RAM_bytes':10**15})}
    tree=ast.Module(body=[m.page_proof_ast()],type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree),'<ARCHIVED_R68_PAGE_PROOF_ONLY>','exec'),namespace)
    return namespace['page_proof']

def plan_and_proof(component,available):
    plan={'output_root':'/home/ubuntu/ds-hbm-pc01-r68-run-20261003','resolved_output_root':'/home/ubuntu/ds-hbm-pc01-r68-run-20261003','component_model_sha256':'pinned','constructor_parent_proof':'/proof.json','runtime_parent_proof':'/proof.json'}
    model={'constructor_projection':{'required_RAM_bytes':component},'runtime_projection':{'required_RAM_bytes':component}}
    proof={'actual_output_root':plan['output_root'],'physical_membership_verified':True,'write_set_source_model_sha256':'pinned','write_set_COW_overlap_reviewed':True,'allocator_page_upper_bytes':component,'filecache_page_upper_bytes':0,'page_tables_and_kernel_upper_bytes':0,'guest_extra_page_upper_bytes':0,'physical_new_page_union_upper_bytes':component,'other_owned_reservations_and_live_growth_bytes':0,'MemAvailable_bytes':available}
    return plan,model,proof

def test_actual_source_refuses_runtime_even_zero_extra_cost():
    p,v,proof=plan_and_proof(71264523536,59949887488)
    with pytest.raises(ValueError,match='physical touched-page aggregate admission fails'):actual_source_guard(proof)(p,v,'runtime')

@pytest.mark.parametrize('field',['allocator_page_upper_bytes','filecache_page_upper_bytes','page_tables_and_kernel_upper_bytes','guest_extra_page_upper_bytes','physical_new_page_union_upper_bytes'])
def test_actual_unknown_costs_failclosed(field):
    p,v,proof=plan_and_proof(100,200);proof[field]=None
    with pytest.raises(ValueError,match='complete physical page inventory'):actual_source_guard(proof)(p,v,'constructor')

def test_no_arbitrary_allocator_discount():
    p,v,proof=plan_and_proof(100,200);proof['allocator_page_upper_bytes']=99
    with pytest.raises(ValueError,match='source component cannot be lowered'):actual_source_guard(proof)(p,v,'constructor')

def test_unpriced_union_exclusion_refused():
    p,v,proof=plan_and_proof(100,200);proof['filecache_page_upper_bytes']=10
    with pytest.raises(ValueError,match='unproved touched-page exclusion'):actual_source_guard(proof)(p,v,'constructor')

def test_peer_growth_must_remain_reserved():
    p,v,proof=plan_and_proof(100,110);proof['other_owned_reservations_and_live_growth_bytes']=11
    with pytest.raises(ValueError,match='physical touched-page aggregate'):actual_source_guard(proof)(p,v,'constructor')

def test_nominal_margin_never_certifies_unknown_pages():
    v=m.certificate_floor(component_bytes=40,host_available_bytes=60,reserved_bytes=0)
    assert v['additional_cost_allowance_bytes']==20 and not v['admission']

def test_source_model_current_values_and_no_smoke_admission():
    v=m.model();assert v['full_native_PCs']==2213 and v['full_homes']==290730
    assert v['checkpoints']==2 and v['runtime_journals']==3 and v['additional_constructor_journals']==2
    assert v['stage_results']['runtime']['additional_cost_allowance_bytes']==-11314636048
    assert not v['resource_admission'] and v['old_R64_R67_guards_unchanged']
