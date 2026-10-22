#!/usr/bin/env python3
"""Synthetic adapter checks only; this never executes or qualifies hardware."""
import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import normalize_cap_sukv_events as N


def run(root):
    root=Path(root);root.mkdir(exist_ok=False)
    source=root/'source';p=source/'tools/s81_dv/layer_prog';p.mkdir(parents=True)
    for name in ('kv_bank_contract.py','lower_vs.py'):
        shutil.copy2(Path(__file__).parent/name,p/name)
    sys.path.insert(0,str(p.parent))
    spec=importlib.util.spec_from_file_location('test_actual_dispatch',p/'kv_bank_contract.py')
    api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
    word=api.dispatch(7,0,0,1024,parameter_base=528,operand_base=896)
    tb=source/'tools/s81_dv/tb_cap_sukv.sv'
    tb.write_text('if(cyc==4900)begin\n$display("JSON RUN_END");\nend\n')
    data=root/'run';images=data/'images';images.mkdir(parents=True)
    (images/'capture.hex').write_text('0\n')
    (images/'gk_command.hex').write_text(f'{word:040x}\n')
    binary=data/'obj/Vtb_cap_sukv';binary.parent.mkdir();binary.write_bytes(b'TEST_ONLY_NOT_AN_EXECUTABLE')
    owner='L2.attn.kv_norm.sumsq';job='L2_KV_GAIN0'
    header=dict(schema=N.E.SCHEMA,record='run_identity',run_id=N.E.SHARED_RUN,
        scope='SYNTHETIC_ADAPTER_TEST_ONLY',owner=owner,source_rank=0,source_native_rows=[2,3],target_rows=[692,693],
        source_sha256={'tools/s81_dv/tb_cap_sukv.sv':N.E.sha(tb)},
        reference_source_files_sha256={str(f.relative_to(source)):N.E.sha(f) for f in p.glob('*.py')},
        runtime_images_sha256={f.name:N.E.sha(f) for f in images.iterdir()},binary_sha256=N.E.sha(binary))
    values=list(range(1,9));pair=sum(v<<(32*i) for i,v in enumerate(values))
    def event(kind,edge,**kw):return 'JSON '+json.dumps(dict(record='event',kind=kind,edge=edge,**kw))
    raw=[f'EV CAP_WRITE {100+i} {8+i} {v:08x}' for i,v in enumerate(values)]
    raw += [event('CARRIAGE_WRITE',200,instance='dst.u',source_native_row=2,target_row=692,
                  mask8='ff',word256=f'{pair:064x}'),
            event('DISPATCH_CAPTURE',3500,owner=owner,job=job,command_kind='GK',gain_set=0,gain_epoch=1),
            'EV GK_DONE 4525',event('GK_DONE',4525,owner=owner,job=job,command_kind='GK',gain_set=0,gain_epoch=1),
            event('RUN_END',4900,future_consumer_lease=None),
            'CAP_SUKV_END cap=8 pair=1 gain=1 bad=0 faults=00 xs=0 capfault=0','CAP_SUKV_PASS']
    (data/'run_mut0.log').write_text('\n'.join(raw)+'\n')
    (data/'run_mut1.log').write_text('PAIR_MISMATCH\nCAP_SUKV_FAIL\n')
    (data/'result.json').write_text(json.dumps(dict(status='PASS',checks={'0':True,'1':True})))
    def save(h): (data/'identity.json').write_text(json.dumps(h))
    save(header);h,events=N.normalize(data,source)
    assert len([e for e in events if e['kind']=='GK_DONE'])==1
    assert len([e for e in events if e['kind']=='RUN_END'])==1
    assert len([e for e in events if e['kind']=='CARRIAGE_WRITE'])==2
    assert h['native_commands'][0]['word160']==f'{word:040x}'
    caught=[]
    def refuse(name):
        try:N.normalize(data,source)
        except ValueError as exc:caught.append(dict(case=name,error=str(exc)))
        else:raise AssertionError('missed '+name)
    command=images/'gk_command.hex';text=command.read_text();command.unlink()
    changed=deepcopy(header);changed['runtime_images_sha256'].pop('gk_command.hex');save(changed)
    refuse('missing_actual_GK_image');command.write_text(text);save(header)
    changed=deepcopy(header);changed['reference_source_files_sha256'].pop('tools/s81_dv/layer_prog/kv_bank_contract.py')
    save(changed);refuse('missing_compiler_API_readset');save(header)
    changed=deepcopy(header);changed['reference_source_files_sha256']['tools/s81_dv/layer_prog/lower_vs.py']='0'*64
    save(changed);refuse('wrong_native_encoder_readset');save(header)
    binary.write_bytes(b'CHANGED');refuse('changed_actual_binary');binary.write_bytes(b'TEST_ONLY_NOT_AN_EXECUTABLE')
    (data/'run_mut0.log').write_text('\n'.join(s for s in raw if 'RUN_END' not in s)+'\n')
    refuse('missing_actual_finite_end');(data/'run_mut0.log').write_text('\n'.join(raw)+'\n')
    result=dict(status='PASS',scope='SYNTHETIC_ADAPTER_TEST_ONLY',normalizer_sha256=N.E.sha(N.__file__),
        causal_refusals=caught,hardware_qualified=False,production_enabled=False)
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS synthetic raw adapter;',len(caught),'causal refusals; no hardware replay or qualification')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
