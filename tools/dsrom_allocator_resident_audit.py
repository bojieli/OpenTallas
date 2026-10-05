#!/usr/bin/env python3
"""Read-only bounded audit of frozen symbolic allocator metadata, never weights."""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
import dsrom_resident_site_binding as R

def sha_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def audit(root):
    names=['model.json','assignments.jsonl.gz','compiler_source.py','provider_assignment.jsonl.gz']
    before={n:(root/n).stat() for n in names}
    if before['assignments.jsonl.gz'].st_size>64*1024*1024:raise ValueError('bounded metadata compressed-size limit')
    model=json.loads((root/'model.json').read_text());stats={x['stage']:x for x in model['stage_stats']}
    if model['candidate_id']!='DS4096-TP4-S58-PAIR1':raise ValueError('one shared candidate')
    ranges=collections.defaultdict(list);formats=collections.defaultdict(set);counts=collections.Counter();bad=collections.Counter();examples=[]
    with gzip.open(root/'assignments.jsonl.gz','rt') as f:
        for line in f:
            m=json.loads(line);counts['matrix_records']+=1
            if m['stage'] is None:counts['unallocated_matrix_records']+=1;continue
            stage=m['stage'];fmt=m['format'];s=stats[stage]
            mask=R.rtl_bf_sites(s['compiled_NP'],s['NBF_shape'])
            for seg,p,first,n,stride,start,w in m['plans']:
                end=start+n*w;counts['allocated_plan_spans']+=1
                ranges[(stage,p)].append((start,end,fmt,m['alias']))
                formats[(stage,p)].add(fmt)
                if fmt=='bf16' and p not in mask:
                    bad['BF_on_source_q_plan_spans']+=1;bad['BF_on_source_q_words_both_slots']+=2*n*w
                    if len(examples)<12:examples.append({'stage':stage,'layer':m['layer'],'alias':m['alias'],'pair':p,'start':start,'end':end})
                if fmt in ('fp4','fp8') and p in mask:
                    bad['q_on_source_BF_plan_spans_needing_dual_abstract']+=1
                if not 0<=start<end<=8192:bad['depth_fault_spans']+=1
    used=0;overlap=0;highwater=0
    for key,rs in ranges.items():
        rs.sort();end=0
        for a,b,fmt,alias in rs:
            if a<end:overlap+=1
            end=max(end,b);used+=2*(b-a)
        highwater+=2*end
    q={k for k,f in formats.items() if f&{'fp4','fp8'}};bf={k for k,f in formats.items() if 'bf16' in f}
    for n,st in before.items():
        now=(root/n).stat()
        if (st.st_size,st.st_mtime_ns)!=(now.st_size,now.st_mtime_ns):raise ValueError('allocator metadata changed during audit')
    return {'schema':'opentallas.dsrom.source-resident-allocator-audit.v1','candidate':model['candidate_id'],
        'observational_draft_only':True,'allocator_source_commit':model['source_commit'],
        'input_receipts':[{'path':str(root/n),'bytes':before[n].st_size,'sha256':sha_file(root/n)} for n in names],
        'census':dict(counts),'source_provider_faults':dict(bad),'fault_examples':examples,
        'shared_residency':{'q_sites':len(q),'BF_sites':len(bf),'mixed_q_BF_sites':len(q&bf),
            'unique_sites':len(q|bf),'matrix_payload_reserved_words_both_slots':used,
            'matrix_highwater_including_holes_words_both_slots':highwater,'overlapping_immutable_spans':overlap,
            'scope':'one four-rank symmetric placement template perstage; raw/HE/CROM/ECC provider reservations remain separate and not credited away'},
        'preserved_allocator_verdict':model['capacity_verdict'],'allocator_failure_count':len(model['allocation_failures']),
        'first_allocator_failure':model['allocation_failures'][0] if model['allocation_failures'] else None,
        'source_PHW6_verdict':model['current_source_PHW6_verdict'],'ECC_verdict':model['ECC_verdict'],
        'physical_catalog_gate':'BF frame is model outline with no full dualcompute hardabstract; q_on_BF remains blocked without actual matching abstract/parameter and resident-depth proof',
        'FAILs_preserved':True,'hardware_or_area_credit':False,'selected_count':False,'jobs_launched':0}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();x=audit(a.input);a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
if __name__=='__main__':main()
