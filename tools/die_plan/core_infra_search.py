#!/usr/bin/env python3
"""Model-first core clock driver/width design. Reads only plan/geometry/NLDM.
No measured CTS/GRT/STA timing, pad insertion or post-build sizing is accepted.
Candidate output is a NEW PLAN; it still needs legalization, review and build.
"""
import argparse
import copy
import json
import math
from collections import defaultdict
from pathlib import Path

import core_infra as CI
import core_infra_plan as CP
import die_clock_128 as C128


class Model:
    def __init__(self, sl, libraries, points, caps, r, c, input_slew_ps=40., routing_model=None):
        plan=CI.compile_slice(sl);tree=plan['core_tree'];self.plan=plan
        self.routing_model=routing_model;self.branch=[];self.wire_cap=[]
        self.input_slew_ps=float(input_slew_ps)
        if not math.isfinite(self.input_slew_ps) or self.input_slew_ps < 0:raise ValueError('invalid declared core input slew')
        self.nodes=tree['nodes'];self.n=len(self.nodes);index={n['name']:i for i,n in enumerate(self.nodes)}
        cells={n['name']:n for n in plan['cells']};self.libraries=libraries;self.r=r;self.c=c
        self.parent=[index.get(n['parent'],-1) for n in self.nodes]
        self.xy=[cells[n['name']]['xy_um'] for n in self.nodes]
        self.children=[[] for _ in self.nodes];self.leaves=[[] for _ in self.nodes]
        for i,p in enumerate(self.parent):
            if p>=0:self.children[p].append(i)
        for leaf in tree['leaves']:
            self.leaves[index[leaf['node']]]+=leaf['sinks']
        self.dist=[];self.wire=[];self.sinkcap={c:[] for c in libraries};self.sinkel={c:[] for c in libraries};self.count=[]
        for i in range(self.n):
            x,y=self.xy[i];tg=[self.xy[j] for j in self.children[i]]+[points[q] for q in self.leaves[i]]
            self.wire.append(CP._mst_length([[x,y]]+tg))
            self.dist.append([abs(x-self.xy[j][0])+abs(y-self.xy[j][1]) for j in self.children[i]])
            self.count.append(len(self.leaves[i]))
            for corner in libraries:
                cpin=lambda q:CP.sink_cap(caps[q],corner)
                self.sinkcap[corner].append(sum(cpin(q) for q in self.leaves[i]))
                el=[]
                for q in self.leaves[i]:
                    dx=abs(x-points[q][0])+abs(y-points[q][1]);el.append(dx*r*(dx*c/2+cpin(q)))
                self.sinkel[corner].append((min(el),sum(el)/len(el),max(el)) if el else None)

        if routing_model is not None:
            from core_infra_wire import rooted_rc
            for i in range(self.n):
                target_points=[self.xy[j] for j in self.children[i]]+[points[q] for q in self.leaves[i]]
                profile=routing_model.get('nodes',{}).get(self.nodes[i]['name'])
                if profile is None:profile=routing_model['nonleaf' if self.children[i] else 'leaf']
                rc=rooted_rc([self.xy[i]]+target_points,[0.]*len(target_points),**profile)
                fixed={}
                for corner in libraries:
                    fixed[corner]=[rc['wire_elmore_ps'][k]+sum(rc['pin_elmore_coeff_kohm'][k][len(self.children[i])+q]*CP.sink_cap(caps[sink],corner) for q,sink in enumerate(self.leaves[i])) for k in range(len(target_points))]
                self.branch.append(dict(coeff=[row[:len(self.children[i])] for row in rc['pin_elmore_coeff_kohm']],fixed=fixed))
                self.wire_cap.append(rc['wire_cap_ff'])
        else:self.wire_cap=[wire*c for wire in self.wire]

    def evaluate(self, choices):
        results={}
        for corner,libs in self.libraries.items():
            ar=[0.]*self.n;sr=[self.input_slew_ps]*self.n;mins=[];means=[];maxs=[];weighted=0.;nreg=0;peak=0.
            for i in range(self.n):
                lib=libs[choices[i]]
                load=self.sinkcap[corner][i]+sum(libs[choices[j]]['cap'] for j in self.children[i])
                d=C128._bilin(lib['delay'],sr[i],load+self.wire_cap[i])
                s=C128._bilin(lib['trans'],sr[i],load+self.wire_cap[i])
                peak=max(peak,s)
                if self.routing_model is not None:
                    branch=self.branch[i];childcaps=[libs[choices[j]]['cap'] for j in self.children[i]]
                    el=[fixed+sum(coef*cap for coef,cap in zip(row,childcaps)) for fixed,row in zip(branch['fixed'][corner],branch['coeff'])]
                    child_el=el[:len(self.children[i])];sink_el=el[len(self.children[i]):]
                else:
                    child_el=[dist*self.r*(dist*self.c/2+libs[choices[j]]['cap']) for j,dist in zip(self.children[i],self.dist[i])]
                    sink_el=None
                for j,elmore in zip(self.children[i],child_el):
                    ar[j]=ar[i]+d+elmore;sr[j]=math.hypot(s,2.2*elmore);peak=max(peak,sr[j])
                if self.sinkel[corner][i]:
                    lo,mean,hi=(min(sink_el),sum(sink_el)/len(sink_el),max(sink_el)) if sink_el is not None else self.sinkel[corner][i]
                    mins.append(ar[i]+d+lo);means.append(ar[i]+d+mean);maxs.append(ar[i]+d+hi)
                    weighted+=(ar[i]+d+mean)*self.count[i];nreg+=self.count[i];peak=max(peak,math.hypot(s,2.2*hi))
            results[corner]=dict(mean=weighted/nreg,leaf_min=min(means),leaf_max=max(means),
                leaf_window=max(means)-min(means),all_min=min(mins),all_max=max(maxs),all_window=max(maxs)-min(mins),slew_max=peak)
        return results


def score(res,slew_limit,window=18):
    # Primary: legal slew and local-window structure. Overall insertion can be
    # raised by one designed common entry trunk only after these are satisfied.
    cost=0.
    for corner,r in res.items():
        cost+=30*max(0,r['slew_max']-slew_limit)**2+10*max(0,r['leaf_window']-window)**2
        cost+=2*max(0,r['leaf_max']-({'TT':270,'FF':222.5}[corner]))**2
        cost+=.01*r['leaf_window']**2
    return cost


def design(sl, libraries, points, caps, r, c, slew_limit=80., passes=10, input_slew_ps=40., routing_model=None):
    model=Model(sl,libraries,points,caps,r,c,input_slew_ps,routing_model)
    choices=[n['master'] for n in model.nodes]
    options=list(libraries['TT'])
    baseline=model.evaluate(choices);best=baseline;bestscore=score(best,slew_limit)
    steps=[]
    # Deterministic coordinate minimization from the all-strongest structured
    # tree. Every candidate is computed from geometry and NLDM BEFORE build.
    for turn in range(passes):
        changed=0
        for i in reversed(range(model.n)):
            old=choices[i];pick=old;pickres=best;pickscore=bestscore
            for cell in options:
                if cell==old:continue
                choices[i]=cell;v=model.evaluate(choices);sc=score(v,slew_limit)
                if (sc,options.index(cell)) < (pickscore,options.index(pick)):
                    pick,pickres,pickscore=cell,v,sc
            choices[i]=pick
            if pick!=old:changed+=1;best,bestscore=pickres,pickscore
        steps.append(dict(pass_number=turn+1,changed=changed,score=bestscore,result=best))
        if not changed:break
    out=copy.deepcopy(sl)
    frozen={x['name']:x for x in CI.compile_slice(sl)['cells']}
    out.pop('cell_placements',None)
    for i,n in enumerate(out['core_tree']['nodes']):n['master']=choices[i];n['xy_um']=frozen[n['name']]['xy_um']
    return out,dict(baseline=baseline,result=best,score=bestscore,steps=steps,
                   driver_counts={n:choices.count(n) for n in options if choices.count(n)},slew_limit_ps=slew_limit,input_slew_ps=input_slew_ps,wire_model=('rooted_directional' if routing_model is not None else 'historical_direct'))


def add_entry_chain(sl,n,cell):
    out=copy.deepcopy(sl);out.pop('cell_placements',None)
    tree=out['core_tree'];root=tree['nodes'][0];entry=out['islands'][0]['clock_pin']['xy_um'];rect=out['islands'][0]['rect_um'];nodes=[]
    parent='port:'+tree['clock_port']
    for i in range(n):
        name=f'mp_core_entry{i}'
        nodes.append(dict(name=name,master=cell,xy_um=entry,island_rect_um=rect,parent=parent));parent=name
    root['parent']=parent;tree['nodes']=nodes+tree['nodes']
    return out


def design_entry(sl,libraries,points,caps,r,c,slew_limit=80.,max_stages=6,input_slew_ps=40.,routing_model=None):
    """One identical designed common trunk, selected only from plan/NLDM."""
    best=None;trials=[]
    for count in range(max_stages+1):
        for cell in libraries['TT']:
            if count==0 and cell!=next(iter(libraries['TT'])):continue
            candidate=add_entry_chain(sl,count,cell)
            model=Model(candidate,libraries,points,caps,r,c,input_slew_ps,routing_model)
            res=model.evaluate([n['master'] for n in candidate['core_tree']['nodes']])
            violation=0.;margin=1e9
            for corner,x in res.items():
                low,high={'TT':(230.,270.),'FF':(182.5,222.5)}[corner]
                violation+=max(0.,low-x['leaf_min'])+max(0.,x['leaf_max']-high)+max(0.,x['leaf_window']-20.)+max(0.,x['slew_max']-slew_limit)
                margin=min(margin,x['leaf_min']-low,high-x['leaf_max'],20.-x['leaf_window'],slew_limit-x['slew_max'])
            trial=dict(count=count,cell=cell,result=res,violation_ps=violation,minimum_leaf_margin_ps=margin)
            trials.append(trial);key=(violation,count,-margin,cell)
            if best is None or key<best[0]:best=(key,candidate,trial)
    return best[1],dict(chosen=best[2],trials=trials,input_slew_ps=input_slew_ps,basis='one common fixed trunk designed from geometry and joint TT/FF NLDM; no measured timing')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('--out',required=True);a=ap.parse_args()
    data=json.loads(Path(a.input).read_text());sl=data['slice'];libs=data['libraries'];points=data['points'];caps=data['caps']
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);results=[]
    for width,cf in data.get('profiles',[[1,1.],[2,1.1],[4,1.3],[8,1.6]]):
        r=data['wire_r_kohm_um']/width;c=data['wire_c_ff_um']*cf
        for slew in data.get('slew_limits',[80.]):
            candidate,rep=design(sl,libs,points,caps,r,c,slew,input_slew_ps=data.get('input_slew_ps',40.),routing_model=data.get('routing_model'))
            rep.update(width_multiplier=width,spacing_multiplier=width,capacitance_factor=cf,
                       rc_basis='R/width from fixed sheet resistance; C scaling stated sensitivity, NOT extracted NDR RC')
            label=f'w{width}_c{cf:g}_s{slew:g}'
            (out/(label+'.json')).write_text(json.dumps(rep,indent=1));(out/(label+'_slice.json')).write_text(json.dumps(candidate,indent=1))
            results.append(dict(profile=label,**{k:rep[k] for k in ('result','driver_counts','score')}))
            print(json.dumps(results[-1]),flush=True)
    (out/'summary.json').write_text(json.dumps(results,indent=1))


if __name__=='__main__':main()
