#!/usr/bin/env python3
"""Current-shape queue replay over retained actual leaves, no arithmetic/build.
Reuses original queue/tag recurrences; reports calibration equality separately
from a source internal occupancy certificate. No claim for unenrolled programs.
"""
import collections,gzip,json,hashlib,io
from pathlib import Path
import model_dsrom_issue_return_calendar as C
import uarch_model_dsrom_field_bridge as B
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_field_bridge_parent_20261003'
ACTUAL=OUT/'inputs/I66_actual_r2.jsonl.gz'
ASSIGN=ROOT/'results/uarch/dsrom_owner_provider_first_20261002/r1/assignments.jsonl.gz'

def rows(path):
    with gzip.open(path,'rt') as f:
        for line in f:yield json.loads(line)

def unpack(raw):return ((raw>>29)&7,(raw>>13)&65535,(raw>>8)&31,(raw>>5)&7,raw&31)

def replay(leaves,np=4096,R=128):
    NL=2*np;LS=(NL//R).bit_length()-1
    levels=[[C.ReturnNode() for _ in range(NL>>(l+1))] for l in range(LS)]
    roots=[C.ReturnRoot() for _ in range(R)];events=collections.defaultdict(dict)
    for t,leaf,tag in leaves:
        bucket=events[t+1].setdefault((0,leaf//2),{})
        if leaf%2 in bucket:raise ValueError('same leaf/edge duplicate')
        bucket[leaf%2]=(tag,('actual_leaf',t,leaf,tag))
    active=set();ra=set();t=0
    while events or active or ra:
        incoming=events.pop(t,{})
        for l,g in incoming:
            if l==LS:ra.add(g)
            else:active.add((l,g))
        for l,g in sorted(active):
            out=levels[l][g].step(t,incoming.get((l,g),{}))
            if out:
                at,v=out;key=(l+1,g//2) if l+1<LS else (LS,g)
                side=g%2 if l+1<LS else 0
                bucket=events[at+1].setdefault(key,{})
                if side in bucket:raise ValueError('registered output collision')
                bucket[side]=v
        active={k for k in active if any(levels[k[0]][k[1]].q)}
        for g in sorted(ra):roots[g].step(t,incoming.get((LS,g),{}).get(0))
        ra={g for g in ra if roots[g].q or roots[g].results}
        t+=1
    predicted=sorted((at,g,tag[1]) for g,r in enumerate(roots) for at,tag,expr in r.rows)
    return predicted,{'levels':LS,'nodes':sum(map(len,levels)),'root_count':R,
        'peak_node_queues_per_level':[max(max(n.peak) for n in level) for level in levels],
        'node_faults':[(l,g,n.faults) for l,level in enumerate(levels) for g,n in enumerate(level) if n.faults],
        'root_faults':[(g,r.faults) for g,r in enumerate(roots) if r.faults],
        'peak_root_input':max(r.peakq for r in roots),'peak_root_held':max(r.peakbuf for r in roots),
        'all_queue_and_held_debt_drained':not events and not active and not ra and not any(r.buf for r in roots),
        'predicted_retired_rows':len(predicted),'calendar_terminal':t}

def actual_certificate():
    leaves=[];observed=[];counts=collections.Counter();writer={};visible={};origin=None
    for x in rows(ACTUAL):
        identity=(x['stage'],x['rank'],x['phase'],x['key_word'],x['reset_era'])
        if origin is None:origin=identity
        if identity!=origin:raise ValueError('mixed accepted phase/reset')
        counts[x['kind']]+=1
        if x['kind']=='pair_partial':leaves.append((x['edge'],2*x['a']+x['b'],unpack(x['c'])))
        if x['kind']=='root_row_accept':observed.append((x['edge'],x['a'],x['b']))
        if x['kind']=='VM_write_accept':
            if x['b'] in writer:raise ValueError('duplicate writer address')
            writer[x['b']]=(x['edge'],x['c'])
        if x['kind']=='final_destination_visible':
            if x['a'] in visible:raise ValueError('duplicate visible address')
            visible[x['a']]=(x['edge'],x['c'])
    predicted,stats=replay(leaves)
    mismatch=[p for p in predicted if p not in set(observed)]
    if sorted(observed)!=predicted:raise ValueError('retained accepted-leaf queue replay differs from actual roots')
    if writer!=visible or len(writer)!=576:raise ValueError('actual writer/visible conservation')
    for edge,g,row in observed:
        if g!=(row%256)//2 or writer[398720+row][0]!=edge+1:raise ValueError('root owner or postNBA edge')
    return {'status':'PASS_RETAINED_ACTUAL_LEAF_TO_ROOT_AND_VISIBLE_CONSERVATION',
       'actual_identity':origin,'actual_event_counts':dict(counts),'queue_recurrence':stats,
       'actual_root_edges':[min(x[0] for x in observed),max(x[0] for x in observed)],
       'actual_visible_edges':[min(x[0] for x in writer.values()),max(x[0] for x in writer.values())],
       'registered_root_writer_visibility_offset':1,'actual_node_occupancy_observed':False,
       'internal_queue_peaks_are_source_recurrence_reconstruction_not_observed_registers':True,
       'source_queue_limits':{'node_per_side':64,'root_input':128,'root_held':128},
       'scope':'Only retained nonzero unit-weight I66 EID0 rank0 sameclock phase10. No fullprogram/current physical wrapper/other EIDs/CDC/SSFF/payload qualification.',
       'full_program_internal_bound':False,'fresh_runtime':False}

def static_phase_bound(m,positions=1):
    """No reduction credit: each original partial counted through every ancestor.
    Total lifetime writes to a child FIFO upper-bound occupancy even if service
    starves. This proves queue capacity under arbitrary accepted timing, provided
    admitted pair emits each compiled partial exactly once and phases don't mix.
    """
    leaf=collections.Counter()
    for si,g,first,n,stride,start,w in m['plans']:
        if first%128!=g//32:raise ValueError('compiled source row/root ownership')
        leaf[2*g]+=n*positions;leaf[2*g+1]+=n*positions
    maxima=[];counts=leaf
    for l in range(6):
        maxima.append(max(counts.values(),default=0))
        nxt=collections.Counter()
        for g,n in counts.items():nxt[g//2]+=n
        counts=nxt
    root_raw=max(counts.values(),default=0)
    held=max(B.root_rows(m['rows'],r) for r in range(128))*positions
    return {'max_total_writes_to_node_side_by_level':maxima,'max_total_raw_partials_to_root':root_raw,
      'unmatched_held_upper_bound':root_raw,'compiled_complete_rows_per_root_max':held,
      'pass_node64_root128_held128':max(maxima)<=64 and root_raw<=128,
      'accepted_pair_ownership_and_exact_once_is_prerequisite':True,
      'no_timing_or_child_reduction_credit_taken':True}

def all_phase_bounds(out):
    summary=collections.Counter();worst=[0]*6;worstroot=0
    with open(out,'wb') as raw, gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as zipped, io.TextIOWrapper(zipped) as f:
        for ordinal,m in enumerate(rows(ASSIGN)):
            one=static_phase_bound(m,1);six=static_phase_bound(m,6)
            summary['phases']+=1;summary['singleposition_count_certificate_PASS']+=int(one['pass_node64_root128_held128'])
            summary['sixposition_count_certificate_PASS']+=int(six['pass_node64_root128_held128'])
            worst=[max(a,b) for a,b in zip(worst,one['max_total_writes_to_node_side_by_level'])]
            worstroot=max(worstroot,one['max_total_raw_partials_to_root'])
            f.write(json.dumps({'ordinal':ordinal,'stage':m['stage'],'layer':m['layer'],'alias':m['alias'],
                'rows':m['rows'],'K':m['K'],'format':m['format'],'singleposition':one,'sixposition_counterfactual':six},sort_keys=True,separators=(',',':'))+'\n')
    return {'counts':dict(summary),'singleposition_max_node_side_writes_per_level':worst,
        'singleposition_max_root_raw_writes':worstroot,
        'scope':'Queue count certificate only. Requires exact-once admitted pair outputs and no overlapping phases. Does not prove pair XFIFO/segment queue, accepted wholeprogram scheduling, arithmetic, added bridge or physical timing.',
        'sixposition_not_count_certified_means':'Inconclusive upper bound, not proof of overflow. Source accepted replay needed; no mandatory six-position allocation.'}
