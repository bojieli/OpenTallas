#!/usr/bin/env python3
"""Replay only source-owned field geometry on a pinned PRE-FINALIZE plan.

This is deliberately not a die binding or final GEN. Unknown relay placement,
clock/reset trees, native cuts and later-resized view families remain explicit
obligations. Every pair/ROM/sequence transform and every bank bit is recorded or
hashed, and all new rectangle intersections are reported without suppression.
"""
import argparse, collections, copy, gzip, hashlib, json, math, re, struct
from pathlib import Path
from s81.qbank_frame import canonical, EXTRA, N_EXTRA, SLOT_EXTRA, HARD_BANK_H, N_BANK_H


def read_json(path):
    p=Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def lef(path):
    p=Path(path);raw=p.read_bytes();text=(gzip.decompress(raw) if p.suffix=='.gz' else raw).decode()
    size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
    assert size, ('missing literal SIZE',str(p))
    pins={};name=None;layer=None
    for line in text.splitlines():
        t=line.split()
        if not t:continue
        if t[0]=='PIN':name=t[1];layer=None
        elif name and t[0]=='END' and len(t)>1 and t[1]==name:name=None
        elif name and t[0]=='LAYER':layer=t[1]
        elif name and t[0]=='RECT':pins.setdefault(name,[]).append((layer,list(map(float,t[1:5]))))
    return dict(size=list(map(float,size.groups())),pins=pins,sha256=hashlib.sha256(raw).hexdigest(),path=str(p))


def world(i,rect,w,h):
    x0,y0,x1,y1=rect;x=(x0+x1)/2;y=(y0+y1)/2
    if i['orient'] in ('MY','R180'):x=w-x
    if i['orient'] in ('MX','R180'):y=h-y
    assert i['orient'] in ('R0','MY','MX','R180'),i['orient']
    return i['x']+x,i['y']+y


def intersections(insts, changed):
    grid=collections.defaultdict(list)
    for i in insts.values():
        for a in range(math.floor(i['x']/100),math.floor((i['x']+i['w'])/100)+1):
            for b in range(math.floor(i['y']/100),math.floor((i['y']+i['h'])/100)+1):grid[a,b].append(i)
    pairs={}
    for name in changed:
        i=insts[name];seen=set()
        for a in range(math.floor(i['x']/100),math.floor((i['x']+i['w'])/100)+1):
            for b in range(math.floor(i['y']/100),math.floor((i['y']+i['h'])/100)+1):
                for j in grid[a,b]:
                    if j['name']==name or j['name'] in seen:continue
                    seen.add(j['name'])
                    dx=min(i['x']+i['w'],j['x']+j['w'])-max(i['x'],j['x'])
                    dy=min(i['y']+i['h'],j['y']+j['h'])-max(i['y'],j['y'])
                    if dx>1e-6 and dy>1e-6:pairs[tuple(sorted([name,j['name']]))]=[round(dx,6),round(dy,6)]
    return pairs


def replay(plan, old, new):
    before={i['name']:copy.deepcopy(i) for i in plan['insts']};after=copy.deepcopy(before)
    changed={};pair_records=[];slot_records=[]
    oldfs={f['root']:f for f in old['placements']};newfs={f['root']:f for f in new['placements']}
    def move(name,dy,why,h=None,w=None):
        assert name in after,('missing source-owned object',name)
        i=after[name];assert name not in changed,('duplicate transform',name)
        i['y']=round(i['y']+dy,6)
        if h is not None:i['h']=h
        if w is not None:i['w']=w
        changed[name]=dict(instance=name,master=i['master'],reason=why,old=before[name],candidate=copy.deepcopy(i))
    for root,f in oldfs.items():
        nf=newfs[root];frame_dy=nf['origin_um'][1]-f['origin_um'][1]
        for s,y in enumerate(f['slot_offsets_um']):
            dy=round(frame_dy+nf['slot_offsets_um'][s]-y,6)
            slot_records.append(dict(root=root,slot=s,old_origin_y=f['origin_um'][1]+y,new_origin_y=nf['origin_um'][1]+nf['slot_offsets_um'][s],dy=dy))
            move(f't{root}_{s}',dy,'slot station follows cfg row')
        for p,k,s,lane in f['packed_elements']:
            base=round(frame_dy+nf['slot_offsets_um'][s]-f['slot_offsets_um'][s],6)
            edy=round(base+(EXTRA if k=='q' else 0),6)
            move(f'e{p}',edy,'element follows coherent row')
            if k=='BF':
                for suffix in ['w','e']:
                    if f'e{p}{suffix}' in after:move(f'e{p}{suffix}',edy,'BF column follows front, chirality unchanged')
            if k=='q':
                # Frame dimensions retain the generator's .024 shave. Use the
                # actual closed LEF SIZE for collision and pin proof here.
                move(f'bs{p}',edy-EXTRA,'S hard bank grows away from element',h=HARD_BANK_H,w=60.48)
                move(f'bn{p}',edy,'N hard bank grows away from element',h=N_BANK_H,w=60.48)
            for j in range(7):move(f'c{p}_{j}',base,'cfg7 ROM row moves below S bank')
            move(f's{p}',base,'cfg7 sequencer follows ROM row')
            pair_records.append(dict(pair=p,kind=k,root=root,slot=s,lane=lane,element_dy=edy,cfg_dy=base,
                                     normal_data_cycles_added=0,rom_count=7,orientation_preserved=True))
        move(f'cf{root}',round(frame_dy,6),'column FIFO follows bottom of grown frame')
        for name,i in before.items():
            if re.fullmatch(r'n'+str(root)+r'_\d+',name):move(name,round(frame_dy,6),'return nodes retain generator rank from frame bottom')
    assert len(pair_records)==old['pair_count']
    assert len({r['pair'] for r in pair_records})==old['pair_count']
    assert all(before[n]['orient']==after[n]['orient'] for n in changed)
    return before,after,changed,pair_records,slot_records


def bank_bits(plan,before,after,qleaf,sleaf,nleaf):
    digest=hashlib.sha256();count=collections.Counter();maxima={};segments={};summary=[];controls=[]
    links={}
    for _name,_kind,width,ends in plan['buses']:
        if len(ends)!=2:continue
        for bank,bport in ends:
            if bank.startswith(('bs','bn')) and bank[2:].isdigit():
                ep=[(i,p) for i,p in ends if i=='e'+bank[2:]]
                if ep:
                    key=(bank,ep[0][1]);assert key not in links,('duplicate bank endpoint',key)
                    links[key]=(bport,width)
    for name,i in before.items():
        if i['master']!='dsfd_qbank_S':continue
        p=name[2:];ename='e'+p;e=before[ename];ne=after[ename]
        row=[]
        for face,leaf,ports in [('S',sleaf,['cfg','go','x0','x1']),('N',nleaf,['r0','r1','st'])]:
            bank=('bs' if face=='S' else 'bn')+p;nb=after[bank];b=before[bank]
            mdx=0;mingap=float('inf');maxgap=0;segment=0;n=0
            for control in ['ck[0]','rs[0]']:
                assert control in leaf['pins']
                controls.append(dict(bank=bank,pin=control,layer=leaf['pins'][control][0][0],
                                     candidate_world=world(nb,leaf['pins'][control][0][1],*leaf['size'])))
            for port in ports:
                names=plan['pins'][e['master']+'|'+port]
                bport,width=links[(bank,port)];assert width==len(names),(bank,port,width,len(names))
                for k,pin in enumerate(names):
                    pin=pin.replace('\\','');bpin=f'{bport}[{k}]'
                    assert pin in qleaf['pins'] and bpin in leaf['pins'],(p,port,k,pin,bpin)
                    qr=qleaf['pins'][pin][0][1];br=leaf['pins'][bpin][0][1]
                    ep=world(ne,qr,*qleaf['size']);bp=world(nb,br,*leaf['size'])
                    oldep=world(e,qr,*qleaf['size']);oldbp=world(b,br,*leaf['size'])
                    # Preserve actual per-bit identity, X relation and chirality;
                    # old raw-table actual-Y was invalid due to undersized slot.
                    assert abs((ep[0]-bp[0])-(oldep[0]-oldbp[0]))<1e-7
                    gap=ep[1]-bp[1] if face=='S' else bp[1]-ep[1]
                    assert gap>0,('bank on wrong side of real element pin',bank,pin,gap)
                    mdx=max(mdx,abs(ep[0]-bp[0]));mingap=min(mingap,gap);maxgap=max(maxgap,gap);segment=max(segment,abs(ep[0]-bp[0])+gap);n+=1
                    digest.update(f'{bank}|{bpin}|{ename}|{pin}|'.encode());digest.update(struct.pack('!dddd',*ep,*bp))
            expected=604 if face=='S' else 128;assert n==expected,(bank,n)
            count[face]+=n;maxima[face]=max(maxima.get(face,0),mdx);segments[face]=max(segments.get(face,0),segment)
            row.append(dict(bank=bank,bits=n,max_x_jog_um=round(mdx,6),max_segment_manhattan_um=round(segment,6),vertical_center_gap_um=[round(mingap,6),round(maxgap,6)]))
        summary.append(dict(pair=int(p),banks=row))
    return dict(checked_bits=dict(count),sha256=digest.hexdigest(),max_x_jog_um=maxima,max_segment_manhattan_um=segments,pairs=summary,clock_reset_pins=controls,
                meaning='Every real bank/element bit identity, unchanged X relation/chirality and candidate actual Y gap checked. Pre-existing X jog is retained, not claimed zero. Historical undersized raw-table actual Y is not valid adoption geometry.')


def main():
    ap=argparse.ArgumentParser()
    for n in ['plan','layout','q-lef','s-lef','n-lef','out']:ap.add_argument('--'+n,required=True,type=Path)
    a=ap.parse_args();plan=read_json(a.plan);old=read_json(a.layout)
    assert plan['scope'].startswith('FIRST_PASS_'),plan['scope']
    new=canonical(old,cfifo_h=95.04);b,n,changes,pairs,slots=replay(plan,old,new)
    q,s,nn=lef(a.q_lef),lef(a.s_lef),lef(a.n_lef)
    assert q['size']==[510.84,221.4] and s['size']==[60.48,25.92] and nn['size']==[60.48,8.64]
    bitproof=bank_bits(plan,b,n,q,s,nn)
    old_hits=intersections(b,changes);new_hits=intersections(n,changes)
    added=[dict(instances=list(k),masters=[n[z]['master'] for z in k],overlap_um=v) for k,v in new_hits.items() if k not in old_hits]
    core={'q','qbank','cfg','seq','bf','bfcol','sstn','cfifo','node'}
    core_added=[r for r in added if all(n[z]['kind'] in core for z in r['instances'])]
    a.out.mkdir(parents=True,exist_ok=True)
    outputs={'canonical_candidate.json':new,'transforms.json':list(changes.values()),'pairs.json':pairs,'slots.json':slots,'bank_bits.json':bitproof,'new_intersections.json':added,'core_new_intersections.json':core_added}
    for name,value in outputs.items():(a.out/name).write_text(json.dumps(value,indent=1)+'\n')
    report=dict(scope=plan['scope'],source=plan['source_commit'],pair_population=dict(total=len(pairs),q=sum(r['kind']=='q' for r in pairs),BF=sum(r['kind']=='BF' for r in pairs)),
                transformed_instances=len(changes),bank_bits=bitproof['checked_bits'],bank_bit_sha256=bitproof['sha256'],max_bank_x_jog_um=bitproof['max_x_jog_um'],max_bank_segment_manhattan_um=bitproof['max_segment_manhattan_um'],
                slots=len(slots),minimum_street_um=min(r['available_um'] for r in new['qbank_hard_frame']['streets']),all_added_intersections=len(added),source_core_added_intersections=len(core_added),
                source_core_kind_definition=sorted(core),orientation_legality='OPEN: geometric transforms preserve MY/MX but do not establish selected LEF orientation legality; root selected-view SYMMETRY reconciliation required, no header patch/waiver.',unmoved_glue_note='Other relay and reset/clock geometry remains original PRE-FINALIZE; every new intersection is exposed. Full source GEN must replan these before adoption.',
                normal_data_cycles_added=0,initialization_release_extra_edges_for_nr1=1,rtl_topology_changed=False,
                latency_scope='Source row transform adds no register. Full hop replan may add relay stages and must price its resulting static schedule before adoption.',bus_endpoint_sha256=hashlib.sha256(json.dumps(plan['buses'],separators=(',',':')).encode()).hexdigest(),
                leaf_sources={k:{kk:vv for kk,vv in v.items() if kk!='pins'} for k,v in [('Q',q),('qS',s),('qN',nn)]},
                files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.plan,a.layout,Path(__file__),Path(__file__).with_name('qbank_frame.py')]},
                adoption=False,remaining=['actual cfg7/BF/other-family LEF endpoint cuts and fit where views missing','all incident unchanged relay/clock/reset rebuild','full source-current final GEN','TT setup/FF hold/native/DRC0 die integration'])
    (a.out/'report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))

if __name__=='__main__':main()
