"""Join exact cfg inventory to retained service costs and audit native descriptor keys."""
import json,gzip,hashlib,io,tarfile,argparse
from collections import Counter,defaultdict
from pathlib import Path
D=Path(__file__).resolve().parents[1]/'results/uarch/dsrom_cfg_service_join_r19_20261002'

def inputs():
    manifest=json.loads((D/'snapshot_manifest.json').read_bytes());raw=(D/'source_metadata.tar.gz').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=manifest['archive_sha256']:raise ValueError('archive digest')
    result={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        for e in manifest['entries']:
            b=tar.extractfile(e['member']).read()
            if len(b)!=e['bytes'] or hashlib.sha256(b).hexdigest()!=e['sha256']:raise ValueError('source digest')
            if e['member'].endswith('.gz'):b=gzip.decompress(b)
            result[e['member']]=[json.loads(x) for x in b.splitlines()] if '.jsonl' in e['member'] else json.loads(b)
    return result

def model():
    i=inputs();x=i['interface.json'];ph=i['phase_directory.jsonl.gz'];kt=i['key_tables.jsonl.gz'];pr=i['immutable_provider_directory.jsonl.gz'];ec=i['FP4_ECC_provider_directory.jsonl.gz'];dem=i['demand-r5.json.gz'];gaps=i['calendar_provider_gaps-r5.json']
    assert x['candidate']==gaps['candidate']=='DS4096-TP4-S58-PAIR1'
    assert len(ph)==46509 and len(kt)==58 and len(pr)==80 and len(ec)==58
    tables={r['stage']:r['words'] for r in kt}; identities=set();counts=Counter();active=Counter()
    for p in ph:
        identity=(p['stage'],p['phase']);assert identity not in identities;identities.add(identity)
        assert tables[p['stage']][p['phase']]==p['source_key_word']
        assert p['config_logical_word_range']==[p['phase']*25,(p['phase']+1)*25]
        counts[p['stage']]+=1;active[p['stage']]+=p['active_pair_count']*25
    stages=[]
    for stage in range(58):
        assert len(tables[stage])==1024
        assert sum(bool(w>>31) for w in tables[stage])==counts[stage]
        stages.append({'stage':stage,'compiled_pairs':4096,'TP_ranks':4,'phases':counts[stage],
          'cfg_physical_instances_per_rank':28672,'cfg_pins_per_rank':2523136,'keytable_bits_per_rank':32768,
          'cfg_loader_words_over_used_phases_per_rank':counts[stage]*4096*25,
          'active_pair_cfg_word_subset_per_rank':active[stage],
          'cfg_events':'request(pair,phase,word,generation) -> reserved capture -> paired physical return -> ECC good/corrected -> c_v delivery -> actual word24/act fence -> go',
          'critical_path':'go_time=max(native ready, all25 per-pair delivered-good fences, operand visibility, generation lease admitted); result=go_time+source-owned field/return/consumer schedule',
          'generic27cycle_is_physical_latency':False,'cfg_or_ECC_or_generation_implemented':False})
    desc=[];census=Counter()
    for node in dem['nodes']:
        ins=node.get('instruction',{});unit=ins.get('unit');kind=None
        if unit==3 and 'qe_wbase' in ins:kind='QE';field='qe_wbase'
        elif unit==1 and ins.get('me_wsrc')==0:kind='ME';field='me_wbase'
        if kind:
            key=ins[field];census[kind]+=1;census[kind+'_zero_wbase']+=key==0
            desc.append({'node_id':node['id'],'kind':kind,'retained_wbase':key,'template_word_sha256':node['template_word_sha256'],'exact_phase_provider_binding':False,
               'required_binding':'Address patches + selected expert VM read/stride where indexed + native mode/admission predicates + stage/phase identity + finite calendar receipt; tags are not executable patches'})
    ledger=x['parent_whole_budget'];assert ledger['already_inside_inherited_named_service_proxy_do_not_add_again']>90
    return {'status':'PASS_EXACT_INVENTORY_SERVICE_JOIN_BLOCKED_EXECUTABLE_CALENDAR','candidate':x['candidate'],
       'source_manifest':'snapshot_manifest.json','phase_identity_joins':len(identities),'immutable_providers':len(pr),'ECC_sidecars':len(ec),'stage_inventory':stages,
       'system_cfg_instances':58*4*28672,'system_cfg_pins':58*4*2523136,'descriptor_key_audit':dict(census),'weight_descriptor_audit':desc,
       'descriptor_calendar':{'actual_instruction_descriptors':4778,'rank_calendar_nodes':gaps['rank_nodes'],'received_service_calendar_bindings':gaps['actual_service_calendar_bindings_received'],'bound_by_this_join':0,'all_native_descriptors_bound':False},
       'retained_whole_budget':ledger,'service_doublecharge_mm2':0,'containment_credit_mm2':0,
       'storage_PASS_is_not_current_native_program_PASS':True,'partition_selection':False,'runtime_or_rate_or_physical_admission':False,'jobs':[],
       'exact_blockers':['Native descriptor address patches and ordered runtime expert selection to exported keys are absent in demand-r5','Every descriptor still needs accepted cfg/codeword/ECC/raw-provider/return/consumer event calendars','Finite cfg generation lease and poison/fault/drain endpoint unimplemented; no timer-based reuse','HE/CROM native interface adapters and exact reply schedules unimplemented','Conservative whole-die margin remains negative; no reduction or replacement credit']}

def emit(output):
    output.mkdir(parents=True,exist_ok=True);m=model();audit=m.pop('weight_descriptor_audit')
    raw=json.dumps(audit,sort_keys=True,separators=(',',':')).encode();packed=gzip.compress(raw,mtime=0);(output/'weight_descriptor_audit.json.gz').write_bytes(packed)
    m['weight_descriptor_audit_sha256']=hashlib.sha256(packed).hexdigest();(output/'join.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);emit(p.parse_args().output)
