#!/usr/bin/env python3
"""M6-only leaf contact candidate; source binding and routed audits stay mandatory."""
import argparse,json,collections
from pathlib import Path
import dvm_m7_seam_plan as S

LEAF_H=136056

def generate():
    # Keep824 payload bits on M3/M5; all146 controls and first200 payload
    # bits take named M6 side contacts. No payload or control is omitted.
    old=S.plan(0)['ports']
    # Derive from the actual explicit names rather than relying on a bundle offset.
    side=[p for p in old if p['names']['leaf_S'].split('[')[0]!='w_d' or int(p['names']['leaf_S'].split('[')[1][:-1])<200]
    ns=[p for p in old if p not in side]
    assert len(side)==346 and len(ns)==824
    slots=S.available(0,('M3','M5'))
    payload=[]
    for i,p in enumerate(ns):
        x,layer,w=slots[((2*i+1)*len(slots))//(2*len(ns))]
        payload.append(dict(names=p['names'],layer=layer,rect_x_nm=[x-w//2,x+w//2],edge_depth_nm=384))
    aliases={}
    for orient in ['R0','MX']:
        for origin in [0,16,32,48]:
            localoff=(16-origin)%64 if orient=='R0' else (origin+LEAF_H-16)%64
            # Separate input/output contact bands; both W/E carry173 bits.
            bands=[]
            for low in [0,LEAF_H-43200]:
                bands.append([y for y in range(localoff,LEAF_H,128) if low+192<=y<=low+43200-192])
            assignments=[]
            for i,p in enumerate(side):
                face='W' if i%2==0 else 'E';j=i//2
                points=[b[((2*j+1)*len(b))//346] for b in bands]
                assignments.append(dict(names=p['names'],layer='M6',side=face,
                    leaf_input_y_nm=points[0],
                    leaf_output_y_nm=points[1],
                    side_contact_depth_nm=384,side_contact_height_nm=32,
                    parent_crossing_layer='M7' if p['names']['leaf_S'].startswith('w_d[') else 'M9'))
            for p in assignments:
                for k in ['leaf_input_y_nm','leaf_output_y_nm']:
                    global_y=origin+(p[k] if orient=='R0' else LEAF_H-p[k])
                    assert (global_y-16)%64==0
            aliases[f'{orient}_origin_y_mod64_{origin}']=dict(local_M6_offset_mod64_nm=localoff,contacts=assignments,
                side_available_two_track_slots_per_band=len(bands[0]),contact_cut_per_band=173/len(bands[0]))
    return dict(schema='opentallas.qwen-dvm-m6-side-candidate.v1',qualified=False,adopted=False,
       normal_cycle_change=0,
       candidate_actual_leaf_outline_um=[64.776,136.056],outline_status='candidate matching prior nominal136.08 export convention; actual gate/export must verify',
       unchanged_word_bits=1170, NS_payload_bits=824,M6_side_bits=346,NS_M3_M5_available_slots=len(slots), NS_pin_cut=824/len(slots),
       side_pins_per_face_per_band=173,side_band_depth_um=43.2,
       parent_M7_additional_bits=200,parent_M9_bits=146,
       parent_M7_candidate_cut=200/(1958-1499),parent_M9_nominal_cut_max=146/336,
       NS_contacts=payload,M6_aliases=aliases,
       no_leaf_M7_or_M9_ports=True,no_blanket_M6_body_route=True,
       open=['actual M6 source-bound PORT-only grant for every relocated exact named bit',
             'actual source/export dimensions and orientation select exact M6 alias; no view inheritance',
             'all173 W/E side input/output capture/launch anchors plus existing E read/control pins and PG vias',
             'head side-face complete pin plan, including346 additional contacts per W/E face',
             'actual parent200 M7 and146M9 track reservations and all incident wholegraph traffic',
             'fresh component behavioral equivalence/mutants, CTS/native/TTsetup/FFhold/DRC0 and parent GRT/STA'])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--origins',required=True);a=ap.parse_args();r=generate()
    r['source_rtl_sha256']={p:S.digest(p) for p in ['rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv']}
    homes=json.loads(Path(a.origins).read_text());requests={}
    for name,h in homes['homes'].items():
        origin=round(h['x']*1000);slots=S.available(origin%64,('M7',))
        selected=[slots[((2*i+1)*len(slots))//400][0]+origin for i in range(200)]
        assert len(set(selected))==200 and all((x-16)%64==0 for x in selected)
        requests[name]=dict(global_M7_x_nm=selected,available_slots=len(slots),cut=200/len(slots),
                            required_seam_y_um=[round(h['y']+y,3) for y in [136.08,272.16,408.24,544.32,889.92,1026,1162.08,1298.16]],
                            requested_seam_band_y_um=[-43.2,43.2])
    r['parent_M7_track_requests']=requests
    r['source_homes_fixture_sha256']=S.digest(a.origins)
    r['parent_M7_candidate_cut']=max(v['cut'] for v in requests.values())
    Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k not in ['NS_contacts','M6_aliases','parent_M7_track_requests']},indent=2))
if __name__=='__main__':main()
