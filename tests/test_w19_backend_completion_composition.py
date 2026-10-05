import importlib.util,tempfile
from pathlib import Path
from decimal import Decimal
import pytest
spec=importlib.util.spec_from_file_location('composition',Path(__file__).resolve().parents[1]/'tools/w19_backend_completion_composition.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_real_bench_callbacks_are_distinct_from_final_consumer_credit():
    r=m.build();p=r['callback_replay'];assert p['backing_commits']==4
    assert p['backend_slots_free_before_frontend_done']
    assert p['credit_release_ps']=='122500'
    a=r['once_only_area'];assert Decimal(a['backend_storage_subcomponent_mm2'])+Decimal(a['backend_nonstorage_subcomponent_mm2'])==Decimal(a['backend_total_addon_mm2'])
    assert Decimal(a['backend_plus_frontend_addon_mm2'])==Decimal('.1100191744')
    assert not a['storage_added_again']
    assert not r['graph_service_costs_bound'] and not r['engine_RTL_build_ready']
    assert r['full_token_cycles'] is None

@pytest.mark.parametrize('mutation',[lambda e,c:e[0].update(consumer_done_ps=25000),lambda e,c:e[0].update(visible_ps=e[0]['column_ps']),lambda e,c:c[0].update(sector=c[0]['sector']+1)])
def test_composed_provider_early_completion_and_wrong_identity_rejected(mutation):
    with tempfile.TemporaryDirectory() as d:
        s=m.load_sources(d)
        with pytest.raises(ValueError):m.replay(s['provider'],s['completion'],mutation)
