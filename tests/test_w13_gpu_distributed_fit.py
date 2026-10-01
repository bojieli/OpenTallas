import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('fit', Path(__file__).resolve().parents[1]/'tools/w13_gpu_distributed_fit.py')
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


def test_candidate_conserves_full_element_resources_and_stays_unqualified():
    j = fit.compose()
    assert j['coarse_resource_candidate']
    assert not j['physical_build_ready'] and not j['adopt'] and j['speed_credit']==0
    for row in j['rows']:
        assert len(row['analytical_SM_placements']) == 32
        assert row['credits_fit'] and row['network_reservation_fit']
        assert row['service_reservation_fit'] and row['geometry_fit']
        assert row['vertical']['tracks'] == 2*24*(256+64+4)
    assert j['compiler_contract']['actual_general_SIMT_lanes']==0
    assert j['compiler_contract']['shared_B_fast_cycle_equivalent']==96


def test_rejects_narrow_links_insufficient_credits_and_undersized_whole_slot():
    assert not fit.compose(lanes=16)['coarse_resource_candidate']
    assert not fit.compose(credits=64)['coarse_resource_candidate']
    j=fit.compose(sm_w=1900,sm_h=2150)
    assert not j['rows'][0]['known_element_area_fit']
    assert not j['coarse_resource_candidate']


def test_backpressure_cannot_mint_credits_or_lose_packets():
    j=fit.link_calendar(128,115,n=1000,stall=2000)
    assert j['done'] and j['packets']==1000 and j['max_live']==128
    assert j['elapsed_fast_cycles']>=3000
    short=fit.link_calendar(2,115,n=1000)
    assert short['done'] and short['elapsed_fast_cycles']>50000
