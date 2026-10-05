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
