"""Join addressed Qwen demand to die/stack/PC and locked RMW service costs.

Existing descriptor output only; no checkpoint access, payload reconstruction
or inferred provider timestamps. Partial sectors cost READ+merge+full WR.
"""
from collections import Counter
import hashlib,json,subprocess
from pathlib import Path
from w13_provider_resource_calendar import write_calendar


def join(rows):
    traffic=Counter();ids=set();dependencies={};first=None
    for q in rows:
        if first is None:first=q
        if q['id'] in ids:raise ValueError('duplicate descriptor')
        ids.add(q['id']);die,stack,pc=q['die'],q['stack'],q['PC']
        if die not in (0,1) or not 0<=stack<4 or q['physical_stack']!=die*4+stack:
            raise ValueError('die stack identity')
        if pc!=((q['sector']>>2)^(q['sector']>>7)^(q['sector']>>12))&31:
            raise ValueError('address PC mapping')
        partial=q['byte_mask']!=(1<<32)-1
        if q['RMW_required']!=partial:raise ValueError('mask/RMW demand mismatch')
        key=(q['position'],die,stack,pc)
        traffic[key,'WR_ACK']+=1;traffic[key,'full_WR_commands']+=1
        traffic[key,'locked_RMW_READ_commands']+=partial
        traffic[key,'port_bytes']+=32*(1+partial)
        dependencies[q['position'],q['instruction']]={k:q[k] for k in ('producer_instructions','fence_instruction','read_instruction','scores_instruction','pv_instruction')}
    scopes=[]
    for key in sorted({k for k,kind in traffic}):
        values={kind:traffic[key,kind] for kind in ('WR_ACK','full_WR_commands','locked_RMW_READ_commands','port_bytes')}
        scopes.append(dict(position=key[0],die=key[1],stack=key[2],PC=key[3],**values))
    bystack=[]
    for pos,die,stack in sorted({k[:3] for k,kind in traffic}):
        rows=[s for s in scopes if (s['position'],s['die'],s['stack'])==(pos,die,stack)]
        values={kind:sum(s[kind] for s in rows) for kind in ('WR_ACK','full_WR_commands','locked_RMW_READ_commands','port_bytes')}
        bystack.append(dict(position=pos,die=die,stack=stack,**values))
    trial=write_calendar([first],4,1000,2000,7274,10000) if first else {'calendar':None,'issues':['empty demand']}
    return {'descriptor_count':len(ids),'per_position_die_stack_PC':scopes,'per_position_die_stack':bystack,
        'WR_visible_ACK_obligations':sum(s['WR_ACK'] for s in scopes),
        'locked_RMW_READ_obligations':sum(s['locked_RMW_READ_commands'] for s in scopes),
        'combined_READ_WR_commands':sum(s['full_WR_commands']+s['locked_RMW_READ_commands'] for s in scopes),
        'combined_port_bytes':sum(s['port_bytes'] for s in scopes),
        'source_phase_dependencies':[dict(position=k[0],writer_instruction=k[1],**v) for k,v in sorted(dependencies.items())],
        'provider_admission_trial':trial,'RMW_lock_release':'full backing-visible WR identity + visible ACK and consumer/credit drain; acceptance is insufficient',
        'physical_provider_clock_and_calendar':None,'checkpoint_reads':0,'hardware_admission':False}


def build(jsonl):
    path='results/rtl/qwen_hbm_complete_20261001/controller_demand_two_positions_r2.json'
    raw=subprocess.check_output(['git','show','18fd06590:'+path]);source=json.loads(raw)
    data=Path(jsonl).read_bytes();assert hashlib.sha256(data).hexdigest()==source['JSONL_sha256']
    for p,v in source['source_pins'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',v['commit']+':'+p])).hexdigest()==v['sha256']
    out=join(json.loads(line) for line in data.splitlines())
    out.update(schema='w13.controller-addressed-resource-join.v1',demand_receipt={'git':'18fd06590','path':path,'sha256':hashlib.sha256(raw).hexdigest()},
        verified_source_pins=source['source_pins'],source_JSONL_sha256=source['JSONL_sha256'])
    return out


if __name__=='__main__':
    import sys
    Path(sys.argv[2]).write_text(json.dumps(build(sys.argv[1]),separators=(',',':'))+'\n')
