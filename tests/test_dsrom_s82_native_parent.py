import gzip,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s82_native_parent as M
@pytest.fixture(scope='module')
def d():return M.build()
def test_full_component_census(d):
 r=d['rectangles'];assert sum(a['kind']=='return_complete_native_NAND_INV_FF50' for a in r)==8064
 assert sum(a['kind']=='return_root_FF50_storage' for a in r)==128
 assert sum(a['kind'] in ('q','BF') for a in r)==2388
 assert sum(a['kind']=='cfg' for a in r)==16716
 assert sum(a['kind']=='HBM_PHY_assumed_abstract' for a in r)==4
def test_single_known_geometry_construction(d):
 assert not d['collisions'] and not d['out_of_die']
 assert d['inherited_residual_credit_mm2']==0
 assert d['actual_complete_node_area_mm2']==pytest.approx(129.0200389632)
def test_no_mesh_and_whole_group_extents(d):
 assert not d['clock_mesh'] and d['clock_option']=='C'
 assert d['clock_group_count']==71
 for g in d['clock_groups']:
  b=g['bbox_um'];assert max(b[2]-b[0],b[3]-b[1])<=5250
 names=[a for g in d['clock_groups'] for a in g['instances']];assert len(names)==len(set(names))
def test_opaque_providers_not_fabricated_regions(d):
 assert len(d['opaque_provider_decomposition_required'])==3
 assert not d['full_die_fit'] and not d['selected_hierarchical_route_admitted']
def test_current_metal_positive_guide_only(d):
 c=d['clock_construction']
 assert c['trunk_leaf_count']==71 and c['trunk_130_leaf_screen_pass']
 assert c['shield_track_guide_area_mm2']>0 and c['trunk_filtered_rail_current_proxy_A']>0
 assert c['shield_metal']['M8']['pitch_um']==.08
 assert c['shield_metal']['M9']['direction']=='VERTICAL'
 assert c['available_tracks'] is None and not c['clock_PG_overlap_proven']
def test_no_free_FIFO_or_forwarded_state(d):
 c=d['clock_construction'];assert c['parallel_crossing_bits']>0
 assert c['FIFO_gross_FF50_storage_proxy_mm2']['4']>0
 assert c['FIFO_gross_FF50_storage_proxy_mm2']['8']==2*c['FIFO_gross_FF50_storage_proxy_mm2']['4']
 assert c['forwarded_stage_state_FF50_proxy_mm2']>0
 assert c['local_CTS_cell_area_mm2'] is None and c['filtered_rail_LDO_area_mm2'] is None
def test_relocation_recomputes_edge_and_path_guides(d):
 p={a['name']:[(a['bbox_um'][0]+a['bbox_um'][2])/2,(a['bbox_um'][1]+a['bbox_um'][3])/2] for a in d['rectangles']}
 for e in d['edges']:
  if e['source'] in p and e['destination'] in p:
   assert e['centre_L1_um']==sum(abs(x-y) for x,y in zip(p[e['source']],p[e['destination']]))
  assert e['native_pin_length_um'] is None
 paths=d['clock_construction']['return_paths'];assert len(paths)==4776
 assert not any(p['missing_endpoint'] for p in paths)
 assert {p['pair'] for p in paths}==set(range(2388))
def test_no_transfer_clock_study_to_fulltoken(d):
 c=d['clock_construction'];assert c['single_user_token_delta_cycles'] is None
 assert d['clock_C']['old_S73_661cycles_not_S82_calibration']
 assert not d['hardware_PnR_admitted'] and not d['rate_adopted']
def test_prior_band_replacement_FAIL_preserved():
 p=ROOT/'results/uarch/dsrom_s82_native_parent_20261003/storage_band_replacement_FAIL.json.gz'
 m=json.loads(gzip.decompress(p.read_bytes()));assert len(m['collisions'])==2080
 assert not m['full_die_fit']
