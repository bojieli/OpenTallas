"""Real SAT regressions on literal source launch sampling, not engine proof."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_literal_launch_pipeline_gate as Q

def test_literal_launch_base_and_induction_with_all_fields(tmp_path):
 r=Q.run(tmp_path/'positive')
 assert r['status']=='PASS_LITERAL_BINARY_PIPELINE_INDUCTION'
 assert r['base_returncode']==r['induction_returncode']==0
 assert r['IBW']==379 and r['vector_width']==128 and r['source_fields_change_every_edge']
 assert r['actual_parent_ready_owner'] is r['vector_owner_and_read_timing'] is r['physical_source_admission'] is False

@pytest.mark.parametrize('mutant',['ungated_go','payload_bit','missing_go_reset'])
def test_mutants_require_actual_sat_counterexample_not_collector_failure(tmp_path,mutant):
 p=tmp_path/mutant;r=Q.run(p,mutant)
 assert r['status']=='FAIL_LITERAL_BINARY_PIPELINE_INDUCTION' and r['base_returncode']!=0
 assert 'proof did fail' in (p/'base.log').read_text()
 assert (p/'counterexample.vcd').is_file()


def test_literal_extractor_rejects_source_field_order_change(tmp_path,monkeypatch):
 for name in (Q.SPINE,Q.TILE):
  p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((Q.ROOT/name).read_bytes())
 p=tmp_path/Q.SPINE
 p.write_text(p.read_text().replace('ib = {i_nout, i_tiles','ib = {i_tiles, i_nout'))
 monkeypatch.setattr(Q,'ROOT',tmp_path)
 with pytest.raises(ValueError,match='ordering'):Q.literal()
