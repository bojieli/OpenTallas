"""Physical screen tests cover rejection and actual LEF inventory, not closure."""
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hbrom_floorplan as fp


def fixture():
    selected={'geometry':{'clusters_per_die':4},'candidate':{'tiles_per_cluster':1,'pairs_per_tile':8}}
    inputs={'compute':{'area_mm2':.2},'macro':{'capture_area_per_pair_mm2':.0002},
            'networks':{'8':{'output_streams_per_tile':4,'area_mm2':.02}},
            'physical_floorplan':{'compute_tile_um':[500,500],'hub_um':[8000,5000], 'hbm_phy_count':4}}
    return selected, inputs


def test_real_macro_inventory_and_reserved_channels():
    s,i=fixture();r=fp.derive(s,i)
    assert r['geometric_fit'],r['geometric_errors']
    assert r['inventory']['rom_macro']==64
    assert r['inventory']['capture_reservation']==64
    assert r['inventory']['mux_reservation']==4
    assert r['routing']['tracks_available']>=r['routing']['tracks_needed']
    assert r['routing']['macro_obs']==['M1','M2','M3','M4']
    assert not r['qualified'] and not r['complete_inventory']


def test_insufficient_rectangle_capacity_fails_closed():
    s,i=fixture();s['geometry']['clusters_per_die']=100000
    r=fp.derive(s,i)
    assert not r['geometric_fit']
    assert 'ROM instance inventory incomplete' in r['geometric_errors']


def test_undersized_compute_rectangle_rejected():
    s,i=fixture();i['physical_floorplan']['compute_tile_um']=[10,10]
    assert 'compute tile rectangle smaller than modeled area' in fp.derive(s,i)['geometric_errors']


def test_overlap_containment_and_duplicate_checks():
    a={'name':'x','x':1,'y':1,'w':2,'h':2}
    b=copy.deepcopy(a);b['x']=2
    errors=fp.check_rectangles([a,b],[3,3])
    assert any('duplicate' in e for e in errors)
    assert any('overlap' in e for e in errors)
    assert any('outside' in e for e in errors)


def test_touching_edges_legal_and_unknown_inventory_blocked():
    a={'name':'x','x':0,'y':0,'w':2,'h':2}
    b={'name':'y','x':2,'y':0,'w':2,'h':2}
    assert fp.check_rectangles([a,b],[4,2])==[]
    s,i=fixture();i.pop('physical_floorplan');r=fp.derive(s,i)
    assert any('area-derived' in e for e in r['qualification_blockers'])


def test_full_free_area_and_shared_cluster_service():
    s,i=fixture()
    i['compute']['private_tile_area_mm2']=.05
    i['compute']['shared_service_area_mm2']=.15
    i['physical_floorplan'].pop('compute_tile_um')
    s['candidate']['tiles_per_cluster']=4
    g=fp.placement_geometry(i,8,4)
    phy=fp.lef(fp.ROOT/fp.PHY)
    expected=(25600-400)*(31800-400-2*(phy['height']+40))-8000*5000
    assert abs(sum(r[2]*r[3] for r in g['regions'])-expected)<1e-5
    r=fp.derive(s,i)
    assert r['geometric_fit'],r['geometric_errors']
    assert r['inventory']['shared_service_reservation']==4
    shared=[a for a in r['rectangles'] if a['kind']=='shared_service_reservation']
    assert abs(sum(a['w']*a['h'] for a in shared)-4*.15*1e6)<1e-5
    assert r['inventory']['compute_sram_reservation']==16
