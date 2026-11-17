#!/usr/bin/env python3
"""NF15e LEP candidate: consume its existing placement contract, stage long legs.
Writes a separate candidate; no in-place canonical update and no adoption.
"""
import argparse,copy,hashlib,json,math,re
from pathlib import Path

HUB=[1174.0,567.0,1230.0,595.0]
TXW,TXH=169.368,29.16
RXW,RXH=51.432,20.808
LDW,LDH=91.8,39.432
ROW={1:518.412,2:561.612,3:604.812}
SLOT=lambda k:69.228+181.44*k
TX={0:[(3,5),(3,6),(3,7),(2,5),(2,7)],
    1:[(3,0),(3,1),(3,2),(2,0),(2,1)],
    2:[(1,0),(1,1),(1,2),(2,2),(2,3)],
    3:[(1,5),(1,6),(1,7),(1,8),(2,8)]}
LAND=[(3,3),(3,8),(2,7),(1,3),(1,4)]

def group(path,rect,tag):
    # OpenDB retains backslashes in mapped generate-array names.
    p=re.escape(path).replace(r'\[',r'\\\[').replace(r'\]',r'\\\]')
    return dict(prefix=p,rect_um=rect,tag='stage:'+tag)

def gap(a,b):
    return max(abs(a[i]-b[j]) + abs(a[k]-b[l]) for i,j in [(0,0),(0,2),(2,0),(2,2)] for k,l in [(1,1),(1,3),(3,1),(3,3)])

def apply(raw):
    p=copy.deepcopy(raw);t=p['partition_types']['hd_lep0N'];c=t['contents'][0]
    assert c['module']=='ot_s81hd_lep0N_noidx_core'
    params=c['params'];assert (params['PIN'],params['POUT'],params['KRX'])==(2,3,"16'h1220")
    params.update(PIN=4,POUT=4,KRX="16'h1330")
    macros={x['inst']:x for x in t['hard_cores']};changes=[]
    def move(name,xy):
        m=macros[name];before=m['origin_um'];m['origin_um']=[round(x,6) for x in xy]
        if before!=m['origin_um']:changes.append(dict(instance=name,before=before,after=m['origin_um']))
    for lane,slots in TX.items():
        for b,(row,col) in enumerate(slots):
            move(f'u_core.u.u_lep.u.g_tx[{lane}].g_safe_write.u_m.g_bank[{b}].u_m',[SLOT(col),ROW[row]])
    for lane in range(4):
        for b in range(5):
            if lane==0:xy=[1020+59.04*b,637.2]
            elif lane in (1,2):
                row=3 if lane==1 else 2
                xy=[SLOT(4)+59.04*(b%3),ROW[row]+21.6*(b//3)]
            else:xy=[1806.0,440.4+21.6*b]
            move(f'u_core.u.u_lep.u.g_rx[{lane}].g_sa.g_true_sram.u_rx_mem.g_bank[{b}].u_m',xy)
    for b,(row,col) in enumerate(LAND):
        xy=[SLOT(col),ROW[row]] if b<2 else [861.0,350.0+43.2*(b-2)]
        move(f'u_core.u.u_land.g_sram.g_t[{b}].g_128.u_m',xy)
    gs=[]
    pin=[[1782,357,1818,393],[1762,547,1798,583],[1500,591.8,1608,603.8],[1230,591.8,1338,603.8]]
    pout=[[1330,548.6,1438,560.6],[1550,548.6,1658,560.6],[1760,450,1796,486],[1828,240,1864,276]]
    plw=[[1421,591.8,1449,603.8],[1726.308,591.8,1746.308,603.8],[1819.6,856,1869.6,868]]
    for key,rs in [('pin',pin),('pout',pout),('plw',plw)]:
        for j,r in enumerate(rs):gs.append(group(f'u_core.u.g_{key}.g_s[{j}]',r,f'{key}_s{j}'))
    txi={0:[[1087.38,591.8,1151.38,603.8]],1:[[920,591.8,984,603.8],[580,591.8,644,603.8]],
         2:[[880,548.6,944,560.6],[560,548.6,624,560.6]],3:[[1351.4,591.8,1409.4,603.8]]}
    for lane,rs in txi.items():
        for j,r in enumerate(rs):gs.append(group(f'u_core.u.u_lep.u.g_tx[{lane}].g_txi.g_s[{j}]',r,f'txi{lane}_s{j}'))
    krx={1:[[400,643.5,450,655.5],[740,643.5,790,655.5],[1020,591.8,1070,603.8]],
         2:[[375,548.6,425,560.6],[695,548.6,745,560.6],[1015,548.6,1065,560.6]],
         3:[[1450,548.6,1500,560.6]]}
    for lane,rs in krx.items():
        for j,r in enumerate(rs):
            for dr in ['rxf','rxr']:gs.append(group(f'u_core.u.g_kl[{lane}].g_{dr}.g_s[{j}]',r,f'krx{lane}_s{j}'))
    t['clock']['landing_contract']['native_stage_groups'].update(params=copy.deepcopy(params),groups=gs)
    t['note']=t.get('note','')+' | NF15e candidate: lane-local SRAMs, required native stage placement; PIN+2,POUT+1,KRX lane1/2 +1; exact arithmetic and word/control alignment unchanged.'
    rects=[]
    for m in t['hard_cores']:
        x,y=m['origin_um'];w,h=m['outline_um'];rects.append((m['inst'],[x,y,x+w,y+h]))
    overlaps=[]
    for i,(n,a) in enumerate(rects):
        for nn,b in rects[i+1:]:
            if min(a[2],b[2])-max(a[0],b[0])>1e-5 and min(a[3],b[3])-max(a[1],b[1])>1e-5:overlaps.append([n,nn])
    conflicts=[]
    for g in gs:
        a=g['rect_um']
        for n,b in rects:
            if min(a[2],b[2])-max(a[0],b[0])>1e-5 and min(a[3],b[3])-max(a[1],b[1])>1e-5:conflicts.append([g['tag'],n])
    hub_conflicts=[n for n,b in rects if min(HUB[2],b[2])-max(HUB[0],b[0])>1e-5 and min(HUB[3],b[3])-max(HUB[1],b[1])>1e-5]
    stage_conflicts=[]
    for i,g in enumerate(gs):
        a=g['rect_um']
        for gg in gs[i+1:]:
            b=gg['rect_um']
            if g['tag']!=gg['tag'] and min(a[2],b[2])-max(a[0],b[0])>1e-5 and min(a[3],b[3])-max(a[1],b[1])>1e-5:stage_conflicts.append([g['tag'],gg['tag']])
    buses={b['name']:b for b in t['buses']}
    def port(name):
        ys=buses[name]['window_um'];return [t['outline_um'][0]-.1,ys[0],t['outline_um'][0]-.1,ys[1]]
    chains={'PIN':[port('lepk_i0')]+pin+[HUB],'POUT':[HUB]+pout+[port('lepk_o0')],
            'KRX1':[[71.12,665.322,463.08,665.322]]+krx[1]+[HUB],
            'KRX2':[[71.12,509.718,463.08,509.718]]+krx[2]+[HUB],
            'KRX3':[[1351.32,509.718,1743.28,509.718]]+krx[3]+[HUB]}
    reaches={k:[round(gap(a,b),3) for a,b in zip(v,v[1:])] for k,v in chains.items()}
    model=dict(kind='NF15E_CANDIDATE_GEOMETRY_NOT_PLACEMENT_NOT_SIGNOFF',added_cycles=dict(PIN=2,POUT=1,KRX_lane1=1,KRX_lane2=1),
        outline_unchanged=t['outline_um'],hub_anchor_rect_um=HUB,required_groups=len(gs),macro_changes=len(changes),
        macro_overlaps=overlaps,stage_macro_overlaps=conflicts,stage_group_overlaps=stage_conflicts,hub_macro_overlaps=hub_conflicts,full_rect_hop_um=reaches,
        reaches405=all(x<=405 for v in reaches.values() for x in v),
        note='Hub rectangle is a sizing anchor, not evidence of mapped placement. TX/RX/LAND internal register locations require the generated-kit review before route. All original source and failed verdicts retained.')
    return p,dict(macro_origin_changes=changes,params_before=raw['partition_types']['hd_lep0N']['contents'][0]['params'],params_after=params,model=model)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('base',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    raw=json.loads(a.base.read_text());p,d=apply(raw);d['base_sha256']=hashlib.sha256(a.base.read_bytes()).hexdigest()
    (a.out/'source_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'delta.json').write_text(json.dumps(d,indent=1)+'\n')
    print(json.dumps(d['model'],indent=1))
