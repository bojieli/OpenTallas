"""Restore compiler metadata from archived native DS images without inference.

No checkpoint/model constructor or memory/golden regeneration. The restored
metadata is admitted ONLY when every original linked native word matches the
archived four IMEM images. Candidate constants/descriptors retain that baseline
namespace. This reduced source archive cannot qualify released 1M execution.
"""
from pathlib import Path
from types import SimpleNamespace
import ast
import hashlib
import inspect
import textwrap
import json
import numpy as np
from tools.hbm_accel_program_engine import compile_native

MOE_SHA='49573d415180a9ef6befd8076dfe7a2f5eea1c26363aeaf4e8f4fea573f7ec47'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def restore(manifest,config,D):
    manifest=Path(manifest);record=json.loads(manifest.read_text())
    if record.get('schema')!='opentallas.ds_hbm_dspark_connected_images.v1':
        raise ValueError('archived native source schema required; not ABI3')
    if (record['tp'],record['nsm'],record['imw'])!=(2,2,14):
        raise ValueError('actual source topology differs')
    for original,digest in record['sources'].items():
        if Path(original).name in ('v41_hbm.py','v41_dspark.py'):
            loaded=D.H.__file__ if Path(original).name=='v41_hbm.py' else D.__file__
            if sha(loaded)!=digest:raise ValueError('source generator pin mismatch')
    expected={}
    for die in range(2):
        for sm in range(2):
            name=f'prog_d{die}_s{sm}.hex';p=manifest.parent/name
            if sha(p)!=record['artifacts'][name]:raise ValueError('archived native image mismatch')
            expected[die,sm]=[int(line,16) for line in p.read_text().splitlines()]
    c=json.loads(Path(config).read_text());F=np.float32
    m=SimpleNamespace(c=c,L=c['n_layers'],dim=c['dim'],hc=c['hc_mult'],
        eps=F(c['norm_eps']),hc_eps=F(c['hc_eps']),sinkhorn_iters=c['hc_sinkhorn_iters'],
        n_exp=c['n_routed_experts'],k_exp=c['n_activated_experts'],
        dspark_n_exp=c['dspark_n_routed_experts'],dspark_k_exp=c['dspark_n_activated_experts'],
        route_scale=F(c['route_scale']),limit=F(c['swiglu_limit']),topk=c['index_topk'],
        attn_scale=F(c['head_dim']**-.5),
        index_w_scale=F(c['index_head_dim']**-.5*c['index_n_heads']**-.5),
        engram_scale=F(c['dim']**-.5))
    p=object.__new__(D.DProgram)
    p.m=m;p.a=dict(record['layout']);p.dbg=False;p.consts={};p.desc_fields={}
    a=p.a
    # Original packing allocates equal-shaped pairs. These distances are
    # archive-derived addresses, not timing or area estimates.
    p.woa_stride=(a['L0.woa1']-a['L0.woa0'])//2
    p.ex_stride=(a['L0.rexp1']-a['L0.rexp0'])//m.n_exp
    _,_,_,groups=D.H.bd_geometry(c['dim'],True)
    _,steps,_,_=D.H.bd_geometry(c['dim'],True)
    p.ex_w2off=32*groups*steps*D.H.MC.BD_LINE
    _,steps,_,groups=D.H.bd_geometry(c['dim'],False)
    p.sh_w2off=32*groups*steps*D.H.MC.BD_LINE
    p.mp_stride=(a['MAINNORM']-a['MAINPROJ'])//2
    p.head={s:a[f'HEAD{s}'] for s in range(2)}
    p.mhead={s:a[f'MHEAD{s}'] for s in range(2)}
    end=a['MHEAD1']+(a['MHEAD1']-a['MHEAD0'])
    p.CONST=(end+4095)//4096*4096
    p.CSTR=record['column_layout']['stride']
    tree=ast.parse(textwrap.dedent(inspect.getsource(D.H.Program.build_images)))
    fields=[n.value for n in ast.walk(tree) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Attribute) and t.attr=='ehash_names' for t in n.targets)]
    if len(fields)!=1:raise ValueError('source hash-field namespace differs')
    p.ehash_names=ast.literal_eval(fields[0])
    baseline=compile_native(p,D.DGen,D.KINDS,D.H.link)
    if baseline['entries']!=record['entries']:raise ValueError('restored original entry mismatch')
    for key,words in baseline['images'].items():
        if words!=expected[key]:
            at=next((i for i,(a,b) in enumerate(zip(words,expected[key])) if a!=b),min(len(words),len(expected[key])))
            raise ValueError(f'restored original native words differ at {key}/{at}; reject metadata')
    return p,baseline,record


def emit(manifest,config,D,out,*,enable=False):
    if not enable:raise ValueError('explicit compiler/source join enable required')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    try:
        p,baseline,origin=restore(manifest,config,D)
        constants=dict(p.consts);fields=dict(p.desc_fields)
        candidate=compile_native(p,D.DGen,D.KINDS,D.H.link,enable=True,moe_sha256=MOE_SHA)
        if p.consts!=constants or p.desc_fields!=fields:
            raise ValueError('candidate changed archived constant/descriptor namespace')
        images={}
        for (die,sm),words in candidate['images'].items():
            path=out/f'prog_d{die}_s{sm}.hex'
            path.write_text(''.join(f'{w:016x}\n' for w in words));images[path.name]=sha(path)
        result=dict(schema='opentallas.ha5-archived-native-candidate.v1',
            verdict='SOURCE_NATIVE_COMPILER_JOIN_PASS',origin_sha256=sha(manifest),
            config_sha256=sha(config),original_artifacts=origin['artifacts'],
            baseline_entries=baseline['entries'],candidate_entries=candidate['entries'],
            candidate_artifacts=images,registers=candidate['registers'],
            baseline_registers=baseline['registers'],
            boundaries=candidate['boundaries'],constant_vectors=len(constants),
            descriptor_fields=fields,constant_base=p.CONST,
            source_position_extent=32,column_stride=p.CSTR,
            archived_memory_changed=False,baseline_words_exact=True,
            full_shape_qualified=False,numerical_qualified=False,union_weight_reuse_qualified=False,
            measured_slot6_time_us=None,measured_overlap_us=None,adopt=False)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(error=str(error),adopt=False),indent=2)+'\n')
        raise


def enroll_loaded(pins,manifest,D,*,candidate=None,enable=False,sm_engine_factory=None):
    """Enroll Sagan's actual preloaded simulator without reset, load or tick.

    Its source factory validates and loads the immutable images. Enrollment
    retains the same ONE pins/clock owner, actual column stride/context extent,
    descriptor selectors and native expand function. It cannot switch IMEM
    inside a live owner; a candidate needs its own actually preloaded bundle.
    """
    if not enable:raise ValueError('explicit loaded-source adapter enable required')
    import types
    from tools.hbm_accel_program_engine import RTLColumnEngine
    record=json.loads(Path(manifest).read_text())
    if record.get('schema')!='opentallas.ds_hbm.simulator20_source.v1':
        raise ValueError('native simulator source schema required')
    if getattr(pins,'source',None)!=record:
        raise ValueError('actual preloaded simulator source identity differs')
    if record['position_extent']!=32 or record['full_shape']:
        raise ValueError('this archived source adapter is reduced CTX32 only')
    if candidate is not None:
        artifact=json.loads(Path(candidate).read_text())
        if record['entries']!=artifact['candidate_entries']:
            raise ValueError('actual preloaded candidate entry mismatch')
        for name,digest in artifact['candidate_artifacts'].items():
            if record['artifacts'].get(name)!=digest:
                raise ValueError('candidate was not actually loaded: '+name)
    # Same source bytecode; explicit source NOISE binding in a private globals
    # dictionary avoids mutating D.NOISE or any pinned module.
    globals_copy=dict(D.expand.__globals__,NOISE=record['noise'])
    expand=types.FunctionType(D.expand.__code__,globals_copy,D.expand.__name__,
                              D.expand.__defaults__,D.expand.__closure__)
    if sm_engine_factory is None:
        from tools.gpu_sys.ds_hbm_sm_engine20_guarded import SMEngine20Guarded
        sm_engine_factory=SMEngine20Guarded
    return RTLColumnEngine(pins,record['entries'],expand,ndie=2,nsm=2,
        position_extent=record['position_extent'],source_sha256=sha(manifest),
        swapin_positions=(*range(43),63),enable=True,
        sm_engine_factory=sm_engine_factory)


def prepare_candidate_bundle(original_manifest,candidate_result,out,*,enable=False):
    """Materialize candidate IMEM plus the SAME validated checkpoint/partition bytes.

    No simulator launch or context acquisition. Original source files are only
    read and linked; candidate files are copied into a new owned bundle. The
    existing Sagan Simulator20 factory can load this native schema directly.
    """
    if not enable:raise ValueError('explicit candidate source preparation enable required')
    import os
    import shutil
    original_manifest,candidate_result=Path(original_manifest).resolve(),Path(candidate_result).resolve()
    original=json.loads(original_manifest.read_text());candidate=json.loads(candidate_result.read_text())
    if original.get('schema')!='opentallas.ds_hbm.simulator20_source.v1':
        raise ValueError('actual native prepared source bundle required')
    if candidate['verdict']!='SOURCE_NATIVE_COMPILER_JOIN_PASS' or not candidate['baseline_words_exact']:
        raise ValueError('exact archived native compiler join required')
    if original['origin_sha256']!=candidate['origin_sha256']:
        raise ValueError('candidate was compiled against another source archive')
    if original['entries']!=candidate['baseline_entries']:
        raise ValueError('baseline native entries differ')
    origin_path=original_manifest.parent/original['origin_manifest']
    if sha(origin_path)!=original['origin_sha256']:raise ValueError('origin lineage changed')
    for name,digest in original['artifacts'].items():
        if Path(name).name!=name or sha(original_manifest.parent/name)!=digest:
            raise ValueError('immutable actual source payload differs: '+name)
    for name,digest in candidate['candidate_artifacts'].items():
        if Path(name).name!=name or sha(candidate_result.parent/name)!=digest:
            raise ValueError('candidate native words changed: '+name)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    for name in original['artifacts']:
        if name in candidate['candidate_artifacts']:
            shutil.copyfile(candidate_result.parent/name,out/name)
        else:
            os.symlink((original_manifest.parent/name).resolve(),out/name)
    # New origin records the native instruction change explicitly; every
    # checkpoint byte hash is identical to the validated original source.
    origin=json.loads(origin_path.read_text())
    origin['artifacts'].update(candidate['candidate_artifacts'])
    origin['entries']=candidate['candidate_entries']
    origin['ha5_lineage']=dict(original_sha256=candidate['origin_sha256'],
        compiler_result_sha256=sha(candidate_result),numerical_qualified=False)
    (out/'origin.json').write_text(json.dumps(origin,indent=2)+'\n')
    result=dict(original)
    result['origin_manifest']='origin.json';result['origin_sha256']=sha(out/'origin.json')
    result['entries']=candidate['candidate_entries']
    result['artifacts']=dict(original['artifacts'],**candidate['candidate_artifacts'])
    result['ha5_candidate_result_sha256']=sha(candidate_result)
    result['source_images_numerical_qualified']=False
    result['transformation']='HA5 native shared-first issue, original expert sum order; memory byte-identical'
    (out/'source.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    import argparse
    import sys
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable',action='store_true',required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parent/'gpu_sys'))
    import v41_dspark as D
    result=emit(args.manifest,args.config,D,args.out,enable=args.enable)
    print(json.dumps(dict(verdict=result['verdict'],baseline_words_exact=True,
                         candidate_artifacts=result['candidate_artifacts'],
                         numerical_qualified=False,adopt=False),indent=2))
