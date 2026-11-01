import copy
import pytest
from layer_prog.test_norm_leaf_calendar import cohort
from layer_prog.norm_leaf_calendar import diagnose
from layer_prog.norm_candidate_book import book,encode_unsealed


def inputs():
    cal=diagnose(cohort(bare=(0,1,2,3,4),pdsk=(4,3,2,1,0)))
    ctl=dict(status='PASS_SELECTED_EMITTED_CTL_TO_XR',source_top_sha256='actual_top',source_view_sha256='actual_view',
        paths=[dict(slice=sl,calendar_command_to_XR_command_edges=7+5*r['sid'])for sl,r in cal['current'].items()])
    return cal,ctl


def test_actual_route_alignment_and_native_payloads():
    cal,ctl=inputs();p=book(cal,ctl,0x1e3ce508,families=2)
    ages={r['slice']:r['calendar_command_to_XR_command_edges']for r in ctl['paths']}
    assert len(p['rows'])==96 and len(encode_unsealed(p))==385
    assert len({(r['eng'],r['issue'])for r in p['rows']})==96
    assert p['latest_go_at_XR']<p['first_norm_issue']
    rows={r['tix']:r for r in p['rows']};templates={t['i']:int(t['payload186'],16)for t in p['templates']}
    for c in p['commands']:
        r=rows[c['template']];word=int(r['row76'],16)
        assert word>>52==c['issue']+5 and (word>>28)&0xffffff==c['issue'] and word&0xffffff==c['template']
        if c['kind']=='NORMR':
            leaf=c['leaf'];sl=c['slice'];body=templates[c['template']]>>26
            assert (body>>14)&1023==5*c['sid']+leaf and (body>>24)&255==2
            assert ((templates[c['template']]>>21)&31)==1<<leaf
            assert c['issue']+ages[sl]+cal['proposal']['calendars'][sl]['crossing_plus_pdsk_edges'][leaf]==c['partial_cohort_offset_excluding_common_local_age']
    assert p['actual_output_edges']is None and p['added_model_cycles']is None and not p['source_parameter_adopted']


def test_wrong_source_and_duplicate_candidate_slots_refused():
    cal,ctl=inputs();bad=copy.deepcopy(ctl);bad['source_top_sha256']='other'
    with pytest.raises(ValueError,match='source identities'):book(cal,bad,0x1e3ce508)
    bad=copy.deepcopy(cal);row=next(iter(bad['proposal']['calendars'].values()))
    row['crossing_plus_pdsk_edges'][0]=row['crossing_plus_pdsk_edges'][1]
    with pytest.raises(ValueError,match='collision'):book(bad,ctl,0x1e3ce508)
