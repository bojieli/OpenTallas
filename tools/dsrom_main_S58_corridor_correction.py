#!/usr/bin/env python3
"""Self-contained correction replay. No git history, helper, build or sweep."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_main_S58_corridor_correction_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 receipt=json.loads((BASE/'input_receipt.json').read_text());inputs={}
 for name,r in receipt['inputs'].items():
  p=BASE/'inputs'/name;assert sha(p)==r['sha256'],name;inputs[name]=json.loads(p.read_text())
 s=inputs['service_model.json'];o=inputs['reservation_outline.json'];grid=inputs['DS_grid.json'];main=inputs['main_S58.json']
 assert main['candidate_id']=='DS4096-TP4-S58-PAIR1'
 # Derive track density from actual grid phases, deduplicating repeated sequences.
 rate=0.;planes=[]
 for layer in ['M2','M4']:
  g=next(g for g in grid['grids'] if g['layer']==layer)
  phases={(start%pitch,pitch) for start,count,pitch in g['Y']}
  rate+=sum(1000/pitch for phase,pitch in phases)
  planes.append(dict(layer=layer,unique_Y_phase_pitch_DBU=sorted(phases)))
 assert math.isclose(rate,1000*(7/270+1/48),abs_tol=1e-10)
 oldband=next(r for r in o['clear_route_bands'] if r['name']=='index_HBM_all128responses_CLEAR_ROUTE_BAND')
 oldheight=oldband['bbox_um'][1];width=oldband['bbox_um'][0]
 req=128*(31+6+16+2);resp=128*(256+16+5+2);tracks=req+resp
 # Same2.16um snapping/one-step guard and50% non-signal reservation as pinned screen.
 height=math.ceil((2*tracks/rate)/2.16)*2.16+2.16
 growth=height-oldheight;debit=width*growth/1e6
 assert (req,resp,tracks)==(7040,35712,42752)
 assert math.isclose(debit,s['geometry']['native_bidirectional_extra_service_rectangle_mm2'],abs_tol=1e-9)
 a=main['area_and_service_reserve'];budget=a['inherited_usable_field_mm2'];need=a['full_conservative_field_need_mm2'];oldmargin=budget-need
 assert math.isclose(oldmargin,a['conditional_field_margin_mm2'],abs_tol=1e-10)
 result=dict(schema='opentallas.DSROM.S58.selfcontained-correction.v1',candidate_id=main['candidate_id'],local_C1_identifier_is_alias=True,main_pin=receipt['inputs']['main_S58.json']['commit'],input_receipt_sha256=sha(BASE/'input_receipt.json'),grid_planes=planes,tracks_per_um_before_reserve=rate,signal_reserve_fraction=.5,native_request_tracks=req,native_response_tracks=resp,native_combined_tracks=tracks,old_band_height_um=oldheight,new_band_height_um=height,band_growth_um=growth,band_width_um=width,new_corridor_debit_mm2=debit,old_budget_mm2=budget,unchanged_field_need_mm2=need,old_conditional_margin_mm2=oldmargin,corrected_budget_mm2=budget-debit,corrected_margin_mm2=budget-debit-need,verdict='FAIL_S58_SAME_BASIS_CAPACITY_AFTER_NATIVE_BIDIRECTIONAL_CORRIDOR_DEBIT',no_double_debit='Existing service and collector halo allocation not charged again; only increased clear route band area debited. Clock/PG policy unchanged.',scope='Prospective nativeAW31/LEN6/BEAT5 interface; retainedDSAW30/LEN4/BEAT4 unchanged. Source grid capacity screen not routing closure; DS adapter state/area remains unbound.',same_candidate_count=True,no_parameter_sweep=True,ownership_map_executable=False,BF1024_indivisible_floor=False,physical_GO=False,new_jobs=0,generator_sha256=sha(Path(__file__)))
 assert result['corrected_margin_mm2']<0
 raw=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode();p=BASE/'correction.json'
 if p.exists():assert p.read_bytes()==raw
 else:p.write_bytes(raw)
 print(json.dumps(dict(candidate=main['candidate_id'],old_margin_mm2=oldmargin,debit_mm2=debit,corrected_margin_mm2=result['corrected_margin_mm2'],verdict=result['verdict'],correction_sha256=hashlib.sha256(raw).hexdigest())))
if __name__=='__main__':main()
