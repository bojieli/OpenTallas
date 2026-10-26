#!/usr/bin/env python3
"""Independent source coverage, colocation and objective audit for a candidate.

The audit establishes a source proposal only, never a native/physical programme.
"""
import argparse
import copy
import json
from pathlib import Path
from source_locality_assignment import read,field_rows,literal_graph,private_su_groups


def verify(demand,homes,candidate):
    nodes,edges,external=literal_graph(demand)
    if candidate.get('qualified') is not False or candidate.get('dispatch_eligible') is not False:
        raise ValueError('candidate cannot claim execution or qualification')
    if candidate.get('literal_dependency_edges')!=edges or candidate.get('unbound_symbolic_inputs')!=external:
        raise ValueError('source dependency or missing producer coverage changed')
    expected={(node,r) for node in nodes if node not in homes for r in range(4)}
    records={(r['node'],r['rank']):r for r in candidate['source_operation_homes']}
    if len(records)!=len(candidate['source_operation_homes']) or set(records)!=expected:
        raise ValueError('incomplete/duplicate/invented literal source rank assignment')
    labels={}
    for (node,rank),r in records.items():
        if r['template_sha256']!=nodes[node]['template_word_sha256']:
            raise ValueError('stale literal source template')
        if any(r.get(k) is not None for k in ('physical_instance','programme_id','core_epoch','start_cycle','duration_cycles')):
            raise ValueError('candidate invents actual implementation or execution timing')
        s=r['stage']
        if s is not None and (type(s)!=int or not 0<=s<81 or r['die_id']!=4*s+rank):
            raise ValueError('invalid canonical stage/rank die')
        if s is None and r['die_id'] is not None:raise ValueError('unanchored node invents a die')
        if node in labels and labels[node]!=s:raise ValueError('candidate rank stages disagree')
        labels[node]=s
    groups=private_su_groups(nodes,edges)[1] if candidate.get('source_colocation_constraints_applied') else []
    if candidate.get('source_private_SU_colocation_groups')!=groups:
        raise ValueError('source private SU group coverage changed')
    for group in groups:
        if len({labels[n] for n in group})!=1:raise ValueError('native source colocation group split')
    objective=0
    for e in edges:
        a,b=e['producer'],e['consumer']
        if a not in homes and b not in homes:
            if labels[a] is not None and labels[b] is not None:objective+=labels[a]!=labels[b]
        elif (a in homes)!=(b in homes):
            variable,field=(a,b) if a not in homes else (b,a)
            stage=labels[variable]
            if stage is None:raise ValueError('FIELD-adjacent operation has no candidate home')
            choices=[{f['stage'] for f in c['fragments']} for c in homes[field]['canonical_choices']]
            objective+=max(sum(s!=stage for s in choice) for choice in choices)
    if candidate['objective']['final']!=objective:raise ValueError('reported boundary objective differs from actual source edges')
    return dict(source_rank_records=len(records),source_SU_rank_records=sum(nodes[n]['instruction']['unit']==2 for n,_ in records),
                colocation_groups=len(groups),objective=objective,native_qualified=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('demand','field-homes','candidate','out'):ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();demand=read(a.demand);homes=field_rows(a.field_homes);candidate=read(a.candidate)
    report=verify(demand,homes,candidate);mutants={}
    def reject(name,mutant):
        try:verify(demand,homes,mutant)
        except ValueError as exc:mutants[name]=str(exc);return
        raise AssertionError('mutant unexpectedly admitted: '+name)
    bad=copy.deepcopy(candidate);bad['source_operation_homes'][0]['template_sha256']='0'*64;reject('changed_literal_template',bad)
    bad=copy.deepcopy(candidate);bad['source_operation_homes'].pop();reject('missing_source_rank_operation',bad)
    bad=copy.deepcopy(candidate);bad['objective']['final']-=1;reject('invented_objective_improvement',bad)
    if candidate['source_private_SU_colocation_groups']:
        bad=copy.deepcopy(candidate);group=bad['source_private_SU_colocation_groups'][0];node=group[0]
        stage=next(r['stage'] for r in bad['source_operation_homes'] if r['node']==node)
        for r in bad['source_operation_homes']:
            if r['node']==node:r['stage']=(stage+1)%81;r['die_id']=4*r['stage']+r['rank']
        reject('split_source_native_colocation_group',bad)
    report.update(status='SOURCE_CANDIDATE_VERIFIED_NOT_NATIVE',mutants_rejected=mutants)
    a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
