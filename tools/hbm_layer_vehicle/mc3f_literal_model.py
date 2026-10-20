#!/usr/bin/env python3
"""Frozen MC3F literal geometry/source model. Never generates a gate or approval."""
import argparse,copy,hashlib,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import check_macro_track_alignment as tracks
from measured_band_fill import lattice_band_errors


def model(frozen,native=None):
    view=frozen/'physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192'
    macro=tracks.parse_lef(view.with_suffix('.lef').read_text())[0]
    Wm,Hm=macro['W']/1000,macro['H']/1000
    pins={p['name']:p for p in macro['pins']if p['use']not in['POWER','GROUND']}
    faces={'W':[],'E':[],'N':[],'S':[]}
    for n,p in pins.items():
        for lay,r in p['rects']:
            face='W'if r[0]<=200 else'E'if r[2]>=macro['W']-200 else'N'if r[3]>=macro['H']-200 else'S'if r[1]<=200 else'INTERIOR'
            if face not in faces:raise ValueError((n,r))
            faces[face].append((n,lay,r))
    steps={}
    for f,ps in faces.items():
        ys=sorted(set((r[1]+r[3])/2000 for n,l,r in ps));steps[f]=min((b-a for a,b in zip(ys,ys[1:])),default=None)
    out=dict(schema='opentallas.hbm.mc3f-literal-source-model.v1',status='MODEL_ONLY_HOLD',source_commit='e6dfdb4e2',analysis_base='6586b0856',
      macro=dict(size_um=[Wm,Hm],nonPG_pins=len(pins),faces={f:len(v)for f,v in faces.items()},minimum_face_pin_pitch_um=steps,
        local_pin_density_per_um=max(1/v for v in steps.values()if v),literal_pitch_um=86.4,
        rejected43_2_gaps_um=[43.2-Wm,43.2-Hm],legal86_4_gaps_um=[86.4-Wm,86.4-Hm],
        note='R0 literal43.2origins; W/E are not bare. Off-lattice27.552 abutment is not admitted.'),layouts=[])
    for tag in ['l531','l358','l358_rolefix_MODEL']:
        base='l358'if tag.startswith('l358')else'l531';d=json.loads((frozen/f'physical/ref_tile/hdie_pc_ctrl_mc3c6_{base}/spec.json').read_text());pp=json.loads((frozen/f'physical/ref_tile/hdie_pc_ctrl_mc3c6_{base}/pin_plan.json').read_text());W,H=d['outline']['w'],d['outline']['h'];lo,hi=d['fill_reason']['lattice_channel_bound']['std_band_y_um'];ms=copy.deepcopy(d['macros'])
        if tag.endswith('MODEL'):
            # Role permutation only: same23live macros, literal slots, ports and source edges.
            for m in ms:
                n=m['inst'];c=round((m['at'][0]/43.2-1)/2)
                if 'u_response_payload' in n:r=1
                elif 'u_write_payload' in n:r=3
                elif '.u_head.'in n:r=2
                elif '.u_post.'in n:r=0 if '.M[0].'in n else 5
                elif 'u_queue' in n:c,r=0,4
                elif 'u_pending_identity'in n:c,r=1,4
                elif 'u_response_identity'in n:c,r=2,4
                else:raise ValueError(n)
                m['at']=[43.2+86.4*c,43.2+86.4*r]
        blocks=[dict(kind='macro',x=m['at'][0],y=m['at'][1],w=Wm,h=Hm)for m in ms]
        assert len(ms)==23 and len({tuple(m['at'])for m in ms})==23
        errs=lattice_band_errors(d,W,H,blocks,d['std_area_um2'])
        assert set(errs)<= {'missing coordinator approval/reason'},(tag,errs)
        placement=[tracks.check_placement(macro,'R0',round(m['at'][0]*1000),round(m['at'][1]*1000))for m in ms]
        assert not any(q['offtrack']for z in placement for q in z['layers'].values())
        off=[]
        for n,p in pp['pins'].items():
            z=p['at'][0]if p['layer']=='M5'else p['at'][1]
            if (round(z*1000)-12)%48:off.append(n)
        assert not off
        area=(W-4.32)*(hi-lo);A=d['std_area_um2'];ordinary=native.get('remaining_source_ordinary_area_um2')if native else None
        byname={m['inst']:m for m in ms}
        def box(inst,pin):
            m=byname[inst];rr=pins[pin]['rects'][0][1];return[m['at'][0]+rr[0]/1000,m['at'][1]+rr[1]/1000,m['at'][0]+rr[2]/1000,m['at'][1]+rr[3]/1000]
        families={}
        def add(f,a,b):
            r=families.setdefault(f,dict(edges=0,max_bbox_L1_um=0,over405=0));z=max(abs(a[x]-b[y])+abs(a[u]-b[v])for x in[0,2]for y in[0,2]for u in[1,3]for v in[1,3]);r['edges']+=1;r['max_bbox_L1_um']=max(r['max_bbox_L1_um'],z);r['over405']+=z>405+1e-6
        def faceff(pin):
            p=pp['pins'][pin];x,y=p['at'];y=H-14 if p['side']=='N'else 14 if p['side']=='S'else y
            return[x-.3,y-.135,x+.3,y+.135]
        def bandff(x=W/2):return[x-.3,(lo+hi)/2-.135,x+.3,(lo+hi)/2+.135]
        for g in range(4):
            resp=f'u_native.u_response_payload.M[{g}].P.u_m';wp=f'u_native.g_wpay.u_write_payload.M[{g}].P.u_m';anchor=bandff(byname[wp]['at'][0]+Wm/2)
            for b in range(64):
                add('RESPread_to_KRhead_N14',box(resp,f'rd_out[{b}]'),faceff(f'kr_data[{64*g+b}]'))
                add('WPAYread_to_PHYcolFF_S14',box(wp,f'rd_out[{b}]'),faceff(f'col_data[{64*g+b}]'))
                add('RREG_S14_to_RESPwrite',faceff(f'dram_rdata[{64*g+b}]'),box(resp,f'wd_in[{b}]'))
                add('Kcapture_N14_to_regionalKring_band',faceff(f'k_wdata[{64*g+b}]'),anchor)
                add('regionalKring_band_to_WPAYwrite',anchor,box(wp,f'wd_in[{b}]'))
            head=f'u_native.METADATA[{g}].u_head.M[0].P.u_m'
            for b in range(21):add('HEADtag_to_PENDINGwrite',box(head,f'rd_out[{32+b}]'),box('u_native.u_pending_identity.M[0].P.u_m',f'wd_in[{b}]'))
            for b in range(32):add('HEADstrb_to_PHYstrbFF_S14',box(head,f'rd_out[{b}]'),faceff(f'col_strb[{b}]'))
            for k in range(2):
                post=f'u_native.METADATA[{g}].u_post.M[{k}].P.u_m'
                for b in range(64 if k==0 else 15):add('POSTread_to_centralPostREG_band',box(post,f'rd_out[{b}]'),bandff())
        for b in range(21):
            add('PENDINGread_to_RIDwrite',box('u_native.u_pending_identity.M[0].P.u_m',f'rd_out[{b}]'),box('u_native.u_response_identity.M[0].P.u_m',f'wd_in[{b}]'))
            p=f'kr_beat[{b}]'if b<4 else f'kr_tag[{b-4}]';add('RIDread_to_KRidentityhead_N14',box('u_native.u_response_identity.M[0].P.u_m',f'rd_out[{b}]'),faceff(p))
        out['layouts'].append(dict(name=tag,geometry_status='PASS_GEOMETRY_ONLY',approval_errors=errs,
          outline_um=[W,H],area_um2=W*H,macro_count=23,macros=ms,macro_pin_track_checks=len(pins)*23,macro_offtrack=0,
          planned_boundary_pins=len(pp['pins']),planned_boundary_point_offtrack=off,
          fullwidth_band_um=[2.16,lo,W-2.16,hi],band_area_um2=area,source_std_area_inherited_um2=A,
          inherited_source_density=A/area,max_source_pin_clock_exception_area_before_density40_um2=A-.4*area,
          source_ordinary_area_from_native=ordinary,source_ordinary_density=None if ordinary is None else ordinary/area,
          ordinary_FF_to_FF_endpoint_rectangle_bound_um=(W-4.32)+(hi-lo),
          source_family_anchor_model=families,
          anchor_scope='Logical stage endpoint bboxes using actual macro pin RECTs and candidate14um face landing centres/role-specific band anchors. Not actual FF placement, full transitive graph or area packing.',
          actual_native_bboxes=None,actual_region_group_membership=None,actual_GPL_consumption=None,
          actual_full_source405='NOT RUN',nativePG='NOT RUN',clockspread='NOT RUN',source_pin_placement_exceptions_approved=[]))
    out['macro_inventory']=dict(raw_source_instances=27,expected_live_after_optimization=23,
      eliminated_candidates=[f'u_native.METADATA[{g}].u_head.M[1].P.u_m'for g in range(4)],
      source_reason='u_headW79 but only mh[63:0]/queue_head consumed; post uses all79. Require actual mapped23inventory, not silent sourceW64 reinterpretation.')
    out['band_consumption']=dict(status='NOT RUN',current_hook='physical/hbm_bw_face_1019/pre_gpl.tcl has pin split/iohold/ioflop hooks and explicitly no fence',
      mechanism='One INCLUSIVE dbRegion full-width band plus dbGroup constructed FROM that region; ordinary instances in BOTH exact objects',
      primary_repo_example='physical/hbm_accel_die_views/stations/bench/stn_meso_fence.tcl:157',
      members='ALL actual standard cells incl generated/repair/data reset cells minus explicitly approved exact native clock/pin inventory; never instance-prefix classification',
      births='Resync/revalidate after IO, GPL repair, CTS and GRT; unknown/mixed clock-data cell remains ordinary or fails. PG binding before DNT required.',
      needed_receipts=['native cell/group/region names and source SHA inventory','actual GPL log named group consumed and all native bboxes inband','all ITerm/BTerm/net/DNT/PG graph identity','exact actual legal-row union covers fullband','placed40..60%density after subtracting exact exceptions','full transitive source405 incl macros/primarypins/reset and transparent cells','real PDK clock and actual macro clock role/phase binding; no clock-data name exclusion'])
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frozen',type=Path,required=True);p.add_argument('--native',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();n=json.loads(a.native.read_text())if a.native else None;d=model(a.frozen,n);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(status=d['status'],layouts=[dict(name=x['name'],source_anchor_over405=sum(z['over405']for z in x['source_family_anchor_model'].values()))for x in d['layouts']])))
