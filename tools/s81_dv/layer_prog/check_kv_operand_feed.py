"""Necessary pure CAP/readset/native-feed API checks; no RTL or producer data."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from layer_prog import kv_operand_feed as F

REF='9e69e49319ffa16cfe2a1bd3be81a5bacdefb3f9'
BIND_REF='7373f3015'
BIND_PATH='results/arch/s81_die72_1021/g9_assembly/actual_source_bindings.json'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[3]
    def blob(ref,path):return subprocess.check_output(['git','-C',str(root),'show',ref+':'+path])
    bindings_raw=blob(BIND_REF,BIND_PATH);bindings=json.loads(bindings_raw)
    assert hashlib.sha256(bindings_raw).hexdigest()==F.BINDINGS_SHA256
    readset=dict(files_sha256=F.ADDRESS_SOURCES,defines=bindings['defines'],
                 source_inputs_manifest_sha256=bindings['source_inputs_manifest_sha256'])
    cases={};records={}
    for half in ['A','B']:
        raw=blob(REF,'results/token_pass/s81_aggregate_source_1021/aggregate_replay_selected_'+half+'.json')
        programme=json.loads(raw)
        out=F.assemble(None,[dict(rank=0,programme=programme)],bindings_raw,readset)
        assert out['source_only_kv_scalars']==0 and not out['native_pair_fragments']
        assert out['actual_resident_kv_scalars']==0 and out['dispatch'] is None and not out['scheduled_rows']
        cases['historical_'+half+'_is_zero_KV_not_512']=True
        records[half]=dict(programme_sha256=hashlib.sha256(raw).hexdigest(),cfg=programme['capture']['cfg'],
                           scalar_count=len(programme['capture']['rows']),tensors=['wq_a'],feed=out)
    # Exercise the actual new producer owner's descriptor constructor, using
    # identity-only type fixtures. No MAT, weights, scalar data, residency or
    # actual source-phase generation is created or qualified by this check.
    ns={};owner_source=blob(REF,'tools/s81_dv/tokfunc/selected_cap_phase.py')
    exec(compile(owner_source,'selected_cap_phase.py','exec'),ns)
    actual=programme['capture']['frames']
    inventory=dict(selected_slice='u_s_0N',selected_ownership={'B':actual},
                   selected_instances={'u_s_0N':dict(conns={'sid':"4'd1"})})
    identities=[('wq_a',i,i) for i in range(320)]+[('wkv',i,1280+i) for i in range(128)]
    cap=ns['explicit_capture'](inventory,None,SimpleNamespace(a_proj_rows=lambda fx:identities),list(range(320,344)),'wkv')
    cap['die_sha']=F.G9_DIE_SHA256
    body=int(cap['cfg_d'],16);payload=(1<<1)|(3<<16)|(body<<26)
    fixture=dict(schema='opentallas.s81.selected_local_cap_phase.v1',capture=cap,
                 command_descriptors=[dict(target=3,body160=cap['cfg_d'],payload186=f'{payload:047x}')])
    words=F.capture_readset(fixture,0)
    assert len(words)==24 and [r['kv_index'] for r in words]==list(range(24))
    assert all((r['leaf'],r['native128_row'],r['word_lane'],r['word_mask4'])==
               (0,i//4,i%4,1<<(i%4)) for i,r in enumerate(words))
    held=F.assemble(None,[dict(rank=0,programme=fixture)],bindings_raw,readset)
    assert held['actual_completeness_mask512']=='0'*128 and held['dispatch'] is None
    assert len(held['missing_source_kv_indices'])==488 and not held['scheduled_rows']
    cases['owner_explicit_24_scalar_address_API_not_packed16']=True
    cases['24_source_descriptors_are_zero_actual_residency_and_no_dispatch']=True
    def reject(name,change):
        malformed=copy.deepcopy(fixture);change(malformed)
        try:F.capture_readset(malformed,0)
        except ValueError:cases[name]=True;return
        raise AssertionError(name)
    reject('wrong_native_target_mask',lambda x:x['command_descriptors'][0].update(payload186='0'))
    reject('wrong_CFG_word',lambda x:x['capture'].update(cfg_d='0'))
    reject('wrong_frame_MAT_ownership',lambda x:x['capture']['frames'][0].update(rows=[0,1,2,3]))
    reject('wrong_packed16_row_map',lambda x:x['capture']['rows'][4].update(native128_row=0))
    reject('wrong_rank_identity',lambda x:x['capture']['rows'][0].update(golden_output_index=1408))
    empty=F.assemble(None,[dict(rank=0,programme=fixture)],bindings_raw,{})
    assert not empty['native_pair_fragments'] and any('seven-define' in h for h in empty['holds'])
    cases['missing_actual_source_readset_blocks_native_fragment']=True
    result=dict(status='PASS_PURE_FEED_API_CHECK',cases=cases,historical_actual_programmes=records,
                owner_constructor_sha256=hashlib.sha256(owner_source).hexdigest(),
                explicit_descriptor_fixture_scope='PURE IDENTITY/ADDRESS API ONLY; no generated MAT/producer or residency',
                explicit_descriptor_fixture_readset=words,explicit_descriptor_fixture_actual_resident=0,
                source_binding_sha256=F.BINDINGS_SHA256,
                code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(F.__file__)]},
                simulation=False,runtime_launch=False,historical_status_counts_changed=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])


if __name__=='__main__':main()
