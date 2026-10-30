"""Deterministic joint TT/FF native flat-forest driver sizing before build.

Run substantial searches under ot-run. Only native geometry, pin capacitances,
clock RC and Liberty are inputs. No measured timing or per-path pad insertion.
"""
import argparse
import copy
import gzip
import json
import math
import re
from collections import Counter
from pathlib import Path
import die_clock_128 as LIB
import core_infra_plan as RC
import flat_clock_plan as PLAN
from flat_clock_forest import ENV


def size(candidate, libdir, passes=4, geometry_path=None, sdc_path=None):
    if candidate.get('input_slew_ps',0)<80 or candidate.get('wire_rc',{}).get('r_kohm_um')!=PLAN.R or candidate.get('wire_rc',{}).get('c_ff_um')!=PLAN.C:
        raise ValueError('regenerate candidate with explicit80ps input slew and native clock RC')
    out=copy.deepcopy(candidate);inv,pairs=PLAN.actual_relations(out,geometry_path,sdc_path);out['inventory']=inv;nodes=out['nodes'];roots=out['root_nodes'];options=sorted(ENV)
    PLAN.validate_topology(inv,nodes,roots,out['groups'])
    libraries={c:PLAN.buffer_models(c,libdir,options) for c in ('TT','FF')};caps={};edges={}
    import die_sta_related as CAL
    factors={corner:{m:CAL.cell_cal_factors(corner,[m]) for m in options} for corner in libraries}
    for corner in libraries:
        caps[corner],masters=PLAN.clock_caps(inv,libdir,corner);edges[corner]={q:masters[c['master']] for q,c in inv['cells'].items() if c['kind']=='S'}
    wires=[];distances=[]
    for n in nodes:
        points=[nodes[k]['xy'] for k in n['children']]+[inv['cells'][q]['xy'] for q in n['sinks']]
        wires.append(RC._mst_length([n['xy']]+points));distances.append([sum(abs(a-b) for a,b in zip(n['xy'],p)) for p in points])
    choices=[n['master'] for n in nodes];feed_cache={}
    def evaluate(root):
        result={}
        for corner,models in libraries.items():
            waves={};slew_max=0.
            for state in ('rise_late','rise_early','fall_late','fall_early'):
                libs={m:v[state] for m,v in models.items()};entry=roots[root];key=(root,corner,state,choices[entry])
                if key not in feed_cache:feed_cache[key]=PLAN.root_feed(inv,nodes,root,entry,libs[choices[entry]]['cap'],out['input_slew_ps'])
                feed,slew,_=feed_cache[key];todo=[(entry,feed,feed,slew)];arr={};cal={}
                while todo:
                    i,arrival,calarr,slew=todo.pop();n=nodes[i];lib=libs[choices[i]];factor=factors[corner][choices[i]][state]
                    targets=[(k,libs[choices[k]]['cap'],True) for k in n['children']]+[(q,caps[corner][state][q],False) for q in n['sinks']]
                    load=wires[i]*PLAN.C+sum(t[1] for t in targets)
                    delay=LIB._bilin(lib['delay'],slew,load);transition=LIB._bilin(lib['trans'],slew,load)
                    for (q,cap,child),distance in zip(targets,distances[i]):
                        elmore=distance*PLAN.R*(distance*PLAN.C/2+cap);a=arrival+delay+elmore;ca=calarr+delay*factor+elmore;tr=math.hypot(transition,2.2*elmore);slew_max=max(slew_max,tr)
                        if child:todo.append((q,a,ca,tr))
                        else:arr[q]=a;cal[q]=ca
                waves[state]=(arr,cal)
            ids=list(waves['rise_late'][0]);values=[waves[edges[corner][q]+'_late'][0][q] for q in ids]
            windows={case:max(waves[edges[corner][q]+'_'+case][1][q] for q in ids)-min(waves[edges[corner][q]+'_'+case][1][q] for q in ids) for case in ('late','early')}
            result[corner]=dict(min_ps=min(values),max_ps=max(values),mean_ps=sum(values)/len(values),raw_window_ps=max(values)-min(values),calibrated_windows_ps=windows,window_ps=max(windows.values()),slew_max_ps=slew_max)
        return result
    def score(metrics):
        if any(m['slew_max_ps']>80 for m in metrics.values()):return (float('inf'),)*2
        windows=[m['window_ps'] for m in metrics.values()]
        return max(windows),sum(windows)
    records={}
    for root,index in roots.items():
        ids=[];todo=[index]
        while todo:
            i=todo.pop();ids.append(i);todo+=nodes[i]['children']
        baseline=evaluate(root);best=baseline;cost=score(best);steps=[]
        if math.isinf(cost[0]):raise ValueError(f'{root}: initial geometry/strongest-driver slew FAIL; revise structure')
        for turn in range(passes):
            changed=0
            for i in ids[::-1]:
                old=choices[i];pick=old;result=best;newcost=cost
                for option in options:
                    if option==old:continue
                    choices[i]=option;m=evaluate(root);s=score(m)
                    if s<newcost:pick=option;result=m;newcost=s
                choices[i]=pick
                if pick!=old:best=result;cost=newcost;changed+=1
            steps.append(dict(pass_number=turn+1,changed=changed,metrics=best))
            if not changed:break
        records[root]=dict(baseline=baseline,result=best,steps=steps)
        print('FLAT_CLOCK_SIZE',root,json.dumps(best),flush=True)
    for node,master in zip(nodes,choices):node['master']=master
    metrics=PLAN.model(inv,nodes,roots,libdir,out['input_slew_ps'])
    out['model']=metrics;out['related_pair_model']=PLAN.related_pair_bounds(inv,nodes,out['groups'],metrics,pairs)
    out['sizing']=dict(basis='geometry-only joint TT/FF R9 BUF8..24 envelope; hard80ps slew; strict max/sum window objective; latency band INFO',roots=records,masters=dict(Counter(choices)))
    out['build_allowed']=False;out['verdict']='UNQUALIFIED_UNTIL_LEGAL_SITE_AND_SUCCESSOR_G1_REVIEW'
    return out


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('candidate',type=Path);a.add_argument('--libdir',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--geometry',type=Path);a.add_argument('--native-sdc',type=Path);a.add_argument('--passes',type=int,default=4);args=a.parse_args()
    if args.out.exists():raise FileExistsError('preserve previous verdict; choose new output')
    with gzip.open(args.candidate,'rt') as f:candidate=json.load(f)
    result=size(candidate,args.libdir,args.passes,args.geometry,args.native_sdc)
    with gzip.open(args.out,'wt') as f:json.dump(result,f)

if __name__=='__main__':main()
