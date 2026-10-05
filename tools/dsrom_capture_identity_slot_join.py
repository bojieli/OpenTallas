#!/usr/bin/env python3
"""Price/place proposal for exact missing46 context bits, no hidden replication."""
import argparse,hashlib,json,math
from pathlib import Path
import dsrom_capture_home_r49 as H
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_identity_slot_join_20261002'
def build():
    pin=json.loads((BASE/'inputs/origin.json').read_text());raw=(BASE/'inputs/owner.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('owner source drift')
    owner=json.loads(raw);state=owner['state_price_equations']
    if (state['frozen_context_existing_baseline_bits'],state['required_extra_frozen_identity_bits'],state['extra_frozen_identity_hold_BUF_lower_bound'])!=(123,46,92):raise ValueError('identity debit changed')
    h=H.build();d,_=H.H.inputs();f=d['capture.json']['source_cell_facts'];box=h['corrected_common_bbox_DBU'];tie_area=d['capture.json']['SETN_TIEHI_LEF_area_um2']/1483
    # One selected-home proposal, not an actual placed controller.
    masters=['DFFASRHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R']+['NAND2x1_ASAP7_75t_R']*3+['INVx1_ASAP7_75t_R']+['BUFx4_ASAP7_75t_R']*2+['TIEHIx1_ASAP7_75t_R']
    widths={m:round(f[m]['SS']['size_um'][0]*1000) for m in set(masters) if not m.startswith('TIEHI')};widths[masters[-1]]=round(tie_area/.27*1000)
    pitch=sum(widths[m] for m in masters)
    if pitch!=3618:raise ValueError('control bit footprint')
    strip=[box[0],box[3]-1080,box[2],box[3]];cells=[]
    for bit in range(46):
        x=strip[0]+(bit%23)*pitch;y=strip[1]+(bit//23)*540
        for index,m in enumerate(masters):
            cells.append(dict(bit=bit,role_index=index,master=m,bbox_DBU=[x,y,x+widths[m],y+270],orientation='R0',actual_instance_name=None));x+=widths[m]
    tree=7 #FO8: ceil46/8=6 leaves+1 root, clock and RESETN separately
    tail=[strip[0]+23*pitch,strip[1],strip[2],strip[3]]
    for n in range(2*tree):
        x=tail[0]+(n%7)*378;y=tail[1]+(n//7)*540
        cells.append(dict(bit=None,role_index='clockBUF' if n<7 else 'resetBUF',master='BUFx4_ASAP7_75t_R',bbox_DBU=[x,y,x+378,y+270],orientation='R0',actual_instance_name=None))
    if any(c['bbox_DBU'][2]>strip[2] or c['bbox_DBU'][3]>strip[3] for c in cells):raise ValueError('identity strip overflow')
    for i,a in enumerate(cells):
        if any(H.H.overlap(a['bbox_DBU'],b['bbox_DBU']) for b in cells[i+1:]):raise ValueError('cell overlap')
    counts={m:sum(c['master']==m for c in cells) for m in set(masters)}
    body=sum(n*(tie_area if m.startswith('TIEHI') else f[m]['SS']['area_um2']) for m,n in counts.items())
    reserve=2*body/1e6
    area=(strip[2]-strip[0])*(strip[3]-strip[1])/1e12
    if reserve>area:raise ValueError('identity source reserve does not fit proposed strip')
    loads={corner:{p:46*f[masters[0]][corner]['pins'][p]['cap_fF'] for p in ('CLK','RESETN','SETN')} for corner in ('SS','FF')}
    return dict(schema='DS_CAPTURE_46_IDENTITY_SLOT_JOIN_1',candidate=h['candidate'],owner_source=pin,
      global_frozen_bits=169,baseline_bits=123,mandatory_extra_bits=46,extra_feedback_BUF92_not_in_R49=True,
      proposal_home_shard=0,common_bbox_DBU=box,identity_strip_bbox_DBU=strip,source_cell_proposal=cells,cell_counts=counts,
      exact_added_body_um2=body,reserve50pct_mm2=reserve,proposed_strip_mm2=area,clock_reset_FO8_new_BUF=14,ASR_direct_pin_loads_fF=loads,
      common_total_required_with_identity_mm2=h['area']['common_required_mm2']+reserve,
      common_remaining_reservation_mm2=h['area']['reduced_common_reserved_mm2']-h['area']['common_required_mm2']-reserve,
      island_remaining_before_replication_tokens_VM_routes_mm2=h['area']['interior_left_before_new_tokens_VM_forward_hold_routes_mm2']-reserve,
      incremental_whole_reticle_enclosure_mm2=0,source_rows_seats_macros_unchanged=True,
      remote_context_copy_added_bits=None,control_remaining_placement_not_done=True,minimum_feedback_screen_not_context_hold=True,
      raw_M1_phase_used_for_R0_but_new_PG_upfeeds_unbound=True,actual_clock_reset_source_pin_routes=None,
      new_gather_arbitration189_gross_not_recharged_as_incremental=True,
      actual_finite_C_or_register_positions=None,actual_consumer_deadline=None,legal_PG_signal_routes=False,physical_build_admitted=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
