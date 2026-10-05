from pathlib import Path
import pytest
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
from tools.gpu_sys.canonical_qwen_banked_manifest_owner import bank_masks,required_banks,generate,model

@pytest.fixture(scope='module')
def p():return SourcePlacement.released()

def test_all_whole_operation_banks_exact_no_actor_storage_alias(p):
 normal,initial=bank_masks(p)
 expected_by_pc={pc:set() for pc in range(1737)}
 for h in p.rf.values():
  if h.birth>=0:expected_by_pc[h.birth].add(h.rank*32+h.sm)
  for pc in h.consumers:expected_by_pc[pc].add(h.rank*32+h.sm)
 for pc in range(1737):
  expected=expected_by_pc[pc]
  assert normal[pc]==sum(1<<b for b in expected)
  for actor in (0,33,63):
   assert required_banks(p,pc,actor)==normal[pc]|(1<<actor)
 for version,mask in initial.items():
  expected={h.rank*32+h.sm for h in p.rf.values() if h.birth<0 and p.version_ids[h.version]==version}
  assert mask==sum(1<<b for b in expected)
  assert required_banks(p,2047,33,version)==mask|(1<<33)


def test_invalid_native_and_INITIAL_refuse(p):
 for pc in (-1,1737,2046,2048):
  with pytest.raises(Exception):required_banks(p,pc,0)
 with pytest.raises(ValueError):required_banks(p,2047,0,2047)
 with pytest.raises(ValueError):required_banks(p,5,0,0)


def test_generated_bank_leaf_preserves_root_child_fields(p,tmp_path):
 s=generate(tmp_path,p).read_text()
 assert 'output wire [63:0] required_bank_mask64' in s
 assert 'bank_participates(claim_tuple)' in s
 assert 'root_member(t,bind_tuple)' in s
 assert 'query_tuple[238:30]==t[238:30]' in s
 assert 'assign required_output_rows=initial_root(bind_tuple)?(bank_has_initial' in s
 assert 'publish_page_mask==page_mask(publish_tuple)&&complete_outputs' in s
 assert '(!local_tuple(frame_retire_tuple)&&!initial_root(frame_retire_tuple))' in s
 assert 'assign workspace_held_valid=all_clean' in s
 assert 'b[B_TUPLE+35]==(SM_INDEX/32)' in s # only actual execution bank owns scratch
 assert 'initial_root=(operation_bank_mask' in s


def test_model_prices_mask_replication_without_new_owner_state(p):
 m=model(p)['bank_actor_composition']
 assert m['additional_mutable_FF']==0 and m['mask_read_ports']==192
 assert m['NAND2_upper_bound']>0 and not m['full_factory_ready']
 assert m['query_latency_edges']==5
