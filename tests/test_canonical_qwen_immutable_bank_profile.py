import hashlib
import pytest
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
from tools.gpu_sys.canonical_qwen_banked_manifest_owner import bank_masks,mask_rom,required_banks
from tools.gpu_sys.canonical_qwen_immutable_bank_profile import lookup,generate,model

@pytest.fixture(scope='module')
def p():return SourcePlacement.released()

def test_all_native_PC_actor_masks_and_opaque_identity_preserved(p):
 normal,_=bank_masks(p)
 opaque=(0xfedcba9876543210<<175)|(0xf123456789abcdef<<100)|(0xe123456789abcdef<<36)
 for pc in range(1737):
  for actor in range(64):
   root=opaque|(pc<<164)|(actor<<30)|(2047<<19)|511
   assert lookup(p,root,True)==(True,normal[pc]|(1<<actor))
   assert lookup(p,root,False)==(False,0)

def test_INITIAL_exact_version_and_invalid_PC_failclosed(p):
 _,initial=bank_masks(p)
 for pc in range(1737,2048):
  for version in (0,1,2047):
   for actor in (0,31,32,63):
    root=(pc<<164)|(actor<<30)|(version<<19)
    valid,mask=lookup(p,root,True)
    assert valid==(pc==2047 and version in initial)
    assert mask==((initial[version]|(1<<actor)) if valid else 0)


def test_emitted_same_proven_ROM_no_clock_owner_or_FF(p,tmp_path):
 s=generate(tmp_path,p).read_text()
 assert mask_rom(p) in s
 assert 'parameter integer ENABLE=0' in s
 assert 'root_tuple[actor_port*239 +:239]' in s
 assert 'required_banks[actor_port*64 +:64]' in s
 assert '(64\'h1<<root[35:30])' in s
 assert 'posedge' not in s and 'negedge' not in s and 'always' not in s
 assert 'owner55' not in s and 'owner46' not in s


def test_model_debits_all_extra_ports_no_reuse_or_clock_credit(p):
 m=model(p);c=m['cost']
 assert c['additional_lookup_ports']==64 and c['additional_mutable_FF']==0
 assert c['NAND2_upper_bound']>0 and c['additional_body_area_estimate_mm2']>0
 assert c['shared_ROM_reuse_credit']==0 and c['loaded_delay_ps_unknown']
 assert not c['SSFF_clock_qualified'] and not m['semantics']['full_factory_ready']
 assert m['ROM_sha256']==hashlib.sha256(mask_rom(p).encode()).hexdigest()
