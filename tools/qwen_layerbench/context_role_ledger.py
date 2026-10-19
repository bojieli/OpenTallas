"""Compile static offered context roles; clock/publication bindings remain open."""
import argparse,gzip,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(words):
    t=0;out=[]
    for index,w in enumerate(words):
        t+=w>>18
        for i in range((w&31)+1):
            out.append(dict(entry=index,run_ordinal=i,source_offset=t+i,
                kind=(w>>10)&15,beat=((w>>5)&31)+i))
        t+=w&31
    return out

def build(admission,frame,cold,sources):
    events=[e for e in decode(frame['im']['tok_rx']['C_rx']['img']) if e['kind']==12]
    if len(events)!=2 or [e['beat'] for e in events]!=[1,0]:
        raise ValueError('SEG1 context role order requires exact beat1 then beat0')
    if cold['context']['user']!=0 or cold['context']['logical_kind']!=12 or cold['context']['logical_beat']!=0:
        raise ValueError('explicit SEG2 context must be user0 kind12 beat0')
    roles=[]
    for start_index,start in enumerate(admission['link_starts']['C_rx']):
        if start['segment']!=1:continue
        u=start['user']
        if u not in range(4):raise ValueError('owner user outside canonical four')
        for ordinal,e in enumerate(events):
            seed=ordinal==0 and u!=0
            roles.append(dict(id=f'C_RX_SEG1_START_{start_index}_K12_{ordinal}',
              source_start_index=start_index,source_start=start,segment=1,kind12_ordinal=ordinal,
              entry=e['entry'],logical_kind=12,logical_beat=e['beat'],cal_user_rx=u,
              context_user=u if ordinal==0 else 0,
              role='fresh-filler-context' if seed else 'preserve-user0-context',
              seed_pending=seed,epoch_slot=seed,accepted_sample=None,
              publication=dict(required=seed,source_event='landed CTLM ctx_ld with immutable static bank mask' if seed else None,
                bank_mask=(1<<u) if seed else 0,sample=None),
              physical_offer_sample=None,source_offset=e['source_offset']))
    roles.append(dict(id='C_RX_SEG2_EXPLICIT_NEW_USER0',segment=2,kind12_ordinal=0,
      logical_kind=12,logical_beat=0,cal_user_rx=0,context_user=0,role='fresh-initial-or-new-user0-context',
      seed_pending=True,epoch_slot=True,accepted_sample=None,physical_offer_sample=None,
      publication=dict(required=True,source_event='landed registered init_u0_q && d_start && d_stage0/user0 (coincident s_start is insufficient by itself)',bank_mask=1,sample=None)))
    return dict(schema='opentallas.qwen.context-role-ledger.v1',production_bound=False,
      source_scope='public cap0 diagnostic fixture; roles only, no timing/capability adoption',
      sources={k:dict(path=str(p),sha256=sha(p)) for k,p in sources.items()},
      semantic_owner_source='SYSFACE companion240a2a350; explicit source-scoped role contract',
      publication_source=dict(commit='9ca1bc85c',GI_sha256='754c9b8c0cf2cfb5ae36e9d3d12f8d19c933d99076c0393cc7e02afa58ca5364'),
      role_count=len(roles),roles=roles,
      invariants=['acceptance seeds pending only; publication is a later separate immutable bank event',
        'SEG1 user0 header and restore both preserve active0 and seed no pending epoch',
        'SEG1 first kind12 beat1 seeds only static owner users1..3',
        'SEG1 second kind12 beat0 restores user0, regardless of cal_user_rx',
        'SEG2 explicit initial/new-user0 context alone seeds pending0',
        'No role is inferred from accepted TAG, CRC-valid level, or live host identity'],
      physical_clock_axis=None,production_INIT_FIRST=None,
      blockers=['actual production full frame/context-role manifest absent',
        'LP landed bank-publication and accepted sample times unbound',
        'same-clock token/epoch embedding fetch-fill-consume-release composition absent'])
def main():
    ap=argparse.ArgumentParser()
    for key in ('admission','frame','cold','out'):ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args();paths={k:getattr(a,k) for k in ('admission','frame','cold')}
    d={k:json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()) for k,p in paths.items()}
    out=build(**d,sources=paths);a.out.write_text(json.dumps(out,indent=2)+'\n')
    print('CONTEXT_STATIC_ROLE_LEDGER',out['role_count'],'roles; production false; publication timestamps null')
if __name__=='__main__':main()
