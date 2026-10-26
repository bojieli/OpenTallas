#!/usr/bin/env python3
"""Connect landing status bands to reachable existing reset-tree collector taps.

No ring/reset site or mission latency changes. Recompute the static boot
deadline from the actual reverse collector after retargeting the source.
"""
import argparse
import json
from pathlib import Path
from collections import defaultdict


def refresh(table):
    c=table['collector'];fixes=[]
    for tn,info in c['types'].items():
        tree=info.get('tree')
        if not tree or tree.get('hard'):continue
        taps={int(r['q'][7:]):r['xy'] for r in tree['relays'] if r['q'].startswith('rst_n_t')}
        for s in info['local_sources']:
            p=s['xy_um'];old=s['tap']
            dist=lambda i:abs(p[0]-taps[i][0])+abs(p[1]-taps[i][1])
            if dist(old)<=405.+1e-6:continue
            new=min(taps,key=lambda i:(dist(i),i))
            if dist(new)>405.+1e-6:raise ValueError(f'{tn}/{s["name"]}: nearest tap {dist(new)}>405')
            fixes.append(dict(type=tn,source=s['name'],xy_um=p,old_tap=old,old_hop_um=dist(old),new_tap=new,new_hop_um=dist(new),data_cycles_added=0))
            s['tap']=new
    budget=c['boot_budget'];depths={}
    for pn,row in c['parts'].items():
        if not row['active']:continue
        info=c['types'][row['type']];tree=info['tree']
        if tree.get('hard'):depths[pn]=len(tree['relays'])+1;continue
        adj=defaultdict(list)
        for r in tree['relays']:adj[r['q']].append(r['d']);adj[r['d']].append(r['q'])
        d={info['collector_root_node']:0};todo=list(d)
        while todo:
            n=todo.pop()
            for q in adj[n]:
                if q not in d:d[q]=d[n]+1;todo.append(q)
        nodes=[f"rst_n_t{s['tap']}" for s in info['local_sources']]+[x['node'] for x in info['children']]
        depths[pn]=max([d[x]+1 for x in nodes]or[0])
    kids=defaultdict(list)
    for e in c['edges']:kids[e['dst']].append(e)
    deadlines={}
    def deadline(pn):
        if pn not in deadlines:
            deadlines[pn]=max([budget['raw_reset_release_max_cycles']+budget['ring_train_max_cycles']]+[deadline(e['src'])+(21 if e['seam'] else 0) for e in kids[pn]])+depths[pn]
        return deadlines[pn]
    before=budget['ready_at_glue_max_cycles'];budget['local_registered_depths']=depths;budget['ready_at_glue_max_cycles']=deadline(c['root'])
    return dict(fixes=fixes,boot_ready_before=before,boot_ready_after=budget['ready_at_glue_max_cycles'],data_cycles_added=0)


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('table');ap.add_argument('--out',required=True);ap.add_argument('--report',required=True);a=ap.parse_args()
    t=json.loads(Path(a.table).read_text());r=refresh(t);Path(a.out).write_text(json.dumps(t,indent=1)+'\n');Path(a.report).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))


if __name__=='__main__':main()
