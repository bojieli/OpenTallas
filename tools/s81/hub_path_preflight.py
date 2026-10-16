#!/usr/bin/env python3
"""Diagnostic first-pass hub geometry audit; never emits RTL, LEF, or route products.

Use the exact generator and its actual first-pass end/relay placement. Catch
independent hub-lane placement failures to enumerate all requested hub interfaces.
Stop at the relay-progress hook, before finalize/emit. This diagnostic continuation
is not a usable die model: failed chains have dangling partial stations. Missing
later-hop repair, final pin/footprint placement and global routing stay explicit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def merge_intervals(intervals):
    out=[]
    for a,b in sorted(intervals):
        if b <= a:
            continue
        if out and a <= out[-1][1]+1e-6:
            out[-1][1]=max(out[-1][1],b)
        else:
            out.append([a,b])
    return out


def audit(path, allowed, boxes):
    """All orthogonal segment/macro crossings and >20um station-region gaps."""
    crosses=[];gaps=[]
    for k,(p,q) in enumerate(zip(path,path[1:])):
        if abs(p[0]-q[0])<1e-6:
            axis=1;fixed=p[0]
        elif abs(p[1]-q[1])<1e-6:
            axis=0;fixed=p[1]
        else:
            crosses.append(dict(segment=k,reason='NON_ORTHOGONAL',p=p,q=q))
            continue
        lo,hi=sorted((p[axis],q[axis]))
        if hi-lo<.001:
            continue
        for name,x,y,w,h in boxes:
            r=[x,y,x+w,y+h]
            if not r[1-axis]+.001<fixed<r[3-axis]-.001:
                continue
            a,b=max(lo,r[axis]),min(hi,r[axis+2])
            if b-a>.001:
                crosses.append(dict(segment=k,macro=name,inside_um=round(b-a,3)))
        if allowed is None:
            continue # a direct within-budget connection has no station search
        intervals=[]
        for r in allowed:
            if r[1-axis]-1e-6<=fixed<=r[3-axis]+1e-6:
                intervals.append((max(lo,r[axis]),min(hi,r[axis+2])))
        cur=lo
        for a,b in merge_intervals(intervals):
            if a-cur>20:
                gaps.append(dict(segment=k,lo=round(cur,3),hi=round(a,3),length_um=round(a-cur,3)))
            cur=max(cur,b)
        if hi-cur>20:
            gaps.append(dict(segment=k,lo=round(cur,3),hi=round(hi,3),length_um=round(hi-cur,3)))
    return dict(macro_crossings=crosses,station_region_gaps=gaps)


class Collected(Exception):
    def __init__(self,model):
        self.model=model


def run(root,recipe,out):
    os.chdir(root) # match the ordinary die chain's source-root working directory
    sys.path.insert(0,str(root/'tools'))
    import dsrom_s81_fulldie as G
    options=G.die_options(argparse.ArgumentParser()).parse_args(shlex.split(recipe.read_text()))
    G.apply_options(options)
    # Explicit diagnostic first pass: do not invoke iterative finalized hop repair.
    G.HOP_FIX=False
    G.HOP_PLAN={}
    G.ALIGN_EXT[0]=False
    G.RELAY_PROGRESS=True
    calls=[];failures=[];requests={};fatal=None;model=None
    original_hub=G._hub_bus_chain;original_run=G.Chains.run;original_stop=G._relay_progress_fix
    def chain(self,name,lanes,path,allowed,start,*a,**kw):
        if name.startswith('hb_'):
            requests[name]=dict(path=[list(p) for p in path],allowed=[list(r) for r in allowed],lanes=list(lanes))
        return original_run(self,name,lanes,path,allowed,start,*a,**kw)
    def hub(*a,**kw):
        saved=sys.getprofile();record=dict(name=f'hb_{a[3]}_{a[6]}_{a[4]}',path=[],bits=a[5],
            source=a[0]['hub'][a[3]].name,target=a[0]['hub'][a[4]].name,source_key=a[3],target_key=a[4],
            source_port=a[6],target_port=a[7],route_built=False)
        def profile(frame,event,arg):
            if frame.f_code is original_hub.__code__ and event=='return':
                loc=frame.f_locals
                if 'path' in loc:
                    record.update(name=loc.get('name',loc.get('hbn')),path=[list(p) for p in loc['path']],bits=loc.get('bits'),
                                  source=loc['A'].name,target=loc['Bk'].name,source_key=loc['a_'],target_key=loc['b_'],route_built=True)
        sys.setprofile(profile)
        try:
            original_hub(*a,**kw)
        except (RuntimeError,AssertionError) as error:
            failures.append(dict(source=a[3],target=a[4],port=a[6],error=str(error)))
        finally:
            sys.setprofile(saved)
            calls.append(record)
    def stop(m,P):
        raise Collected(m)
    G._hub_bus_chain=hub;G.Chains.run=chain;G._relay_progress_fix=stop
    try:
        G.build()
        fatal='Diagnostic stop hook not reached; refuse incomplete enumeration'
    except Collected as done:
        model=done.model
    except Exception as error:
        fatal=type(error).__name__+': '+str(error)
    finally:
        G._hub_bus_chain=original_hub;G.Chains.run=original_run;G._relay_progress_fix=original_stop
    rows=[];boxes=[]
    if model is not None:
        # Relay stations are intentionally not obstacles to their own wire path.
        # End blocks and all actual functional macros, including field leaves,
        # remain blockers, with no source/receiver blanket exemption.
        boxes=[(i.name,i.x,i.y,i.w,i.h) for i in model['insts'] if i.kind not in ('stn','hstn','rly')]
        for call in calls:
            req=requests.get(call['name'])
            row=dict(call)
            row.update(audit(call['path'],req['allowed'] if req else None,boxes))
            row['placement_failed']=any(f['source']==call['source_key'] and f['target']==call['target_key']
                                        and f['port']==call['source_port'] for f in failures)
            rows.append(row)
    bad=[r for r in rows if r['macro_crossings'] or r['station_region_gaps'] or r['placement_failed'] or not r['route_built']]
    result=dict(schema='opentallas.s81.hub-path-preflight.v1',scope='DIAGNOSTIC_FIRST_PASS_ONLY_NO_USABLE_DIE_MODEL',
        source_commit=(root/'SOURCE_SHA').read_text().strip() if (root/'SOURCE_SHA').exists() else None,
        generator_sha256=sha(root/'tools/dsrom_s81_fulldie.py'),driver_sha256=sha(__file__),recipe_sha256=sha(recipe),working_directory=str(Path.cwd()),
        complete_hub_request_enumeration=model is not None,fatal=fatal,verdict='FAIL' if fatal or failures or bad else 'PREFLIGHT_PASS_NOT_PHYSICAL',
        requests=len(rows),problem_requests=len(bad),station_placement_failures=failures,paths=rows,
        obstacle_rectangles=[dict(name=n,origin_um=[x,y],outline_um=[w,h]) for n,x,y,w,h in boxes],
        remaining=['Hop repair and final pin/footprint placement not evaluated','Partial failed stations retained only as conservative diagnostic occupancy; no RTL/LEF emitted','Clock/PG/cut/native/STA qualification not established'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k] for k in ('verdict','complete_hub_request_enumeration','requests','problem_requests','fatal')}))
    return 2 if result['verdict']=='FAIL' else 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    return run(a.root.resolve(),a.recipe.resolve(),a.out.resolve())

if __name__=='__main__':
    raise SystemExit(main())
