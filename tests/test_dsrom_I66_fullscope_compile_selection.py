import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_I66_fullscope_compile_selection as M

def test_exact_source_selection_and_preserved_order():
    r=M.select();p=json.loads((M.ROOT/M.PRODUCER/'run_source_plan.json').read_text())
    assert r['source_census_count']==130
    assert len(r['selected_die_compile_order'])==len(p['die_compile_order'])==113
    assert len(set(r['selected_die_compile_order']))==113
    assert r['selected_die_compile_order']==[r['substitutions'].get(x,x) for x in p['die_compile_order']]
    assert r['required_parameters']==dict(I66_OBSERVE=1,ROM_PHW=10,ROM_FBW=1632,ROM_R=128,SUN=256)
    assert r['jobs_launched']==0 and not r['elaboration_pass']
    assert not r['complete_run_source_closure'] and r['qualified_F'] is None

def test_current_core_and_passive_top_only():
    r=M.select();rows={x['path']:x['sha256'] for x in r['selected_sources']}
    assert len(rows)==130
    for old,new in r['substitutions'].items():assert old not in rows and new in rows
    core='rtl/w17_runtime/hdc/v41x/ckvsel/ot_hdc_core_v41x.sv'
    assert rows[core]=='8f0f96712ad05393379dcbb3312c7616993697b7e2a5cc37aceb9556d106bde6'
    for path,h in rows.items():assert M.sha((M.ROOT/path).read_bytes())==h

def test_changed_current_core_rejected(monkeypatch):
    original=M.sha
    expected='8f0f96712ad05393379dcbb3312c7616993697b7e2a5cc37aceb9556d106bde6'
    monkeypatch.setattr(M,'sha',lambda b:'0'*64 if original(b)==expected else original(b))
    with pytest.raises(ValueError,match='current selected core'):M.select()
