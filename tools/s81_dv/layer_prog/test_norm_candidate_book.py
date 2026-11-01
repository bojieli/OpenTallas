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


def test_head_consumer_keeps_egress_flag_and_required_family():
    cal,ctl=inputs();p=book(cal,ctl,0x1e3ce508,families=2,consumer='head_final')
    for c in p['commands']:
        if c['kind']!='NORMR':continue
        payload=int(p['templates'][c['template']]['payload186'],16);body=payload>>26
        index=(body>>14)&1023
        assert index==128+5*c['sid']+c['leaf']
        assert index&127==c['global_beat'] and (body>>24)&255==2
    assert p['head_egress_flag']==128 and not p['native_job_sealed']
    for family in (1,3):
        with pytest.raises(ValueError,match='HEAD final requires'):book(cal,ctl,0x1e3ce508,families=family,consumer='head_final')
    with pytest.raises(ValueError,match='attention entry requires'):book(cal,ctl,0x1e3ce508,families=2,consumer='attention_entry')
