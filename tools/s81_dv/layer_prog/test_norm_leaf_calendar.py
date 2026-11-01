import copy
import pytest
from layer_prog.norm_leaf_calendar import calendars,diagnose


def cohort(bare=(0,0,0,0,0),pdsk=(0,0,0,0,0)):
    rows=[]
    for sid in range(16):
        for leaf in range(5):
            rows.append(dict(slice=f'u_s_{sid//2}{"N"if sid&1 else "S"}',sid=sid,leaf=leaf,
                xr_command_to_leaf_boundary_edges=bare[leaf],vn_b_partial_to_xr_input_edges=0,
                pdsk_edges=pdsk[leaf],crossing_plus_pdsk_edges=bare[leaf]+pdsk[leaf]))
    return dict(schema='opentallas.s81.emitted_leaf_boundary_routes.v1',verdict='PASS_SELECTED_BOUNDARY_WIRING',
        source_top_sha256='actual_top',source_view_sha256='actual_view',leaves=rows)


def test_duplicate_crossing_ages_need_distinct_command_edges():
    report=cohort();result=diagnose(report)
    assert len(result['current_impossible_slices'])==16
    assert result['proposal']['pdsk']==[0,1,2,3,4]
    assert result['proposal']['parameter_value']==sum(k<<(3*k)for k in range(5))
    assert all(r['command_offsets']==[4,3,2,1,0]for r in result['proposal']['calendars'].values())
    assert result['proposal_adopted']is False and result['native_programme_qualified']is False


def test_reverse_pdsk_alone_hides_physical_alignment_conflict():
    result=diagnose(cohort(bare=(0,1,2,3,4),pdsk=(4,3,2,1,0)))
    assert len(result['current_impossible_slices'])==16
    assert result['proposal']['pdsk']==[0]*5
    assert all(r['alignment_offset']==4 and not r['duplicate_command_slots']for r in result['proposal']['calendars'].values())


def test_missing_or_wrong_route_refused():
    report=cohort();bad=copy.deepcopy(report);bad['leaves'].pop()
    with pytest.raises(ValueError,match='80-leaf'):calendars(bad)
    bad=copy.deepcopy(report);bad['leaves'][0]['crossing_plus_pdsk_edges']+=1
    with pytest.raises(ValueError,match='edge sum'):calendars(bad)
    bad=copy.deepcopy(report);bad['leaves'][1]=bad['leaves'][0]
    with pytest.raises(ValueError,match='five distinct'):calendars(bad)


def test_wrong_source_sid_refused():
    report=cohort();report["leaves"][0]["sid"]=15
    with pytest.raises(ValueError,match="SID identity"):calendars(report)
