"""Literal source initialization gate and owned-contract negative cases."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_owned_binary_source_gate as G

def test_connected_literal_binary_init_is_conditional(tmp_path):
 r=G.run(tmp_path/'good')
 assert r['status']=='PASS_LITERAL_BINARY_METADATA_CONDITIONAL_ONLY'
 assert r['retained_cell_instances']==85
 assert r['actual_parent_driven_initialization_contract'] is False
 assert r['physical_control_survival'] is r['contextual_SSFF'] is False
 assert 'ticks=237' in (tmp_path/'good'/'run.log').read_text()

@pytest.mark.parametrize('mutant,reason',[('missing_mask_reset','unqualified payload observation'),('accepted_Z','accepted instruction not binary')])
def test_source_contract_mutants_are_detected_by_semantic_checks(tmp_path,mutant,reason):
 r=G.run(tmp_path/mutant,mutant)
 assert r['status']=='FAIL_LITERAL_BINARY_METADATA'
 assert r['returncode']!=0
 assert reason in (tmp_path/mutant/'run.log').read_text()

def test_prior_failure_receipt_is_immutable(tmp_path):
 out=tmp_path/'old';out.mkdir();p=out/'terminal.json';p.write_text('prior FAIL')
 with pytest.raises(ValueError,match='refuse overwrite'):G.run(out)
 assert p.read_text()=='prior FAIL'
