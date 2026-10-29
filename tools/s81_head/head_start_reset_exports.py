#!/usr/bin/env python3
"""Site START reset feeds on actual existing registered raw wavefront relays.

This emits proposed type-uniform aliases of real raw-Q nets, never raw die reset
or mission-gated taps. No extra root synchronizer, reset stage, or timing waiver
is introduced. The reset crossing still needs actual STA/phase qualification.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import schema as S
import reset_tree as R


def plan_exports(plan,offsets,stages,max_hop=405):
    candidates=[]
    for pn,p in sorted(plan.parts.items()):
        tn=p['type']
        if plan.types[tn].get('hard'):continue
        t=R.for_type(plan,tn)
        raw=R.start_relays(t) if t.get('start') else t['relays']
        for relay in raw:
            if t.get('start') and relay['role'] not in ('raw','boot','bootstrap_transport'):continue
            xy=plan.to_die(pn,relay['xy'])
            release=offsets['parts'][pn]['release']-R.release_clocks(t)+R.entry_stages(t)+relay['depth']
            candidates.append(dict(part=pn,type=tn,instance=relay['name'],net=relay['q'],
                xy_um=list(xy),local_xy_um=list(relay['xy']),raw_release=release))
    selected=[];uses={};failed=[]
    for stage in stages['stages']:
        xy=stage['clock_pin_xy_um']
        distance=lambda c:sum(abs(a-b) for a,b in zip(xy,c['xy_um']))
        c=min(candidates,key=lambda q:(distance(q),q['part'],q['net']))
        d=distance(c);key=(c['type'],c['instance'],c['net'])
        uses[key]=c
        row=dict(stage=stage['id'],stage_region=stage['region'],clock_node=stage['node_cell'],
            stage_xy_um=xy,source=dict(c),hop_um=round(d,4),qualified=False,
            phase_status='NOT RUN: raw reset crossing actual TT/FF capture and shared phase model required')
        selected.append(row)
        if d>max_hop:failed.append(stage['id'])
    aliases={};types={}
    for tn in sorted({k[0] for k in uses}):
        for n,key in enumerate(sorted(k for k in uses if k[0]==tn)):
            c=uses[key];port=f'rst_start_raw_{n}'
            aliases[key]=port
            types.setdefault(tn,[]).append(dict(port=port,instance=c['instance'],net=c['net'],xy_um=c['local_xy_um']))
    for row in selected:
        c=row['source'];c['port']=aliases[(c['type'],c['instance'],c['net'])]
    root=next(r for r in selected if r['stage']==next(s['id'] for s in stages['stages'] if s['root']))
    relative=max(r['source']['raw_release']-root['source']['raw_release'] for r in selected)
    return dict(schema='ot_head_start_reset_exports/1',reset_form='local_wavefront_PROPOSED',
        sources='actual existing registered raw reset relays; no raw-die input',
        types=types,stages=selected,
        summary=dict(stages=len(selected),type_aliases=sum(map(len,types.values())),
            max_hop_um=max(r['hop_um'] for r in selected),over_hop=failed,
            root_raw_release=root['source']['raw_release'],max_relative_raw_release=relative,
            settle_status='NOT QUALIFIED: add actual crossing/phase and stage reset-to-start guard'),
        added_reset_cycles=0,actual_START_offsets=None)


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('offsets');a.add_argument('stages');a.add_argument('--out',required=True);a=a.parse_args()
    p=S.Plan(S.load(a.plan),Path(a.plan));o=plan_exports(p,json.load(open(a.offsets)),json.load(open(a.stages)))
    Path(a.out).write_text(json.dumps(o,indent=1)+'\n');print(json.dumps(o['summary']))
if __name__=='__main__':main()
