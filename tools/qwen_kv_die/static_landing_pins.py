#!/usr/bin/env python3
"""Official canonical static landing leaf pins, balanced branch homes and reach.
No route/clock qualification is inferred from this geometry contract.
"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/qwen_split_1014/kvsys_v1_3_candidate/static_landing'

def build():
    masters={}
    def master(name,w,h):
        d=dict(outline=[w,h],pins={});masters[name]=d;return d
    def pins(d,name,n,face,lo,hi,indices=None):
        ids=list(range(n)) if indices is None else indices
        for j,i in enumerate(ids):
            pos=lo+(hi-lo)*(j+.5)/len(ids)
            # 10-15 (kvsys-elements DRT-0255 on the writer, generator fix b37888273): S / N face pins sit on the ASAP7 M5
            # track lattice (offset .060, pitch .192); W / E faces stay on the M4 lattice (.012 + .048 k)
            pos=(.06+.192*round((pos-.06)/.192)) if face in 'SN' else (.012+.048*round((pos-.012)/.048))
            w,h=d['outline'];xy={'W':[0,pos],'E':[w,pos],'S':[pos,0],'N':[pos,h]}[face]
            key=name if n==1 and indices is None else f'{name}[{i}]'
            assert key not in d['pins'];d['pins'][key]=dict(face=face,xy=xy,layer='M4' if face in 'WE' else 'M5')
    pc=master('qkd_static_kv_landing_pc',151.2,172.8)
    for name,n,lo,hi in [('get',1,8,9),('get_t',14,10,12),('get_v',1,14,15),('get_epoch',16,16,18),('get_layer',6,20,21),('out_data',256,50,125),('out_valid',1,132,133),('out_t',14,136,139),('out_v',1,140,141),('out_epoch',16,144,147),('out_layer',6,150,152),('fault',1,154,155)]:pins(pc,name,n,'W',lo,hi)
    for name,n,lo,hi in [('expected_put',1,8,9),('expected_sector',10,10,13),('actual_valid',1,16,17),('actual_sector',10,18,21),('actual_epoch',16,24,28),('actual_layer',6,30,32),('actual_data',256,40,112),('arm',1,120,121),('epoch',16,124,128),('layer',6,130,132)]:pins(pc,name,n,'E',lo,hi)
    for name,n,lo,hi in [('ck',1,70,72),('rst_n',1,75,77),('cfg_stack',2,80,81),('cfg_group',3,84,85)]:pins(pc,name,n,'S',lo,hi)
    ctl=master('qkd_static_kv_rowctl',86.4,302.4)
    for name,n,lo,hi in [('req_valid',1,4,5),('req_t',14,6,8),('req_v',1,9,10),('req_epoch',16,12,14.4),('req_layer',6,15,16),('rsp_data',1024,24,284),('rsp_valid',1,286,286.4),('rsp_t',14,287,289),('rsp_v',1,289.5,289.8),('rsp_epoch',16,290.5,292.8),('rsp_layer',6,293.5,294.5),('fault',1,296,296.4)]:pins(ctl,name,n,'W',lo,hi)
    for name,n,lo,hi in [('ck',1,40,41),('rst_n',1,43,44)]:pins(ctl,name,n,'S',lo,hi)
    for name,n,lo,hi in [('pc_get',4,4,4.6),('pc_get_t',56,5,13),('pc_get_v',4,13.5,14.1),('pc_get_epoch',64,14.5,23.6),('pc_get_layer',24,24,27.4)]:pins(ctl,name,n,'E',lo,hi)
    for q in range(4):
        start=32+64*q
        for name,n,lo,hi in [('pc_valid',1,0,1),('pc_data',256,2,42),('pc_t',14,44,47),('pc_v',1,48,49),('pc_epoch',16,50,53),('pc_layer',6,54,55.5),('pc_fault',1,57,58)]:pins(ctl,name,4*n,'E',start+lo,start+hi,list(range(q*n,(q+1)*n)))
    for width in (38,295):
        # hop295: 295 M5 tracks (.192) need 56.6 um of face -> 69.12 wide (was 52.68: .149-um pin pitch, off-track)
        hw=69.12 if width>200 else 52.68
        d=master(f'qkd_static_kv_hop{width}',hw,30.24)
        pins(d,'a',width,'S',4,hw-4);pins(d,'b',width,'N',4,hw-4);pins(d,'ck',1,'W',8,9);pins(d,'rst_n',1,'W',12,13)
    homes=[dict(name='rowctl',master='qkd_static_kv_rowctl',xy=[0,604.8],orient='R0')]
    req=[(90.72,432),(90.72,777.6),(151.2,777.6),(90.72,907.2)]
    rsp=[(151.2,432),(151.2,820.8),(90.72,864),(90.72,1166.4)]
    for q in range(4):
        homes += [dict(name=f'pc{q}',master='qkd_static_kv_landing_pc',xy=[86.4,190.08+378*q],orient='R0'),dict(name=f'req{q}',master='qkd_static_kv_hop38',xy=list(req[q]),orient='MX' if q==0 else 'R0'),dict(name=f'rsp{q}',master='qkd_static_kv_hop295',xy=list(rsp[q]),orient='MX' if q>=2 else 'R0')]
    by={x['name']:x for x in homes}
    def coord(h,p):
        d=by[h];x,y=masters[d['master']]['pins'][p]['xy'];w,hgt=masters[d['master']]['outline']
        if d['orient']=='MX':y=hgt-y
        return [x+d['xy'][0],y+d['xy'][1]]
    nets=[]
    for q in range(4):
        for direction,fields in [('req',[('get',1),('get_t',14),('get_v',1),('get_epoch',16),('get_layer',6)]),('rsp',[('out_valid',1),('out_data',256),('out_t',14),('out_v',1),('out_epoch',16),('out_layer',6),('fault',1)])]:
            offset=0
            for field,width in fields:
                for bit in range(width):
                    pp=field if width==1 else f'{field}[{bit}]'
                    cf=('pc_'+field if direction=='req' else {'out_valid':'pc_valid','out_data':'pc_data','out_t':'pc_t','out_v':'pc_v','out_epoch':'pc_epoch','out_layer':'pc_layer','fault':'pc_fault'}[field])
                    cp=f'{cf}[{q*width+bit}]'
                    relay=f'{direction}{q}';rb=offset+bit
                    chain=[('rowctl',cp),(relay,f'a[{rb}]'),(relay,f'b[{rb}]'),(f'pc{q}',pp)] if direction=='req' else [(f'pc{q}',pp),(relay,f'a[{rb}]'),(relay,f'b[{rb}]'),('rowctl',cp)]
                    for k in (0,2):
                        a,b=[coord(*z) for z in chain[k:k+2]];dist=sum(abs(a[i]-b[i]) for i in range(2));nets.append(dict(branch=q,direction=direction,bit=rb,source=list(chain[k]),destination=list(chain[k+1]),distance_um=round(dist,3)))
                offset+=width
            assert offset==(38 if direction=='req' else 295)
    overlaps=[]
    for i,a in enumerate(homes):
        ax,ay=a['xy'];aw,ah=masters[a['master']]['outline']
        assert ax>=0 and ay>=0 and ax+aw<=237.6+1e-6 and ay+ah<=1512
        for b in homes[i+1:]:
            bx,by_=b['xy'];bw,bh=masters[b['master']]['outline']
            if min(ax+aw,bx+bw)>max(ax,bx)+1e-6 and min(ay+ah,by_+bh)>max(ay,by_)+1e-6:overlaps.append([a['name'],b['name']])
    assert not overlaps,overlaps
    worst=max(nets,key=lambda x:x['distance_um']);assert worst['distance_um']<=500,worst
    # Check actual face spacing after track snapping, across all port windows.
    for name,d in masters.items():
        for face in 'WESN':
            ps=sorted((p['xy'][1 if face in 'WE' else 0],n) for n,p in d['pins'].items() if p['face']==face)
            assert all(b[0]-a[0]>=(.192 if face in 'SN' else .096)-1e-6 for a,b in zip(ps,ps[1:])),(name,face)
    OUT.mkdir(parents=True,exist_ok=True)
    for name,d in masters.items():
        lines=[]
        for p,v in d['pins'].items():
            x,y=v['xy'];sz='.144 .024' if v['face'] in 'WE' else '.024 .144'
            lines.append(f'place_pin -pin_name {{{p}}} -layer {v["layer"]} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}}')
        (OUT/f'{name}.tcl').write_text('\n'.join(lines)+'\n')
    result=dict(status='OFFICIAL_GEOMETRY_ONLY; native clock/reset/STA and mapped leaf fit OPEN',group_outline=[237.6,1512],logical_latency_edges=5,physical_latency_edges=7,clock_family='core',period_ps=833.334,clock_entries=['ck']+[f'ck_pc[{q}]' for q in range(4)]+[f'ck_req_rly[{q}]' for q in range(4)]+[f'ck_rsp_rly[{q}]' for q in range(4)],masters=masters,homes=homes,reach=dict(edges=len(nets),worst=worst,over500=0),nets=nets,acquisition_cdc_latency='SEPARATE; not included in seven-edge landing return',macro=dict(master='ot_sram_1r1w_128x256_m1_r2c2',xy=[27.216,64.8],outline=[94.824,41.064],orientation='R0',channel_um=20))
    (OUT/'contract.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['reach']))
if __name__=='__main__':build()
