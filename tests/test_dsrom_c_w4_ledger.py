import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).resolve().parents[1]/'tools/dsrom_c_w4_ledger.py'
s=importlib.util.spec_from_file_location('w4',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_attribution():
 d=m.build();assert d['increment_mm2']==pytest.approx(58.14742729288);assert d['historical_start_mm2']+sum(x['mm2'] for x in d['terms'])==pytest.approx(d['historical_end_mm2'])
def test_no_complement_credit():
 d=m.build();assert d['complement_credit_mm2']==0;assert d['unmapped_complement_mm2']==pytest.approx(287.02184985143);assert not d['physical_admitted'];assert not d['rate_adopted']
def test_union_overlap_not_doublecharged():assert m.union_area([[0,0,1000000,1000000],[500000,0,1500000,1000000]])==1.5
def test_required_shapes():
 d=m.build();assert len(d['source_sha256'])==7;assert all(x['rectangles'] is None and x['credit_mm2']==0 for x in d['replacement_requirements'].values())
def test_padding_policy_is_not_cell_credit():
 d=m.build();t={x['name']:x for x in d['terms']};assert t['field row whitespace']['kind']=='noncontainment policy';assert t['field row whitespace']['mm2']>11
