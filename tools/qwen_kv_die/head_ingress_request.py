#!/usr/bin/env python3
"""Request source-local ABC capture homes and real producer-derived pin checks.

This creates a candidate request, NEVER a die grant or qualified view. Existing
heads/relays occupying the requested source bands must actually move in the die
generator; every incident edge and native clock/timing budget must be rechecked.
"""
import argparse, hashlib, itertools, json
from pathlib import Path
import head_staged_plan as H
ROOT=Path(__file__).resolve().parents[2]

def sources():
    prefix=ROOT/'physical/ref_tile'
    return {c:prefix/f'qkd_ectl_{c}_tp8_direct/views'/m/(m+'.lef')for c,m in
       [('a','qkd_ectl_a_tp8_epoch_direct'),('b','qkd_ectl_b_tp8_direct'),('c','qkd_ectl_c_tp8_direct')]}

def signal(role,bit,h):
    pair=h//2
    if role=='a': return f't{pair}_row[{bit}]'
    if role=='b':
        if bit<12:return f't{pair}_cl[{bit+4}]'
        if bit<524:return f't{pair}_row[{bit-12}]'
        return f't{pair}_cl[{bit-524}]'
    if bit<512:return f't{pair}_q[{bit+7}]'
    if bit<518:return f't{pair}_q[{bit-511}]'
    if bit==518:return f't{pair}_q[0]'
    return f'e{h}[{bit-519}]'

def chunk_source_for_tstage(bit):
    """Flat T1 input bit0..1574 -> registered ABC output bit, per actual RTL."""
    if not 0<=bit<1575:raise ValueError('T1 input bit outside1575-bit word')
    if bit<519:return 'c',bit
    if bit<531:return 'b',bit-519
    if bit<1043:return 'a',bit-531
    if bit<1559:return 'b',bit-1031
    return 'c',bit-1040

def move_source_bands(insts):
    """Move connected head/ECTL groups before ANY relay generation."""
    band_changes=[]
    for i in insts:
        old=dict(i);name=i['name']
        if i['master']in('qkd_rhead','qkd_ectl'):
            parts=name.split('_');e=int(parts[2]);shift=(e%4)*118.8-237.6
            if i['master']=='qkd_rhead': shift+=118.8 if int(parts[-1])>=2 else 0.
            else:shift+=59.4
            i['y']=round(i['y']+shift,6)
        elif i['master']in('qkd_astk','qkd_astk_n'):
            i['y']=round(i['y']-237.6,6);i['h']=round(i['h']+475.2,6)
        if old!=i:band_changes.append(dict(name=name,before=old,after=dict(i)))
    return band_changes

def capture_homes(insts):
    """Exact source-derived homes; proposed pins, never a physical view grant."""
    by={i['name']:i for i in insts};paths=sources();leaves={c:H.lef(p)for c,p in paths.items()}
    pins={}
    for i in range(535):
        x=round(13.5+.192*i,6)
        pins[f'a[{i}]']=dict(layer='M5',face='S',xy=[x,0.])
        pins[f'b[{i}]']=dict(layer='M5',face='N',xy=[x,21.6])
    pins['ck']=dict(layer='M4',face='W',xy=[0.,10.812])
    homes=[];all_worst=[]
    for head in (i for i in insts if i['master']=='qkd_rhead'):
        parts=head['name'].split('_');h=int(parts[-1]);ectl=by['ectl_'+'_'.join(parts[1:-1])]
        efx,efy=H.FLIPS[ectl['orient']]
        for role,n,x in [('a',512,129.6),('b',528,264.6),('c',535,480.6)]:
            lower=h<2;tier=1 if h in(1,2)else 2
            y=-27.*tier-.048 if lower else 129.6+5.448+27.*(tier-1)
            orient=H.ORIENT[(efx,efy!=lower)]if hasattr(H,'ORIENT')else next(o for o,v in H.FLIPS.items()if v==(efx,efy!=lower))
            wx=ectl['x']+(ectl['w']-x-129.6 if efx else x)
            wy=ectl['y']+(ectl['h']-y-21.6 if efy else y)
            oldxy=[wx,wy]
            fx,fy=H.FLIPS[orient]
            input_x=129.6-13.5 if fx else 13.5
            clock_y=21.6-10.812 if fy else 10.812
            wx=round(.012+.048*round((wx+input_x-.012)/.048)-input_x,6)
            wy=round(.012+.048*round((wy+clock_y-.012)/.048)-clock_y,6)
            assert abs((wx+input_x-.012)/.048-round((wx+input_x-.012)/.048))<1e-6
            assert abs((wy+clock_y-.012)/.048-round((wy+clock_y-.012)/.048))<1e-6
            w=dict(um=-1.)
            for bit in range(n):
                peer=signal(role,bit,h);size,pp=leaves[role]
                box=(0. if role=='a'else 254.88 if role=='b'else 509.76,0.)
                fx,fy=H.FLIPS[ectl['orient']]
                leafxy=(ectl['x']+(ectl['w']-box[0]-size[0]if fx else box[0]),ectl['y']+(ectl['h']-size[1]if fy else 0.))
                src=H.xf(pp[peer],leafxy,size,ectl['orient'])
                xx=pins[f'a[{bit}]']['xy'][0]
                dst=H.xf([(xx-.012,0.),(xx+.012,0.),(xx-.012,.144),(xx+.012,.144)],(wx,wy),(129.6,21.6),orient)
                dist=max(abs(u[0]-v[0])+abs(u[1]-v[1])for u,v in itertools.product(src,dst))
                if dist>w['um']:w=dict(um=round(dist,6),producer_pin=peer,capture_pin=f'a[{bit}]')
            box=[wx,wy,129.6,21.6]
            blockers=[i['name']for i in insts if H.overlap(box,[i[k]for k in('x','y','w','h')])]
            homes.append(dict(name=head['name']+'/u_ingress/u_'+role,master='qkh_head_chunk_stage',parameters=dict(W=535),xy=[wx,wy],size_um=[129.6,21.6],orient=orient,origin_grid_shift_um=[round(wx-oldxy[0],6),round(wy-oldxy[1],6)],pin_track_lattice='M5x/M4y=.012+.048k checked for mirrored placement',producer=ectl['name']+'/'+role,payload_bits=n,explicit_zero_pad_bits=535-n,producer_to_capture=w,existing_frame_blockers=blockers,clock='independent native phi-R; missing new view, must not inherit old insertion',requested=True,adopted=False))
            all_worst.append(w['um'])
    assert len(homes)==384
    return paths,pins,homes,all_worst

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--create-bands',action='store_true',help='Source-bound proposal: grow each ECTL intakegap59.4um/side and recenter four-row connected engine groups; relays require regeneration')
    ap.add_argument('--insts',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    insts=json.loads(a.insts.read_text())
    original=json.loads(a.insts.read_text());band_changes=[]
    if a.create_bands:band_changes=move_source_bands(insts)
    paths,pins,homes,all_worst=capture_homes(insts)
    rec=dict(schema='opentallas.qwen-head-abc-request.v1',qualified=False,adopted=False,master='qkh_head_chunk_stage',parameters=dict(W=535),instances=384,proposed_physical_FF=384*535,payload_FF=128*1575,padding_FF=3840,outline_um=[129.6,21.6],pins=pins,homes=homes,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths.values()},insts_sha256=hashlib.sha256(a.insts.read_bytes()).hexdigest(),max_actual_producer_to_candidate_pin_um=max(all_worst),timing_qualified=False,missing=['actual child route+TT/FF/DRC/native audit+insertion','generator band grants and displacement of named blockers','all chunk-to-T1 actual matched-bit native reach','all128 N3 source binding, clock roots and complete incident cuts','ECTL HXK/HXN/calendar+1 and real8192bit ECTL-head composition+mutants', 'static compiler+1 layer cycle and measured end-to-end cost'],fixed_cycles=dict(ABC_capture=1,T1=1,T2=1,score_return=1,increment_vs_N2=1),track_model=dict(underlying_M5_pitch_um=.048,pin_spacing_um=.192,gross_two_track_fraction=535*.096/129.6,local_two_track_fraction=535*.096/(535*.192),PG_and_OBS_audit='REQUIRED; gross counts do not establish routing'),band_request='Two21.6um capture rows with5.4um gaps on EACH ECTL producer face, total54um per side. Current head/relay blockers are explicitly retained; actual generator must grant/rehome them.')
    if a.create_bands:
        body=[i for i in insts if not i['master'].startswith('qkd_rly')]
        def hit(a,b):
            return min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])>.001 and min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])>.001
        body_hits=[(x['name'],y['name'])for x,y in itertools.combinations(body,2)if hit(x,y)]
        all_hits=[(x['name'],y['name'])for x,y in itertools.combinations(insts,2)if hit(x,y)]
        outline=json.loads(a.insts.with_name('plan.json').read_text())['die_um']
        outside=[i['name']for i in body if i['x']<0 or i['y']<0 or i['x']+i['w']>outline[0]+.001 or i['y']+i['h']>outline[1]+.001]
        rec['band_creation_proposal']=dict(nonrelay_frames_outside=outside,die_outline_um=outline,qualified=False,source='exact current390b candidate insts; actual die generator successor still required',grow_um_per_face=59.4,engine_group_height_added_um=475.2,engine_group_recenter_um=-237.6,changed_frames=len(band_changes),changes=band_changes,unchanged_package_and_HBM_strip_homes=True,die_outline_change_um=[0,0],die_area_added_mm2=0.,nonrelay_frame_overlaps=body_hits,all_retained_old_relay_overlaps_count=len(all_hits),all_retained_old_relay_overlaps_examples=all_hits[:40],relay_status='Old relays retained only to expose collisions; MUST regenerate every incident path, cut, clock and reset before adoption. ASTK is a resized wires-only parent request, no hard view enlarged.')
    a.out.mkdir(parents=True,exist_ok=True);
    if a.create_bands:(a.out/'proposed_source_band_insts.json').write_text(json.dumps(insts)+'\n')
    (a.out/'request.json').write_text(json.dumps(rec,indent=2)+'\n')
    lines=[]
    for pin,v in pins.items():
        x,y=v['xy'];size='.144 .024'if v['layer']=='M4'else'.024 .144'
        lines.append(f'place_pin -pin_name {{{pin}}} -layer {v["layer"]} -location {{{x:.6f} {y:.6f}}} -pin_size {{{size}}}')
    (a.out/'candidate_pins.tcl').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:rec[k]for k in('instances','proposed_physical_FF','padding_FF','max_actual_producer_to_candidate_pin_um')}))
if __name__=='__main__':main()
