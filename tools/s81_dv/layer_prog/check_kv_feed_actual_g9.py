"""Pure actual-G9 CAP address/route/control assembly check; no runtime/MAT."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from layer_prog import kv_operand_feed as F

PARSER_REF='802a6d63d868774356d9418814d770b431d3a244'
FIXTURE_META_SHA='d7f2eb6175bec6a21f2ccede5a103842d7d03e36c54b4859b967a6e04ba44b28'
SNAPSHOTS={'parser-source': {'ref': '802a6d63d868774356d9418814d770b431d3a244', 'path': 'tools/s81_dv/tokfunc/selected_cap_phase.py', 'sha256': 'e60fca98d5f0dae97257716b1c4a90c6911935eb82ac1490bd0899992af8c66f'}, 'driver-source': {'ref': 'f14ca52e7e37d54f28a4aee36f35906537584916', 'path': 'tools/s81_dv/dv_layer_compile.py', 'sha256': '1e26495715f1c8a992a35170307482883b1e8fe0d2dd54eea31bc4470a350517'}, 'lower-xs-source': {'ref': 'f14ca52e7e37d54f28a4aee36f35906537584916', 'path': 'tools/s81_dv/layer_prog/lower_xs.py', 'sha256': '89091fb1b1c791b94759e09b599c08736ca24099e0165fd10188917368024015'}, 'bindings-source': {'ref': '7373f3015e1c0ed89e0f4e7ab1900b0ff4b4b8ca', 'path': 'results/arch/s81_die72_1021/g9_assembly/actual_source_bindings.json', 'sha256': '5e2de380659740383ab311382803d92b34b8cf49359a3167d6f9aa3c56e6d7ee'}}
PLAN_SHA='5a061882234eb18f4bea0ca2dd2af93922a20d08f203d25260b18d4892ee08a1'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['actual-die','actual-plan','fixture-meta','fixture-files','out']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--source-readset',type=Path,help='actual full G9 normalized readset; absence keeps native fragment held')
    for name in SNAPSHOTS:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def snapshot(name):
        path=getattr(a,name.replace('-','_'));raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SNAPSHOTS[name]['sha256']:
            raise ValueError('portable source snapshot SHA256 mismatch: '+name)
        return raw
    assert sha(a.actual_die)==F.G9_DIE_SHA256 and sha(a.actual_plan)==PLAN_SHA
    assert sha(a.fixture_meta)==FIXTURE_META_SHA
    assert sha(a.fixture_files)=='528904b75d19c03948bb35e190903caf8d2a90fa049b3b1990570e670c102bed'
    meta=json.loads(a.fixture_meta.read_text());files=json.loads(a.fixture_files.read_text())
    # Real fixture metadata and raw-weight dimensions only; no operand, MAT,
    # reference output or checkpoint intermediate is read by this check.
    fx=dict(meta=meta,w={n:[SimpleNamespace(shape=tuple(files['weights/'+n+'.bin']['shape']))]
                         for n in ['wq_a','wkv']})
    driver_source=snapshot('driver-source')
    tree=ast.parse(driver_source);nodes=[n for n in tree.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id in ['INST_RE','CONN_RE'] for t in n.targets)]
    env={'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual_compiler_regex','exec'),env)
    parser_source=snapshot('parser-source');owner={}
    exec(compile(parser_source,'selected_cap_phase.py','exec'),owner)
    die=owner['ComponentDie'](a.actual_die,a.actual_plan,SimpleNamespace(**env))
    lower_source=snapshot('lower-xs-source')
    fn=[n for n in ast.parse(lower_source).body if isinstance(n,ast.FunctionDef) and n.name=='a_proj_rows']
    fn_env={};exec(compile(ast.Module(body=fn,type_ignores=[]),'real_a_proj_identity','exec'),fn_env)
    sl='u_s_0N';frames=[dict(frame=f,master=die.inst[f]['master'],lk=die.strap(f,'lk')) for f in die.frames_of(sl)]
    assert len(frames)==6
    inventory=dict(selected_slice=sl,selected_ownership={'B':frames},selected_instances=die.inst)
    cap=owner['explicit_capture'](inventory,fx,SimpleNamespace(**fn_env),list(range(320,344)),'wkv')
    cap['die_sha']=die.die_sha
    # Only the real source descriptor's native target3 command is needed for
    # feed assembly. This is not a generated/executed MAT or XS programme.
    word=int(cap['cfg_d'],16);payload=(1<<die.slices()[sl]['sid'])|(3<<16)|(word<<26)
    programme=dict(schema='opentallas.s81.selected_local_cap_phase.v1',capture=cap,
        command_descriptors=[dict(target=3,body160=cap['cfg_d'],payload186=f'{payload:047x}')],
        qualification='actual metadata/control constructor only; no MAT/XS assets or producer execution')
    words=F.capture_readset(programme,meta['rank']);assert len(words)==24
    route=F._horizontal(die,die.slices()[sl]['sid'],die.slices()['u_s_3N']['sid'])
    assert len(route)==3 and all(len(h['actual_lane_chains'])==4 for h in route)
    assert all(h['age_edges'] is None and not h['clock_phase_qualified'] for h in route)
    bindings=snapshot('bindings-source')
    readset=json.loads(a.source_readset.read_text()) if a.source_readset else {}
    assembled=F.assemble(die,[dict(rank=meta['rank'],programme=programme)],bindings,readset)
    assert not assembled['scheduled_rows'] and assembled['dispatch'] is None and assembled['actual_resident_kv_scalars']==0
    native=assembled['native_pair_fragments']
    if a.source_readset and native:
        assert len(native)==3, assembled['holds']
        for i,packet in enumerate(native):
            assert packet['kv_indices']==list(range(8*i,8*i+8))
            cfg,rd=[int(t['payload186'],16) for t in packet['native_templates']]
            assert (cfg&65535)==2 and (cfg>>16)&31==4 and (cfg>>21)&31==0
            body=cfg>>26
            assert body&15==1 and (body>>4)&7==4 and (body>>7)&31==3
            assert (body>>12)&65535==128 and (body>>28)&7==0 and (body>>31)&1023==692+2*i
            assert (rd&65535)==2 and (rd>>16)&31==0 and (rd>>21)&31==1
            assert (rd>>26)&15==6 and (rd>>(26+4))&1023==2*i and (rd>>(26+24))&255==1
        status='PASS_PURE_ACTUAL_G9_NATIVE_FRAGMENT'
    else:
        assert not native and any('source readset' in h or 'source-input manifest' in h for h in assembled['holds'])
        status='PARTIAL_ACTUAL_G9_ROUTE_READSET_VERIFIED_SOURCE_PROFILE_HELD'
    result=dict(status=status,actual_die_sha256=die.die_sha,actual_plan_sha256=die.plan_sha256,
        fixture_meta_sha256=sha(a.fixture_meta),fixture_files_sha256=sha(a.fixture_files),
        portable_snapshot_inputs=SNAPSHOTS,parser_ref=PARSER_REF,parser_sha256=hashlib.sha256(parser_source).hexdigest(),
        actual_lane_hops=12,source_phase_qualified=False,source_descriptor=programme,
        first_blocker=assembled['holds'][0],
        source_profile_provenance=dict(source_readset_file_sha256=sha(a.source_readset),
            source_inputs_manifest_sha256=hashlib.sha256(readset['source_inputs_manifest_text'].encode()).hexdigest(),
            port_bind_sha256=hashlib.sha256(readset['port_bind_text'].encode()).hexdigest(),
            ordered_selected_rtl_sha256=readset['selected_rtl_sha256']) if a.source_readset else None,
        actual_source_routes=route,feed=assembled,simulation=False,source_MAT_assets_generated=False,
        runtime_launch=False,historical_status_counts_changed=False,
        code_sha256={p.name:sha(p) for p in [Path(__file__),Path(F.__file__)]})
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(status)


if __name__=='__main__':main()
