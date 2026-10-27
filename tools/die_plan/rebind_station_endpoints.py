#!/usr/bin/env python3
"""Rebind changed hard-core station endpoints to real pin groups, refusing ambiguous peers.

IN is the current plan directory; --baseline is the pre-delta plan. Only stations
incident on changed core geometry/pin content are selected with a baseline.
Explicit --endpoint-map keys TYPE:STATION:launch|capture map to a reference string
or {core: actual_instance, ports: [physical_or_logical_ports]} for declared bundles.
No input alias or port-name similarity heuristic is used. Bare peers require an explicit native port/bit map; the peer-only core-conns
graph is diagnostic and never establishes a port binding. Use --route to run the existing
hbm_final_stations regeneration on fully resolved selected stations; old priced
counts are preserved and additions listed. Failed/unresolved stations retain their
complete source record. A candidate with unresolved or failed stations is FAIL.
This model transform does not authorize P&R, sign-off, or a latency adoption.
"""
import argparse,collections,copy,hashlib,json,math,re,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import hbm_final_stations as FS
import schema as S


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def logical(n):return re.sub(r'\[\d+\]$','',n)
def baseinst(n):return re.sub(r'__q\d+$','',n)
def md(a,b):return sum(abs(x-y) for x,y in zip(a,b))

def transform(h,p):
    x,y=p;w,hh=h['outline_um'];o=h.get('orient','R0')
    x,y={'R0':(x,y),'MX':(x,hh-y),'MY':(w-x,y),'R180':(w-x,hh-y)}[o]
    dx,dy=h.get('track_offset_um',[0,0]);ox,oy=h['origin_um']
    return [round(ox+dx+x,6),round(oy+dy+y,6)]

def split_ref(ref,cores):
    matches=[]
    for h in cores:
        name=h['inst'];bn=baseinst(name)
        if ref==name or ref.startswith(name+'.'):matches.append((len(name),h,ref[len(name):].lstrip('.')))
        elif ref==bn or ref.startswith(bn+'.'):matches.append((len(bn),h,ref[len(bn):].lstrip('.')))
    if not matches:return []
    longest=max(x[0] for x in matches)
    return [(h,p) for n,h,p in matches if n==longest]


class Resolver:
    def __init__(self,pd,raw,baseline=None):
        self.pd=Path(pd);self.raw=raw;self.types=raw['partition_types'];self.P=S.Plan(raw,self.pd/'die_plan.json')
        cc=self.pd/'core_conns.json';self.cc=json.loads(cc.read_text()) if cc.is_file() else {}
        self.baseline=Path(baseline) if baseline else None
        self.old=json.loads((self.baseline/'die_plan.json').read_text()) if baseline else None
        self.cache={};self.groupcache={};self.shacache={};self.changed={}
        for tn,t in self.types.items():
            oldt=self.old['partition_types'].get(tn,{}) if self.old else {}
            olds={h['inst']:h for h in oldt.get('hard_cores',[])};changed=set()
            for h in t.get('hard_cores',[]):
                old=olds.get(h['inst'])
                if not self.old or old is None or any(h.get(k)!=old.get(k) for k in ['origin_um','outline_um','track_offset_um','orient','pin_select']):changed.add(h['inst']);continue
                pf,of=h.get('pins_file'),old.get('pins_file')
                if not pf or not of or not (self.pd/pf).is_file() or not (self.baseline/of).is_file() or sha(self.pd/pf)!=sha(self.baseline/of):changed.add(h['inst'])
            self.changed[tn]=changed

    def affected(self,tn,ref):
        if not self.old:return True
        return any(h['inst'] in self.changed[tn] for h,p in split_ref(ref,self.types[tn].get('hard_cores',[])))

    def pins(self,h):
        pf=h.get('pins_file')
        if not pf or not (self.pd/pf).is_file():raise ValueError('core has no readable pin table')
        if pf not in self.cache:
            tab=json.loads((self.pd/pf).read_text())
            if not isinstance(tab,list):raise ValueError('pin table must be a list')
            self.cache[pf]=tab
        return self.cache[pf]

    def group(self,h,port):
        pp=self.pins(h);physical=h.get('pin_select',{}).get(port,port)
        # An explicit bit maps to that bit, including after logical->physical group selection.
        bm=re.search(r'(\[\d+\])$',port)
        if bm:physical=h.get('pin_select',{}).get(port[:bm.start()],port[:bm.start()])+bm[0]
        cachekey=(h['pins_file'],physical,bool(bm))
        if not hasattr(self,'groupcache'):self.groupcache={}
        if not hasattr(self,'pinindex'):self.pinindex={};self.portindex={}
        pf=h['pins_file']
        if pf not in self.pinindex:
            self.pinindex[pf]={p['name']:p for p in pp};self.portindex[pf]=collections.defaultdict(list)
            for p in pp:self.portindex[pf][logical(p['name'])].append(p)
        if cachekey not in self.groupcache:self.groupcache[cachekey]=([self.pinindex[pf][physical]] if physical in self.pinindex[pf] else []) if bm else self.portindex[pf].get(physical,[])
        selected=self.groupcache[cachekey]
        if not selected:raise ValueError(f'no actual pins for logical {port} / physical {physical}')
        w,hh=h['outline_um'];faces=set()
        for p in selected:
            x,y=p['x'],p['y'];face,dist=min([('W',abs(x)),('E',abs(w-x)),('S',abs(y)),('N',abs(hh-y))],key=lambda z:z[1])
            if dist>.1:raise ValueError(f'port {physical} has an interior pin; no signal face anchor')
            faces.add(face)
        if len(faces)!=1:raise ValueError(f'port {physical} spans faces {sorted(faces)}; declare exact bit/subgroup endpoint')
        point=[sum(p[k] for p in selected)/len(selected) for k in ['x','y']]
        if not hasattr(self,'shacache'):self.shacache={}
        if h['pins_file'] not in self.shacache:self.shacache[h['pins_file']]=sha(self.pd/h['pins_file'])
        return transform(h,point),dict(core=h['inst'],logical_port=port,physical_group=physical,pins=len(selected),face_core=next(iter(faces)),pins_file=h['pins_file'],pins_sha256=self.shacache[h['pins_file']],pin_group_extremes_um=[transform(h,[min(p['x'] for p in selected),min(p['y'] for p in selected)]),transform(h,[max(p['x'] for p in selected),max(p['y'] for p in selected)])])

    def resolve(self,tn,station,side,index,override=None):
        field='launch' if side==0 else 'capture';coord='from_um' if side==0 else 'to_um';ref=station.get(field,'')
        if not ref:raise ValueError('missing endpoint reference')
        cores=self.types[tn].get('hard_cores',[]);oldpoint=station[coord]
        if isinstance(override,dict):
            for mk,actual in [('expected_reference',ref),('expected_conn',station.get('conn')),('expected_r9_segments',station.get('r9_segments'))]:
                if mk in override and override[mk]!=actual:raise ValueError(f'explicit endpoint map {mk} does not match station')
            hits=[h for h in cores if h['inst']==override.get('core')]
            if len(hits)!=1:raise ValueError('explicit map core is not one actual instance')
            ports=override.get('ports')
            if not isinstance(ports,list) or not ports:raise ValueError('explicit bundle map needs nonempty ports')
            entries=[self.group(hits[0],p) for p in ports]
            faces={e[1]['face_core'] for e in entries}
            if len(faces)!=1:raise ValueError('declared bundle spans multiple physical faces')
            n=sum(e[1]['pins'] for e in entries)
            extremes=[p for e in entries for p in e[1]['pin_group_extremes_um']]
            bounds=[[min(p[0] for p in extremes),min(p[1] for p in extremes)],[max(p[0] for p in extremes),max(p[1] for p in extremes)]]
            return [sum(e[0][a]*e[1]['pins'] for e in entries)/n for a in [0,1]],dict(method='explicit_bundle',groups=[e[1] for e in entries],pin_group_extremes_um=bounds)
        if isinstance(override,str):ref=override
        if self.old and override is None and not self.affected(tn,ref):return list(oldpoint),dict(method='unchanged_baseline_anchor',ref=ref)
        if ref.startswith('face bus '):
            bus=ref[len('face bus '):];parts=[p for p in self.P.parts if self.P.parts[p]['type']==tn]
            if not parts:raise ValueError('type has no representative partition for face bus')
            f,win,ls,order=self.P._type_geom(parts[0],bus);c=sum(win)/2;w,hh=self.types[tn]['outline_um']
            return list({'W':(0,c),'E':(w,c),'S':(c,0),'N':(c,hh)}[f]),dict(method='type_face_bus',bus=bus,face=f)
        candidates=split_ref(ref,cores)
        if not candidates:raise ValueError('reference names no actual hard core; unchanged soft anchor needs baseline')
        segs=station.get('r9_segments')
        if len(candidates)>1 and isinstance(segs,list) and len(segs)>side:
            target=f'__q{segs[side]}';hit=[(h,p) for h,p in candidates if h['inst'].endswith(target)]
            if not hit:raise ValueError("explicit r9 segment has no matching actual replica")
            candidates=hit
        if len(candidates)>1:
            # Use the original point relative to baseline instances, not moved candidate geometry.
            oldcores={h['inst']:h for h in self.old['partition_types'][tn].get('hard_cores',[])} if self.old else {}
            ranked=[]
            for h,p in candidates:
                oh=oldcores.get(h['inst'],h);ox,oy=oh['origin_um'];w,hh=oh['outline_um']
                dist=max(ox-oldpoint[0],oldpoint[0]-ox-w,0)+max(oy-oldpoint[1],oldpoint[1]-oy-hh,0)
                ranked.append((dist,h,p))
            ranked.sort(key=lambda x:x[0])
            if len(ranked)>1 and abs(ranked[1][0]-ranked[0][0])<1e-6:raise ValueError('ambiguous replica: no segment and nearest old core is tied')
            candidates=[(ranked[0][1],ranked[0][2])]
        h,port=candidates[0]
        method='actual_pin_group'
        if not port:
            other=station.get('capture' if side==0 else 'launch','');oc=split_ref(other,cores)
            peers={x['inst'] for x,p in oc}|{baseinst(x['inst']) for x,p in oc}
            ports={}
            cc=self.cc.get(tn,{})
            for key in [h['inst'],baseinst(h['inst'])]:
                for p,ends in cc.get(key,{}).items():
                    if any(e.startswith('core:') and (e[5:] in peers or baseinst(e[5:]) in peers) for e in ends):ports[p]=ends
            raise ValueError(f'bare peer requires exact native endpoint map; {len(ports)} peer-graph diagnostic candidate ports: {sorted(ports)}')
        xy,detail=self.group(h,port);detail.update(method=method,reference=ref)
        return xy,detail


def guard_endpoint_groups(t,station,row,reach,raster=None):
    """Guard bus extremes, not only the group centre. Added signal registers are priced."""
    rr=copy.deepcopy(station)
    if raster is None:raster=FS.HR.Raster(*t['outline_um'],[FS.HR._core_rect(h) for h in t.get('hard_cores',[])])
    added=0
    for side in [0,1]:
        details=next((e for e in row['endpoints'] if e['field']==('launch' if side==0 else 'capture')),{})
        extrema=details.get('pin_group_extremes_um')
        if not extrema:continue
        points=[rr['from_um']]+rr.get('regs_um',[])+[rr['to_um']]
        adjacent=points[1] if side==0 else points[-2]
        otherdetails=next((e for e in row['endpoints'] if e['field']==('capture' if side==0 else 'launch')),{})
        otherextrema=otherdetails.get('pin_group_extremes_um',[adjacent]) if not rr.get('regs_um') else [adjacent]
        worst=max(md(p,q) for p in extrema for q in otherextrema)
        if worst<=reach+1e-6:continue
        anchor=rr['from_um'] if side==0 else rr['to_um'];G=FS.HR.G;best=None
        used={tuple(p) for p in rr.get('regs_um',[])}
        for ring in range(41):
            for dx in range(-ring,ring+1):
                for dy in range(-ring,ring+1):
                    if max(abs(dx),abs(dy))!=ring:continue
                    site=[round(round(anchor[0]/G+dx)*G,3),round(round(anchor[1]/G+dy)*G,3)]
                    if tuple(site) in used or not raster.free(*site):continue
                    dist=max(md(p,site) for p in extrema)
                    if dist>reach+1e-6 or md(site,adjacent)>reach+1e-6:continue
                    cost=md(site,anchor)+.01*md(site,adjacent)
                    if best is None or cost<best[0]:best=(cost,site,dist)
            if best:break
        if best is None:return None,dict(reason='pin-group extreme reach requires station split/replan',side=side,worst_hop_um=worst)
        rr.setdefault('regs_um',[]).insert(0 if side==0 else len(rr.get('regs_um',[])),best[1]);added+=1
    pts=[rr['from_um']]+rr.get('regs_um',[])+[rr['to_um']]
    worst=max([md(a,b) for a,b in zip(pts,pts[1:])],default=0)
    for side in [0,1]:
        details=next((e for e in row['endpoints'] if e['field']==('launch' if side==0 else 'capture')),{})
        extrema=details.get('pin_group_extremes_um',[])
        adjacent=pts[1] if side==0 else pts[-2]
        worst=max([worst]+[md(p,adjacent) for p in extrema])
    if worst>reach+1e-6:return None,dict(reason='signal endpoint/extreme hop exceeds reach after guards',max_hop_um=worst)
    return rr,dict(guard_added_cycles=added,max_endpoint_hop_um=worst)


def rebind(pd,out,baseline=None,types=None,endpoint_map=None,route=False,reach=405.):
    pd,out=Path(pd),Path(out)
    if out.exists():raise ValueError('refusing to overwrite output')
    if out.resolve()==pd.resolve() or pd.resolve() in out.resolve().parents:raise ValueError('output must be outside input')
    raw=json.loads((pd/'die_plan.json').read_text());resolver=Resolver(pd,raw,baseline);new=copy.deepcopy(raw);emap=endpoint_map or {}
    report=dict(schema='opentallas.station_endpoint_rebind.v1',input=str(pd),baseline=str(baseline) if baseline else None,input_sha256=sha(pd/'die_plan.json'),route=route,rows=[],unresolved=[],route_failures=[],added_cycles=0,changed_stations=0,selected_stations=0,skipped_stations=0,orphan_references=[])
    for tn,t in raw['partition_types'].items():
        if types and tn not in types:continue
        # A baseline narrows changed work; it must not hide legacy references to
        # nonexistent cores. Declared soft anchors may remain unchanged.
        for i,s in enumerate(t.get('internal_stations',[])):
            for field in ['launch','capture']:
                ref=s.get(field,'')
                if ref.startswith('face bus ') or split_ref(ref,t.get('hard_cores',[])):continue
                soft=[c.get('inst','') for c in t.get('contents',[])]
                if any(n and (ref==n or ref.startswith(n+'.') or ref==baseinst(n) or ref.startswith(baseinst(n)+'.')) for n in soft):continue
                report['orphan_references'].append(dict(type=tn,station=i,field=field,reference=ref,reason='reference names neither an actual hard core nor a declared soft anchor/face bus'))
        selected=[];pending=[]
        for i,s in enumerate(t.get('internal_stations',[])):
            if baseline and not any(resolver.affected(tn,s.get(f,'')) or f'{tn}:{i}:{f}' in emap for f in ['launch','capture']):report['skipped_stations']+=1;continue
            report['selected_stations']+=1;ss=copy.deepcopy(s);row=dict(type=tn,station=i,conn=s.get('conn'),old_cycles=len(s.get('regs_um',[])),endpoints=[]);errors=[]
            for side,(field,coord) in enumerate([('launch','from_um'),('capture','to_um')]):
                try:
                    xy,detail=resolver.resolve(tn,s,side,i,emap.get(f'{tn}:{i}:{field}'));ss[coord]=xy;row['endpoints'].append(dict(field=field,old=s[coord],new=xy,**detail))
                except (ValueError,KeyError) as e:errors.append(dict(field=field,ref=s.get(field),reason=str(e)))
            if errors:
                row.update(verdict='FAIL',errors=errors);report['unresolved'].append(dict(type=tn,station=i,errors=errors));report['rows'].append(row);continue
            changed=any(md(ss[k],s[k])>1e-6 for k in ['from_um','to_um']);row['geometry_changed']=changed
            if not changed and not route:row.update(verdict='PASS',new_cycles=row['old_cycles'],added_cycles=0);report['rows'].append(row);continue
            selected.append(ss);pending.append((i,row,s));report['changed_stations']+=int(changed)
        if selected:
            if route:
                trial=copy.deepcopy(t);trial['internal_stations']=selected;fixed,rr=FS.regenerate(trial,reach=reach)
                guardraster=FS.HR.Raster(*t['outline_um'],[FS.HR._core_rect(h) for h in t.get('hard_cores',[])])
                for ss,(i,row,orig),rrr in zip(fixed['internal_stations'],pending,rr['rows']):
                    if rrr['verdict']=='PASS':
                        guarded,gr=guard_endpoint_groups(t,ss,row,reach,guardraster)
                        if guarded is None:
                            row.update(verdict='FAIL',route_reason=gr['reason'],endpoint_reach=gr);report['route_failures'].append(dict(type=tn,station=i,**gr))
                        else:
                            ss=guarded;new['partition_types'][tn]['internal_stations'][i]=ss;row.update(rrr,station=i,verdict='PASS',**gr)
                            row['new_cycles']=len(ss.get('regs_um',[]));row['added_cycles']=row['new_cycles']-row['old_cycles'];report['added_cycles']+=row['added_cycles']
                    else:
                        row.update(verdict='FAIL',route_reason=rrr.get('reason'));report['route_failures'].append(dict(type=tn,station=i,reason=rrr.get('reason')))
                    report['rows'].append(row)
            else:
                for ss,(i,row,orig) in zip(selected,pending):
                    new['partition_types'][tn]['internal_stations'][i]=ss;row.update(verdict='UNROUTED',new_cycles=len(ss.get('regs_um',[])),added_cycles=0);report['rows'].append(row)
    report['verdict']='FAIL' if report['unresolved'] or report['route_failures'] or report['orphan_references'] else ('PASS' if route or not report['changed_stations'] else 'UNROUTED')
    report['scope']='model only; added cycles require compiler/model adoption; no route/signoff authorization'
    shutil.copytree(pd,out,symlinks=False,ignore=shutil.ignore_patterns('gates'))
    text=json.dumps(new,indent=1)+'\n';(out/'die_plan.json').write_text(text)
    sc=out/'die_plan.sha256'
    if sc.exists():sc.write_text(hashlib.sha256(text.encode()).hexdigest()+'  die_plan.json\n')
    report['output_sha256']=sha(out/'die_plan.json');(out/'endpoint_rebind_report.json').write_text(json.dumps(report,indent=1)+'\n')
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan_dir');ap.add_argument('out');ap.add_argument('--baseline');ap.add_argument('--types',help='comma-separated type names');ap.add_argument('--endpoint-map');ap.add_argument('--route',action='store_true');ap.add_argument('--reach',type=float,default=405.);a=ap.parse_args()
    if not 0<a.reach<=405:ap.error('reach must be <=405 um')
    emap=json.loads(Path(a.endpoint_map).read_text()) if a.endpoint_map else None
    r=rebind(a.plan_dir,a.out,a.baseline,set(a.types.split(',')) if a.types else None,emap,a.route,a.reach)
    print(json.dumps({k:v for k,v in r.items() if k not in ['rows','unresolved','route_failures','orphan_references']}));print('UNRESOLVED',len(r['unresolved']),'ROUTE_FAILURES',len(r['route_failures']),'ORPHAN_REFS',len(r['orphan_references']));return 0 if r['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
