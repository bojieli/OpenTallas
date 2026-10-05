import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_selector_clock_slot_join as J

def test_all70406_source_sites_named_distinct_and_inside():
 m=J.build();b=m['clock_annex_bbox_DBU'];sites=m['proposed_sites']
 assert len(sites)==len({s['proposed_site_ID'] for s in sites})==70406
 assert m['rows']==13 and m['rowpitch_DBU']==540
 for s in sites:
  a=s['bbox_DBU'];assert b[0]<=a[0]<a[2]<=b[2] and b[1]<=a[1]<a[3]<=b[3]
 assert m['site_capacity']>=70406

def test_unique_clock_charge_and_no_fit_adoption():
 m=J.build();assert m['core_clock_BUF70406_separate_from_transport48007']
 assert m['clock_annex_reservation_mm2']>=m['additional_clock_source50pct_floor_mm2']
 assert abs(m['combined_selector_priced_mm2']-2.32020267588)<1e-10
 assert m['exact_replacement_delta_vs_4cc_selector_charge_mm2']>0
 assert not m['physical_fit'] and not m['contextual_PR_admitted']
 assert m['required_equal_depth_pad_BUF_count'] is None
