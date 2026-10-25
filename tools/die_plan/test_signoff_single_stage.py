import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pytest
import signoff
from test_signoff import record


def zero_pair_record():
    rec=record()
    for c in ('tt','ff'):
        ps=rec['corners'][c]['pair_skew']
        ps['census']=dict(done=1,status='PASS',registers=3,clocked=3,missing_clock=0,
                          missing_arrival=0,internal_pairs_any=0,data_pins=3)
        for value in ps['checks'].values():
            value.update(n=0,worst_abs_ps=None,worst_signed_ps=None,worst_crpr_ps=None,
                         bounded=False,nopath=0,verify_ps=0)
    return rec


def test_zero_internal_paths_have_null_metric_and_vacuous_applicability():
    r=signoff.evaluate(zero_pair_record())
    assert r['verdict']=='SIGNED'
    for c in ('tt','ff'):
        ps=r['checks']['clock']['by_corner'][c]['pair_skew']
        assert ps['applicability']=='no_internal_sequential_paths'
        assert all(v['worst_abs_ps'] is None for v in ps['checks'].values())


@pytest.mark.parametrize('field,value',[('done',0),('status','FAIL'),('registers',0),('registers',float('inf')),('registers','3'),('clocked',2),
                                        ('missing_clock',1),('missing_arrival',1),('internal_pairs_any',1)])
def test_incomplete_or_nonzero_structural_census_cannot_excuse_empty_pairs(field,value):
    r=zero_pair_record();r['corners']['ff']['pair_skew']['census'][field]=value
    assert signoff.evaluate(r)['checks']['clock']['verdict']=='FAIL'


def test_missing_census_fails_closed():
    r=zero_pair_record();del r['corners']['tt']['pair_skew']['census']
    assert signoff.evaluate(r)['checks']['clock']['verdict']=='FAIL'


def test_fake_zero_census_cannot_waive_measured_active_pair():
    r=zero_pair_record();r['corners']['ff']['pair_skew']['checks']['min'].update(n=1,worst_abs_ps=81.0)
    assert signoff.evaluate(r)['checks']['clock']['verdict']=='FAIL'


def test_boundary_hold_still_must_close():
    r=zero_pair_record()
    bad=record(ff_hold=-1)
    r['corners']['ff'].update({k:v for k,v in bad['corners']['ff'].items() if k!='pair_skew'})
    assert signoff.evaluate(r)['checks']['clock']['verdict']=='PASS'
    assert signoff.evaluate(r)['verdict']=='NOT SIGNED'


def test_parser_preserves_no_metric_instead_of_inventing_zero():
    p=signoff.pair_skew_result({'PAIR_DONE':'1','PAIR_max':'n 0 worst NA bounded 0 nopath 0',
        'PAIR_min':'n 0 worst NA bounded 0 nopath 0','PAIR_CENSUS':
        'done 1 status PASS registers 3 clocked 3 missing_clock 0 missing_arrival 0 internal_pairs_any 0 data_pins 3'})
    assert signoff.no_internal_sequential_paths(p)
    assert p['checks']['max']['worst_abs_ps'] is None
