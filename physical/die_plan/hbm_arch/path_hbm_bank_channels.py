#!/usr/bin/env python3
"""Keep current HBM masters and give bank FT real core-free channels.

The two N-turn bank columns grow while the hubs give up509.76um each.
All current hard-core masters and outlines stay unchanged. Hub cores are
re-placed with real17.28um channels. Coreless neighbouring tiles provide the
shared-face overlap; L28 turns through the SU bottom corridor. Physical
stations and clock must be rebuilt before this candidate can route.
"""
import argparse,copy,collections,json,math,re,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'tools'/'die_plan'),str(HERE)]
import schema as S
import cores_b2 as CB


def pack_windows(p,parts,T,pairs,bottom=None,ppu=5.5):
    changes=[]
    for ns in pairs:
        prs=[q for q in p['ports'] if set(q[z]['part'] for z in ['src','dst'])==set(ns)]
        if not prs:continue
        horizontal=prs[0]['face'] in 'EW';axis=1 if horizontal else 0
        if any((q['face'] in 'EW')!=horizontal for q in prs):raise ValueError(f'mixed interface {ns}')
        lo=max(parts[n]['origin_um'][axis] for n in ns)+8.64
        hi=min(parts[n]['origin_um'][axis]+T[parts[n]['type']]['outline_um'][axis] for n in ns)-8.64
        if horizontal and bottom is not None:lo=max(lo,bottom)
        lo=math.ceil(lo/.192-1e-8)*.192;hi=math.floor(hi/.192+1e-8)*.192
        prs.sort(key=lambda q:(sum(q['window_um']),q['id']))
        sizes=[max(8.64,math.ceil(S.window_for(0,S.port_pins_count(q),q['layers'],per_um=ppu)/.192-1e-8)*.192) for q in prs]
        need=sum(sizes)+.576*(len(sizes)-1)
        if need>hi-lo+1e-6:raise ValueError(f'{ns}: {need:.3f}um windows need >{hi-lo:.3f}um sharedface')
        cur=lo
        for q,L in zip(prs,sizes):
            old=list(q['window_um']);q['window_um']=[round(cur,3),round(cur+L,3)];cur+=L+.576
            changes.append({'port':q['id'],'before':old,'after':q['window_um']})
    return changes


def update_core(t,c,new):
    old=list(c['origin_um']);c['origin_um']=list(new)
    for ct in t.get('contents',[]):
        if ct['inst']==c['inst'] and 'origin_um' in ct:ct['origin_um']=list(new)
    for tap in t.get('clock',{}).get('taps',[]):
        if (tap['name']==c['inst'] or tap['name'].startswith(c['inst']+'.')):tap['xy']=[round(tap['xy'][i]+new[i]-old[i],3) for i in [0,1]]
    return {'inst':c['inst'],'before':old,'after':new}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('output must be new')
    p=json.loads((a.src/'die_plan.json').read_text());T=p['partition_types'];parts={q['name']:q for q in p['partitions']};r={'not_release_ready':True,'width_changes':{},'cores':{},'windows':[],'global_outline_delta_um':[0,0]}
    oldT=copy.deepcopy(T);banks=['q_b013','q_b003','q_b012','q_b002','q_b011','q_b001','q_b010','q_b000']
    widths={'q_b013':552.96,'q_b003':552.96,'q_b012':552.96,'q_b002':380.16,'q_b011':380.16,'q_b001':786.24,'q_b010':829.44,'q_b000':457.92}
    xx=parts['NW_b013']['origin_um'][0]
    for tn in banks:
        t=T[tn];oldw=t['outline_um'][0];w=widths[tn];t['outline_um'][0]=w;r['width_changes'][tn]=w-oldw
        for side in ['NW_','NE_']:
            q=parts[side+tn[2:]];q['origin_um'][0]=round(xx if side=='NW_' else p['die']['outline_um'][0]-xx-w,3)
        xx+=w
        # Existing exact masters: the two leaf pieces beside one another,
        # SRAM-bearing bank piece on the next row. Their top is <=920.16um.
        cs=t['hard_cores'];big=max(cs,key=lambda c:c['outline_um'][0]*c['outline_um'][1]);leaves=[c for c in cs if c is not big]
        dx={'q_b001':233.28,'q_b010':8.64}.get(tn,8.64)
        moves=[];lx=dx;lh=0
        for c in leaves:
            moves.append(update_core(t,c,[lx,17.28]));lx+=c['outline_um'][0]+17.28;lh=max(lh,c['outline_um'][1])
        moves.append(update_core(t,big,[dx,round(lh+34.56,3)]));r['cores'][tn]=moves
        if any(c['origin_um'][0]+c['outline_um'][0]>w-8.64+1e-6 for c in cs):raise ValueError(f'{tn}: core width overflow')
        for ct in t.get('contents',[]):
            if ct.get('outline_um')==oldT[tn]['outline_um']:ct['outline_um']=list(t['outline_um'])
        t['die_ft_bands']=[{'dir':'EW','span_um':[946.08,t['outline_um'][1]-8.64],'layers':['M4','M6'],'die_share':1.0,'note':'Physical bank cores below920.16um; full core-free EW FT corridor'}]
        if tn in ['q_b001','q_b010']:
            t['die_ft_bands'].append({'dir':'NS','span_um':[0,224.64] if tn=='q_b001' else [552.96,829.44],'layers':['M5','M7'],'die_share':1.0,'note':'Core-free N-turn landing corridor; actual masters occupy separate E bay'})
    growth=xx-(parts['NW_hub']['origin_um'][0]);r['hub_width_taken_um']=round(growth,3)
    for tn,pn in [('q_hub_nw','NW_hub'),('q_hub_ne','NE_hub')]:
        t=T[tn];oldw,h=t['outline_um'];w=round(oldw-growth,3);t['outline_um'][0]=w
        parts[pn]['origin_um'][0]=round(xx if pn=='NW_hub' else p['die']['outline_um'][0]-xx-w,3)
        cs=t['hard_cores'];attrs={c['inst']:[(1,( (c['origin_um'][0]+c['outline_um'][0]/2)*w/oldw,c['origin_um'][1]+c['outline_um'][1]/2))] for c in cs}
        pos=CB.place_flow([(c['inst'],*c['outline_um']) for c in cs],w,h,attrs,passes=1,band=17.28,chan=17.28)
        if pos is None:raise ValueError(f'{tn}: hub cores do not fit resized outline')
        r['cores'][tn]=[update_core(t,c,list(pos[c['inst']])) for c in cs]
        r.setdefault('hub_core_fill',{})[tn]=sum(c['outline_um'][0]*c['outline_um'][1] for c in cs)/(w*h)
        # Die-owned strips will be rebuilt from the new actual FT windows.
        t.pop('die_ft_bands',None)
    # Recover the NS overlap below each hub using the empty neighbouring tile.
    T['q_su21']['outline_um'][0]=round(T['q_su21']['outline_um'][0]+345.6,3)
    T['q_spu1']['outline_um'][0]=round(T['q_spu1']['outline_um'][0]-345.6,3)
    if T['q_spu1'].get('hard_cores'):raise ValueError('spu1 is not coreless')
    for side in ['NW_','NE_']:
        if side=='NW_':parts[side+'spu1']['origin_um'][0]+=345.6
        else:parts[side+'su21']['origin_um'][0]-=345.6
    T['q_su01']['outline_um'][0]+=129.6
    T['q_spu0']['outline_um'][0]-=129.6
    if T['q_spu0'].get('hard_cores'):raise ValueError('spu0 is not coreless')
    for side in ['NW_','NE_']:
        if side=='NW_':parts[side+'spu0']['origin_um'][0]+=129.6
        else:parts[side+'su01']['origin_um'][0]-=129.6
    # L28 reaches SU01 above its widened bank, then turns W into SU00's
    # empty bottom band. Preserve the real abutment rather than moving a
    # window beyond its neighbouring face.
    T['q_su01']['ft_slots'].append({'name':'L28_detour','in_face':'S','out_face':'W','width':1615,'stations':3})
    sl=next(z for z in T['q_su00']['ft_slots'] if z['name']=='L28x3');sl['in_face']='E'
    for k in ['regs_um','bit_sites_um','bit_site_cell_um']:sl.pop(k,None)
    for side,lid in [('NW_','L28'),('NE_','L28m')]:
        pr=next(v for v in p['ports'] if v['id']==lid+'_2')
        pr['dst']={'part':side+'su01','bus':'L28_detour_i'}
        extra=copy.deepcopy(pr);extra['id']=lid+'_detour';extra['face']='W' if side=='NW_' else 'E'
        extra['src']={'part':side+'su01','bus':'L28_detour_o'};extra['dst']={'part':side+'su00','bus':'L28x3_i'}
        extra.pop('order',None)
        extra['layers']=['M4','M6'];extra['window_um']=[parts[side+'su00']['origin_um'][1]+150,parts[side+'su00']['origin_um'][1]+444]
        p['ports'].append(extra)
        lane=next(z for z in p['lanes'] if z['id']==lid);at=lane['ports'].index(pr['id']);lane['ports'].insert(at+1,extra['id'])
    r['windows']+=pack_windows(p,parts,T,[('NW_su00','NW_su01'),('NE_su00','NE_su01')],ppu=5.5)
    # All bank EW shared faces become real channels above their physical cores.
    pairs={tuple(sorted(q[z]['part'] for z in ['src','dst'])) for q in p['ports'] if q['face'] in 'EW' and any(parts.get(q[z]['part'],{}).get('type') in banks for z in ['src','dst'])}
    r['windows']+=pack_windows(p,parts,T,sorted(pairs),bottom=parts['NW_b000']['origin_um'][1]+946.08,ppu=5.5)
    # Hub N/S shared interfaces remain on their actual abutment at default6.
    hpairs={tuple(sorted(q[z]['part'] for z in ['src','dst'])) for q in p['ports'] if q['face'] in 'NS' and any(q[z]['part']=='NW_hub' for z in ['src','dst']) and all(q[z]['part'] in parts for z in ['src','dst'])}
    r['windows']+=pack_windows(p,parts,T,sorted(hpairs),ppu=6.0)
    # Re-window the two bank N-turn outputs, keeping their real SU00 neighbour.
    for side in ['NW_','NE_']:
        for tn,sn in [('q_b001','L36x3'),('q_b010','L28x2')]:
            pn=side+tn[2:];q=parts[pn];pr=next(v for v in p['ports'] if v['src']=={'part':pn,'bus':sn+'_o'})
            L=math.ceil(S.window_for(0,S.port_pins_count(pr),pr['layers'],per_um=6)/.192-1e-8)*.192
            left=(tn=='q_b001')==(side=='NW_')
            lo=q['origin_um'][0]+1 if left else q['origin_um'][0]+T[tn]['outline_um'][0]-1-L
            r['windows'].append({'port':pr['id'],'before':list(pr['window_um']),'after':[round(lo,3),round(lo+L,3)]});pr['window_um']=[round(lo,3),round(lo+L,3)]
        pr=next(v for v in p['ports'] if v['src']['part']==side+'b010' and v['src']['bus']=='L148x4_o');q=parts[side+'b010'];w=T[q['type']]['outline_um'][0]
        lo=max(q['origin_um'][0]+1,parts[side+'su20']['origin_um'][0]+1) if side=='NW_' else min(q['origin_um'][0]+w-9.64,parts[side+'su20']['origin_um'][0]+T['q_su20']['outline_um'][0]-9.64);pr['window_um']=[round(lo,3),round(lo+8.64,3)]
    # Re-window displaced soft NS neighbours (e.g. spu1->spb2) on their
    # actual overlap. Hard-macro pin contracts must not move here.
    badpairs=set()
    for pr in p['ports']:
        if pr['face'] not in 'NS' or not all(pr[z]['part'] in parts for z in ['src','dst']):continue
        if not any(pr[z]['part'].startswith('NW_') for z in ['src','dst']):continue
        ns=tuple(sorted(pr[z]['part'] for z in ['src','dst']))
        lo=max(parts[n]['origin_um'][0] for n in ns);hi=min(parts[n]['origin_um'][0]+T[parts[n]['type']]['outline_um'][0] for n in ns)
        if min(pr['window_um'])<lo-1e-6 or max(pr['window_um'])>hi+1e-6:
            if any(T[parts[n]['type']].get('hard') for n in ns):raise ValueError(f'hard NS neighbour cannot be repinned: {ns}')
            badpairs.add(ns)
    r['windows']+=pack_windows(p,parts,T,sorted(badpairs),ppu=6.0)
    # One canonical bit table for MY replicas; independently packing the
    # mirrored face reverses unequal quantized gaps and creates variants.
    ports={q['id']:q for q in p['ports']}
    for pr in list(p['ports']):
        mm=re.match(r'^(L[0-9]+)(_.+)$',pr['id'])
        if not mm:continue
        other=ports.get(mm[1]+'m'+mm[2])
        if other is None or other['width']!=pr['width']:continue
        def mapped(e):return {'part':e['part'].replace('NW_','NE_',1),'bus':e['bus']}
        if mapped(pr['src'])!=other['src'] or mapped(pr['dst'])!=other['dst']:continue
        lo,hi=pr['window_um'];other['window_um']=[round(p['die']['outline_um'][0]-hi,3),round(p['die']['outline_um'][0]-lo,3)] if pr['face'] in 'NS' else [lo,hi]
    for tn in banks:
        T[tn]['clock']['tap_um']=[round(round(T[tn]['outline_um'][0]/2/8.64)*8.64,3),963.36]
    p['clock']['spine']['root_um']=[p['die']['outline_um'][0]/2,p['die']['outline_um'][1]/2]
    for t in T.values():
        if isinstance(t.get('face_pins_per_um'),dict):t.pop('face_pins_per_um')
    model=S.Plan(p);p['latency']['lanes']={lid:model.lane_latency(lid) for lid in model.lanes}
    r['required_next']='Rebuild every moved core/FT/reset/clock chain, price exact cycles, full G0/render before route'
    shutil.copytree(a.src,a.out);(a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'bank_channels_report.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:r[k] for k in ['width_changes','hub_width_taken_um','hub_core_fill','global_outline_delta_um']},indent=1))

if __name__=='__main__':main()
