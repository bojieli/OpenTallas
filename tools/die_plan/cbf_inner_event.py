#!/usr/bin/env python3
"""QC CBF corridor event: coherent INNER fixed-prefix floor, before physical kit generation.

The existing bind remains authoritative for old timing. A fixed-common floor applies to the entire selected
n_b edge in EVERY instance of cbf_q01/cbf_q01_s2; companion reduction inputs and downstream reductions receive
only the pad needed to retain their already-coherent old relative timing. Optional count spans are not edited.
Output is a new land_r8_extra table, consumed by Binder._apply_inner/inner_strap_sites. Never edits RTL.
A non-aligned/stale seed is rejected; this adapter does not conceal a failing strict bind.
"""
import argparse, copy, json, re
from collections import defaultdict
from pathlib import Path

TYPES = ('cbf_q01', 'cbf_q01_s2')
TARGET = '.u_t_0_2'
SOURCE = '.u_t_1_2'
FIXED_FLOOR = 4


def coherent_pads(edges, floors):
    """edges[(sink, input)] = {src, src_port, delta}; floor is an extra stage on a named old edge.
    Return added pads and output timing increments. Old reduction inputs must already be aligned.
    """
    by = defaultdict(dict)
    for (leaf, port), e in edges.items(): by[leaf][port] = e
    for (leaf,port),extra in floors.items():
        if not {'n_a','n_b'} <= by[leaf].keys():raise ValueError('floor requires complete paired node: '+leaf)
        if not isinstance(extra,int) or extra<0:raise ValueError('floor must be nonnegative integer stages')
    memo, active, pads, bad = {}, set(), {}, []
    def sig(leaf, port):
        key = leaf, port
        if key in memo: return memo[key]
        if key in active: raise ValueError('combinational timing cycle: '+str(key))
        if leaf not in by: return (0, 0)
        active.add(key); ins = by[leaf]
        if re.search(r'\.u_t_\d_\d$', leaf):
            selected = ['tap'] if port == 't_out' else ['n_a', 'n_b']
        else: selected = list(ins)
        vals = {}
        for pn in selected:
            if pn not in ins: continue
            e = ins[pn]; old, new = sig(e['src'], e['src_port']); old += e['delta']; new += e['delta']
            vals[pn] = old, new, int(floors.get((leaf,pn),0))
        if vals:
            old = max(v[0] for v in vals.values())
            new = max(v[1]+v[2] for v in vals.values())
            if re.search(r'\.u_t_\d_\d$',leaf) and port != 't_out' and {'n_a','n_b'} <= vals.keys():
                if vals['n_a'][0] != vals['n_b'][0]:
                    bad.append(dict(node=leaf,old_arrivals={k:v[0] for k,v in vals.items()}))
                for pn, (_old, before, forced) in vals.items():
                    pad = new-before
                    if pad < forced: raise AssertionError('floor lost')
                    if pad: pads[(leaf,pn)] = pad
            ans = old,new
        else: ans = 0,0
        active.remove(key);memo[key]=ans;return ans
    for leaf in sorted(by):
        if re.search(r'\.u_t_\d_\d$',leaf) and {'n_a','n_b'} <= by[leaf].keys():sig(leaf,'n_y')
    if bad: raise ValueError('seed reduction timing is not coherent: '+json.dumps(bad[:12]))
    return pads,{k:n-o for k,(o,n) in memo.items()}


def generate(plan, bdir, r8_path, extra_path):
    raw=json.loads(Path(plan).read_text());bd=Path(bdir)
    seed_report=json.loads((bd/'bind_report.json').read_text())
    if seed_report.get('errors') or seed_report.get('n_errors',0):
        raise ValueError('requires clean strict seed bind before coherent CBF event; errors='+str(seed_report.get('n_errors',len(seed_report.get('errors',[])))))
    bg=json.loads((bd/'bus_groups.json').read_text());sinks=json.loads((bd/'bind_sinks.json').read_text())
    names=json.loads((bd/'bind_names.json').read_text());part_of={leaf:k.split('.',1)[0] for k,leaf in names.items()}
    ptypes={p['name']:p['type'] for p in raw['partitions']}
    r8=json.loads(Path(r8_path).read_text());extra=json.loads(Path(extra_path).read_text())
    member={}
    for m in r8['members']+extra['members']:
        src=m['source'];src_leaf=src.rsplit('.',1)[0] if not m['id'].startswith('INNER:') else src
        member[(m['sink'],m['sink_port'],src_leaf)] = copy.deepcopy(m)
    orig={};member_for={}
    for g in bg['landing']:
        for m in g['members']:
            for a,b in m['sink_bits']:
                for bit in range(a,b+1):orig[(g['sink'],m['sink_port'],bit)]=m['asbuilt_stages']
    for m in bg['internal']:
        for a,b in m['sink_bits']:
            for bit in range(a,b+1):orig[(m['sink'],m['sink_port'],bit)]=m['asbuilt_stages']
    per=defaultdict(list)
    for k,v in sinks.items():
        if not k.startswith('c16_') or v[0]!='pin' or '.tie' in str(v[1]):continue
        lp,bi=k.rsplit('[',1);leaf,pn=lp.rsplit('.',1);bit=int(bi[:-1])
        if pn in ('tile_id','rst_n','sidx'):continue
        sl,sp=v[1].rsplit('[',1)[0].rsplit('.',1);depth=int(v[2]);a=int(orig.get((leaf,pn,bit),depth))
        per[(leaf,pn)].append(dict(src=sl,src_port=sp,depth=depth,asbuilt=a,delta=depth-a,bit=bit))
    edges={}
    for key,vs in per.items():
        sig={(v['src'],v['src_port'],v['delta'],v['depth'],v['asbuilt']) for v in vs}
        if len(sig)!=1:raise ValueError('mixed timing/source bits in '+str(key))
        edges[key]=vs[0]
    targets={};bytype=defaultdict(list)
    for (leaf,pn),e in edges.items():
        pt=part_of.get(leaf)
        if pn=='n_b' and leaf.endswith(TARGET) and ptypes.get(pt) in TYPES:
            if {x['bit'] for x in per[(leaf,pn)]} != set(range(514)):raise ValueError('target bank must carry all514bits: '+leaf)
            if not e['src'].endswith(SOURCE) or e['src_port']!='t_out':raise ValueError('target source changed: '+leaf)
            bytype[ptypes[pt]].append((leaf,pn,e))
    for tn in TYPES:
        rows=bytype[tn]
        if not rows:raise ValueError('missing target type '+tn)
        mn=min(e['depth'] for _,_,e in rows);mx=max(e['depth'] for _,_,e in rows)
        if mx-mn!=1:raise ValueError(f'{tn}: expected optional span1, got {mn}..{mx}')
        for leaf,pn,e in rows:targets[(leaf,pn)]=max(0,FIXED_FLOOR-mn)
    pads,timing=coherent_pads(edges,targets)
    updated={m['id']:copy.deepcopy(m) for m in extra['members']};ledger=[]
    for (leaf,pn),add in sorted(pads.items()):
        e=edges[(leaf,pn)];pt=part_of.get(leaf);srcpt=part_of.get(e['src']);old=member.get((leaf,pn,e['src']))
        if old is not None:
            if int(old['landed'])!=e['depth']:raise ValueError('stale seed table for '+old['id'])
            m=copy.deepcopy(old)
        elif srcpt==pt and pt is not None:
            a=e['asbuilt'];m=dict(id=f"INNER:{pt}:{leaf}.{pn}<-{e['src']}@{a}",sink=leaf,sink_part=pt,src_part=pt,
              sink_port=pn,sink_bits=[],source=e['src'],asbuilt=a,bound=a,pad=e['depth']-a,landed=e['depth'],lane=None)
        else:raise ValueError('missing crossing member for '+str((leaf,pn)))
        m['pad']=int(m['pad'])+add;m['landed']=int(m['landed'])+add;m['tree_align']=int(m.get('tree_align',0))+add
        m['why']=str(m.get('why',''))+' | CBF fixed-prefix floor and coherent reduction propagation'
        updated[m['id']]=m;ledger.append(dict(sink=leaf,port=pn,part=pt,type=ptypes.get(pt),added_cycles=add,
            old_depth=e['depth'],new_depth=e['depth']+add,bits=len(per[(leaf,pn)]),forced_floor=targets.get((leaf,pn),0)))
    out=copy.deepcopy(extra);out['members']=list(updated.values());out['note']=str(out.get('note',''))+'\nCBF corridor event: fixed prefix floor4; coherent n_a/n_b and downstream tree pads.'
    out['summary']=dict(extra.get('summary',{}),members=len(out['members']),inner=sum(m['id'].startswith('INNER:') for m in out['members']),
        pad_flops=sum(int(m.get('tree_align',0))*(sum(b-a+1 for a,b in m.get('sink_bits',[])) or len(per.get((m['sink'],m['sink_port']),[]))) for m in out['members']))
    out['cbf_corridor_event']=dict(fixed_floor=FIXED_FLOOR,types=list(TYPES),source_bind=str(bd),adopted=False)
    report=dict(status='CANDIDATE_REQUIRES_STRICT_BIND_MODEL_AND_PLACE',fixed_floor=FIXED_FLOOR,
        types={t:dict(instances=len(v),old_min=min(e['depth'] for _,_,e in v),old_max=max(e['depth'] for _,_,e in v))for t,v in bytype.items()},
        members_changed=len(ledger),added_stage_bits=sum(x['added_cycles']*x['bits'] for x in ledger),
        max_added_output_cycles=max(timing.values(),default=0),ledger=ledger,
        obligations=['strict bind and unchanged count spans on target site','lane_asbuilt/INNER ledger','compiler/model price','RTL lockstep+mutants','plan render and PLACE pilot'])
    return out,report


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('bind_dir');a.add_argument('r8_table');a.add_argument('cb16_table');a.add_argument('out');a.add_argument('--report',required=True);x=a.parse_args()
    for p in [x.out,x.report]:
        if Path(p).exists():raise SystemExit('refuse existing output '+p)
    try:out,rep=generate(x.plan,x.bind_dir,x.r8_table,x.cb16_table)
    except ValueError as e:
        Path(x.report).write_text(json.dumps(dict(status='BLOCKED_SEED_BIND',error=str(e)),indent=1)+'\n');raise SystemExit(str(e))
    Path(x.out).write_text(json.dumps(out,indent=1)+'\n');Path(x.report).write_text(json.dumps(rep,indent=1)+'\n')
    print(json.dumps({k:v for k,v in rep.items()if k!='ledger'}))
if __name__=='__main__':main()
