#!/usr/bin/env python3
"""Size a bounded parent M9 reservation for the unchanged146 control bits.

This is a die-lead reservation request, never an assertion of actual PG/via or
whole-graph clearance. Leaf M9 ports/interior M6 routing are not permitted.
"""
import argparse,json,re,math,hashlib
from pathlib import Path
import dvm_m7_seam_plan as S

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--origins',required=True);ap.add_argument('--pdn',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    record=json.loads(Path(a.origins).read_text());p=Path(a.pdn);s=p.read_text()
    m=re.findall(r'^add_pdn_stripe -grid core -layer M9 -width ([.\d]+) -pitch ([.\d]+) -offset ([.\d]+)$',s,re.M)
    if len(m)!=1:raise ValueError('Need exact single coreM9 stripe declaration')
    width,pitch,offset=[round(float(x)*1000) for x in m[0]]
    controls=[(i,inp,out,suffix,bit,n) for i,(inp,out,suffix,n) in enumerate(S.FIELDS) if inp!='w_d' for bit in range(n)]
    assert len(controls)==146
    columns={}; summaries=[]
    for name,h in record['homes'].items():
        x0=round(h['x']*1000);x1=x0+S.WIDTH_NM
        # Global M9 track family offset36nm, pitch80nm, two-track160nm spacing.
        # PG recipe is conservative .48um rectangles plus40nm snap and48nm clearance.
        nominal=[offset+j*pitch/2+k*pitch for j in (0,1) for k in range(math.floor((x0-offset)/pitch)-1,math.ceil((x1-offset)/pitch)+1)]
        tracks=[x for x in range(36, x1, 160) if x>=x0+576 and x<x1-576
                and all(abs(x-c)>width/2+40+48+20 for c in nominal)]
        if len(tracks)<146:raise ValueError('Insufficient parent M9 candidates')
        selected=[tracks[((2*i+1)*len(tracks))//292] for i in range(146)]
        assert len(set(selected))==146
        cols=dict(origin_um=[h['x'],h['y']],candidate_M9_x_nm=selected,
                  candidate_M9_available_after_nominal_PG=len(tracks), M9_cut=146/len(tracks),
                  internal_seam_y_um=[round(h['y']+y,3) for y in [136.08,272.16,408.24,544.32,889.92,1026,1162.08,1298.16]],
                  reserved_y_interval_per_seam_um=[-20,20])
        columns[name]=cols;summaries.append(cols['M9_cut'])
    assignments=[]
    for idx,(_,inp,out,suffix,bit,n) in enumerate(controls):
        assignments.append(dict(index=idx,bit=bit,side='W' if idx%2==0 else 'E',side_index=idx//2,
            leaf_input=inp+(f'[{bit}]' if n>1 else ''),leaf_output=out+(f'[{bit}]' if n>1 else ''),
            head_N='cn_'+suffix+(f'[{bit}]' if n>1 else ''),head_S='cs_'+suffix+(f'[{bit}]' if n>1 else '')))
    out=dict(schema='opentallas.qwen-dvm-m9-parent-request.v1',qualified=False,adopted=False,
       pdn_source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(), source_full_homes_sha256=record['source_full_homes_sha256'],
       source_PG_recipe_nm=dict(M9_width=width,M9_pitch=pitch,M9_offset=offset,M9_other_net_phase_nm=offset+pitch/2),
       nominal_PG_assumptions=['core origin0; die lead must validate against actual placed PG rectangles',
                              'conservative40nm PG snap allowance+48nm separation+20nm signal halfwidth; actual via landing could require more'],
       unchanged_word_bits=1170,payload_NS_bits=1024,control_side_bits=146,normal_cycle_change=0,
       payload_NS_contact_cut=1024/1958,aggregate_legacy_M3_M5_M7_cut=1170/1958,
       parent_M9_cut_range=[min(summaries),max(summaries)],parent_M9_minimum_two_track_width_um=23.36,
       control_side_pins_per_face_per_edge_band=73, side_band_depth_um=20,
       M6_side_contact_depth_um=.384,M6_side_available_two_track_slots_per20um=156, M6_side_contact_cut=73/156,
       no_leaf_M9_contacts=True,no_leaf_M6_M7_body_route_permission=True,
       control_bit_assignments=assignments,columns=columns,
       open=['die actual coreM9 PG shapes/vias and wholegraph traffic reservation',
             'leaf exact M6 side-contact geometry on four y phases and native pin flop anchors',
             'head side-face complete pin capacity; existing head-row/corridor/read buses cannot be displaced silently',
             'payload source-bound M7 contact permissions and actual landing proof',
             'native per-child root insertion/phase-R, real read relays and full TT/FF/DRC signoff'],
       interpretation='M9 routes are parent wires over M5-capped bodies, not a leaf layer-cap relaxation; provisional track requests require actual placed geometry audit')
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ['columns','control_bit_assignments']},indent=2))
if __name__=='__main__':main()
