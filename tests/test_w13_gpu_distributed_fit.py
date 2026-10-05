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


def test_all_32_boxes_channels_root_and_service_macros_share_one_frame():
    for row in fit.compose()['rows']:
        w,h=row['array_including_reserved_channels_um']
        assert row['array_bbox_um']==[0,0,w,h]
        assert row['geometry_audit']['pass_all']
        assert row['geometry_audit']['checked_macros']==656
        for sm in row['analytical_SM_placements']:
            x0,y0,x1,y1=sm['bbox_um']
            assert 0<=x0<x1<=w and 0<=y0<y1<=h
        for i,a in enumerate(row['analytical_SM_placements']):
            assert not any(fit.overlaps(a['bbox_um'],b['bbox_um']) for b in row['analytical_SM_placements'][i+1:])
        for region in row['reserved_regions']:
            assert fit.contains(row['array_bbox_um'],region['bbox_um'])
        for i,a in enumerate(row['reserved_regions']):
            assert not any(fit.overlaps(a['bbox_um'],b['bbox_um']) for b in row['reserved_regions'][i+1:])
        origin=row['array_die_origin_um']
        assert row['array_absolute_die_bbox_um']==[origin[0],origin[1],origin[0]+w,origin[1]+h]


def test_geometry_audit_rejects_outside_SM_corridor_overlap_and_service_overrun():
    import copy
    row=fit.compose()['rows'][0]
    def audit(r):
        return fit.audit_geometry(r['array_bbox_um'],r['core_bbox_um'],r['reserved_regions'],r['analytical_SM_placements'],r['service_macro_grids'])
    r=copy.deepcopy(row)
    r['analytical_SM_placements'][7]['bbox_um'][2]=row['array_bbox_um'][2]+1
    assert not audit(r)['pass_all']
    r=copy.deepcopy(row)
    root=next(x for x in r['reserved_regions'] if x['name']=='root_router')
    root['bbox_um'][0]-=1
    assert any(x.startswith('region_overlap:') for x in audit(r)['issues'])
    r=copy.deepcopy(row)
    r['service_macro_grids'][0]['bbox_um'][3]=1501
    assert any(x.startswith('grid_outside_band:') for x in audit(r)['issues'])
    r=copy.deepcopy(row)
    r['service_macro_grids'][0]['macros'][0]=r['service_macro_grids'][0]['macros'][1][:]
    assert any(x.startswith('macro_overlap:') for x in audit(r)['issues'])


def test_original_candidate_bytes_remain_but_original_frame_fails_extent_check():
    import hashlib,json
    p=Path(__file__).resolve().parents[1]/'results/physical_abi3/asap7/gpu/w13_distributed_ordinary_gpu_20261001/candidate_24lane_128credit.json'
    assert hashlib.sha256(p.read_bytes()).hexdigest()=='f309ca1690d09d7c4249b4fc550db70e99f2d203f8730a195ac093efdd21dcee'
    for row in json.loads(p.read_text())['rows']:
        w,h=row['array_including_reserved_channels_um']
        assert sum(not fit.contains([0,0,w,h],sm['bbox_um']) for sm in row['analytical_SM_placements'])==11
