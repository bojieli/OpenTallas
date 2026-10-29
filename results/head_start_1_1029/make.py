#!/usr/bin/env python3
"""HEAD-START-1: gate census + PLANNED absolute START offsets for the leaf START form.

Inputs (read-only, Codex leaf form): leaf CA plan (leaf_plan4.json), emitted
provider start_stages.json (final5, local raw-wavefront resets), final5
physical.json (capture-pin sites), reset_start_offsets_rx_tx.json.
start_offset(part) = root local raw release + root SETTLE + origin_cycles(leaf).
J is the planner's nominal from the pre-legalization clock proof: PLANNED, not
qualified until a fresh routed phase re-plan reproduces the same stage set.
"""
import argparse,hashlib,json
from pathlib import Path
man=lambda a,b:sum(abs(x-y) for x,y in zip(a,b))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser(description=__doc__)
    for k in ('plan','stages','physical','offsets'):a.add_argument(k)
    a.add_argument('--out',required=True);a=a.parse_args()
    P=json.load(open(a.plan));R={g['region']:g for g in P['regions']}
    st=json.load(open(a.stages));ph=json.load(open(a.physical))['ports'];rso=json.load(open(a.offsets))
    S={s['region']:s for s in st['stages']};I={s['id']:s for s in st['stages']}
    root=next(s for s in st['stages'] if s['root'])
    # 1) structural match provider <-> plan (cycle count matches plan)
    mism=[s['id'] for s in st['stages'] if not s['root'] and (R[s['region']]['start_from']['parent']!=s['parent']
          or R[s['region']]['start_from']['rtl']['PAD']!=s['pad'] or bool(R[s['region']]['start_from']['rtl']['EDGE_FALL'])!=s['edge_fall'])]
    mism+=[o['dst_part'] for o in st['die_outputs'] if R[o['dst_region']]['start_from']['parent']!=I[o['stage']]['region']]
    # 2) hops
    span=[(round(man(s['clock_pin_xy_um'],S[s['parent']]['clock_pin_xy_um']),3),s['id']) for s in st['stages'] if s['parent']]
    leaf=[(round(man(ph[o['net']]['xy_um'],I[o['stage']]['clock_pin_xy_um']),3),o['dst_part']) for o in st['die_outputs']]
    rst=[(s['reset_hop_um'],s['id']) for s in st['stages']]
    # 3) planned offsets
    base=root['reset_source']['raw_release']+root['settle'];outs={o['dst_part']:o for o in st['die_outputs']}
    parts={}
    for pn,v in sorted(rso['parts'].items()):
        o=outs.get(pn);oc=R[o['dst_region']]['origin_cycles'] if o else None
        parts[pn]=dict(type=v['type'],reset_release=v['reset_release'],origin_cycles=oc,
            start_offset=None if o is None else base+oc,start_minus_reset=None if o is None else base+oc-v['reset_release'])
    stage_slack=min(base+R[s['region']]['origin_cycles']-s['reset_source']['raw_release'] for s in st['stages'] if not s['root'])
    jdev=sum(1 for g in P['regions'] if g['start_from'] and g['start_from'].get('J_dev') not in (None,[0,0]))
    so=[v['start_offset'] for v in parts.values() if v['start_offset'] is not None]
    summ=dict(stages=len(st['stages']),flops=st['counts']['flops'],leaf_outputs=len(st['die_outputs']),plan_regions=len(R),
        plan_edges_clean=P['summary']['tree_edges_clean'],plan_edges=P['summary']['tree_edges'],J_dev_nonzero=jdev,
        provider_plan_mismatches=len(mism),
        stage_parent_span=dict(n=len(span),max=max(span),over405=sum(x[0]>405 for x in span)),
        stage_to_capture_pin=dict(n=len(leaf),max=max(leaf),over405=sum(x[0]>405 for x in leaf)),
        reset_source_hop=dict(n=len(rst),max=max(rst),over405=sum(x[0]>405 for x in rst)),
        root=dict(stage=root['id'],raw_release=root['reset_source']['raw_release'],settle=root['settle'],origin_cycle0=base),
        start_offsets=dict(parts=len(parts),null=sum(v['start_offset'] is None for v in parts.values()),min=min(so),max=max(so)),
        min_part_start_minus_reset=min(v['start_minus_reset'] for v in parts.values() if v['start_minus_reset'] is not None),
        min_stage_start_minus_reset=stage_slack)
    doc=dict(schema='head_start_planned_offsets/1',
        authority='PLANNED: leaf CA plan J nominal on pre-legalization clock proof; local raw reset relay phase NOT RUN; requires fresh routed phase re-plan (--start-prev fixed point) before compiler adoption',
        formula='start_offset = root_raw_release + root_SETTLE + origin_cycles(leaf part)',
        inputs={k:dict(path=str(getattr(a,k)),sha256=sha(getattr(a,k))) for k in ('plan','stages','physical','offsets')},
        summary=summ,parts=parts)
    Path(a.out).write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps(summ))
if __name__=='__main__':main()
