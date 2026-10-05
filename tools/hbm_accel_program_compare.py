"""Actual source-bound layer field readback, then sequential RTL comparison.

No CPU oracle, inference, expected-output injection or build. The predecessor
must complete and release its actual process owner before any backend launch.
Default off. Existing M-only backend supports complete field readback; router
and BD activation probes require Sagan's separate H-capable successor.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
from tools.hbm_accel_program_backend import digest,guarded_factory,validate_native
from tools.hbm_accel_program_engine import RTLColumnEngine
from tools.hbm_accel_column_probes import SectorReadbackPins
from tools.hbm_accel_column_source import ColumnSource,REGIONS


def read_json(path):return json.loads(Path(path).read_text())


def predecessor_released(root,expected_source_sha256):
    """Require the original terminal record and actual drained owner departure."""
    root=Path(root)
    result_path=root/'run/result.json';exit_path=root/'exit.rc'
    if not result_path.exists() or not exit_path.exists():
        raise RuntimeError('original numerical owner has no authoritative terminal')
    result=read_json(result_path);owner=read_json(root/'run/backend/owner.json')
    if int(exit_path.read_text())!=0 or result.get('verdict')!='COMPLETED_SOURCE_NATIVE_TOKEN':
        raise RuntimeError('original numerical owner did not complete successfully')
    if result['source_manifest_sha256']!=expected_source_sha256 or owner['source_manifest_sha256']!=expected_source_sha256:
        raise RuntimeError('original source identity differs')
    final=result['final']
    if final['sys_fault'] or not final['rst_sm_n'] or any(s['busy'] for s in final['sms']) or any(d['cpl_v'] for d in final['dies']):
        raise RuntimeError('actual original context remains undrained')
    # This contract is checked on the owning host, never against an unrelated
    # local PID namespace. No kill/reset/lease release is performed here.
    if Path('/proc',str(owner['pid'])).exists():
        raise RuntimeError('original simulator process still owns source context')
    return dict(terminal_sha256=digest(result_path),owner_sha256=digest(root/'run/backend/owner.json'),
                exit_code=0,simulator_pid=owner['pid'],scope='same owning host; closed drained predecessor')


def admit_source(path):
    path=Path(path).resolve();source=read_json(path)
    if source.get('schema')!='opentallas.ds_hbm.simulator20_source.v1' or source['full_shape'] or source['position_extent']!=32:
        raise ValueError('admitted actual reduced native source required')
    topology=dict(dies=2,sms_per_die=2,partitions_per_die=2,sector_words=2097152)
    if source['topology']!=topology:raise ValueError('source geometry differs')
    origin_path=path.parent/source['origin_manifest']
    if digest(origin_path)!=source['origin_sha256']:raise ValueError('native source lineage differs')
    origin=read_json(origin_path)
    for name,sha in source['artifacts'].items():
        if Path(name).name!=name or digest(path.parent/name)!=sha:
            raise ValueError('actual source artifact changed: '+name)
    for name,sha in origin['artifacts'].items():
        if source['artifacts'].get(name)!=sha:raise ValueError('origin payload changed: '+name)
    images={(d,s):[int(word,16) for word in (path.parent/f'prog_d{d}_s{s}.hex').read_text().splitlines()]
            for d in range(2) for s in range(2)}
    validate_native(images,source['entries'])
    return source,origin,images


def program_view(source,origin,witness,config):
    """Restore only the already admitted descriptor/layout readback namespace.

    No compiler/golden rerun: fields and strides were admitted by the saved
    cold native-word join. Do not reinterpret attention SEL as routed experts.
    """
    if not witness['baseline_words_exact'] or witness['verdict']!='SOURCE_NATIVE_COMPILER_JOIN_PASS':
        raise ValueError('saved cold native source-word admission required')
    if digest(config)!=witness['config_sha256']:raise ValueError('source config changed')
    original_sha=origin.get('ha5_lineage',{}).get('original_sha256',source['origin_sha256'])
    if original_sha!=witness['origin_sha256']:raise ValueError('saved native witness has another source')
    c=read_json(config);a=dict(source['layout'])
    if a!=origin['layout'] or origin['column_layout']['stride']!=witness['column_stride']:
        raise ValueError('actual source column layout differs')
    return SimpleNamespace(a=a,CSTR=witness['column_stride'],desc_fields=dict(witness['descriptor_fields']),
        ex_stride=(a['L0.rexp1']-a['L0.rexp0'])//c['n_routed_experts'],
        ex_w2off=32*5*288,sh_w2off=32*5*288,
        m=SimpleNamespace(dim=c['dim'],L=c['n_layers'],k_exp=c['n_activated_experts'],n_exp=c['n_routed_experts']))


def same_memory(baseline,candidate):
    for key in ('layout','position_extent','topology','prompt','noise'):
        if baseline[key]!=candidate[key]:raise ValueError('baseline/candidate source field differs: '+key)
    names={n for n in baseline['artifacts'] if n.startswith(('die','mem_'))}
    if names!={n for n in candidate['artifacts'] if n.startswith(('die','mem_'))}:
        raise ValueError('actual memory artifact census differs')
    if any(baseline['artifacts'][n]!=candidate['artifacts'][n] for n in names):
        raise ValueError('baseline/candidate checkpoint memory differs')
    return {n:baseline['artifacts'][n] for n in sorted(names)}


def cold_fields(pins,path,source):
    """Confirm actual loaded memory against immutable source INPUT bytes."""
    a=source['layout'];fields={n:(a[n],size) for n,(_,size) in REGIONS.items() if n in a}
    fields['COLUMN0']=(a['COL'],4736)
    before=pins.snapshot();records=[]
    for die in range(2):
        with (Path(path).parent/f'die{die}.bin').open('rb') as stream:
            for name,(address,size) in fields.items():
                stream.seek(address);expected=stream.read(size)
                actual=pins.read_bytes(die,address,size,mem_words=2097152)
                if actual!=expected:raise RuntimeError(f'actual source preload differs: {die}/{name}')
                records.append(dict(die=die,field=name,address=address,bytes=size,
                                    sha256=hashlib.sha256(actual).hexdigest()))
    if pins.snapshot()!=before:raise RuntimeError('input readback advanced evaluated RTL')
    return records


def run_layer(path,source,images,program,*,build,callback_source,out,enable=False,phase_markers=None):
    if not enable:raise ValueError('explicit actual RTL field-run enable required')
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parent/'gpu_sys'))
    import v41_dspark as D
    from tools.hbm_accel_program_source import enroll_loaded
    out=Path(out);out.mkdir(parents=True,exist_ok=False);build=Path(build)
    binary=build/'obj/Vha5_cp20_runtime'
    terminal=read_json(build/'terminal.json')
    if terminal['exit_code']!=0 or digest(binary)!=terminal['binary_sha256']:
        raise ValueError('existing actual compiled backend terminal pin required')
    pin_class=SectorReadbackPins
    if phase_markers is not None:
        from tools.hbm_accel_column_probes import ColumnProbePins
        build_record=read_json(build/'build_manifest.json')
        if not build_record.get('source_probes'):
            raise ValueError('existing M-only binary cannot supply H shared/router/BD probes')
        pin_class=ColumnProbePins
    pins=pin_class(binary,image_prefix=Path(path).parent/'mem',log=out/'backend.log',enable=True)
    # Retain a failed live owner on any exception. No fake release/reset/retry.
    record=dict(source_manifest_sha256=digest(path),binary_sha256=digest(binary),pid=pins.process.pid)
    (out/'owner.json').write_text(json.dumps(record,indent=2)+'\n')
    try:
        pins.boot();pins.load_native(images);pins.source=source
        source_inputs=cold_fields(pins,path,source)
        engine=enroll_loaded(pins,path,D,enable=True,sm_engine_factory=guarded_factory(callback_source))
        join=ColumnSource(engine,program,source_sha256=digest(path),mem_words=2097152,enable=True)
        if phase_markers is not None:
            markers=read_json(phase_markers)
            if markers.get('entries',markers.get('candidate_entries'))!=source['entries']:
                raise ValueError('phase markers belong to another loaded native program')
            marker_images=markers.get('image_artifacts',markers.get('candidate_artifacts'))
            if not isinstance(marker_images,dict) or len(marker_images)!=4:
                raise ValueError('phase marker native image pins required')
            for name,sha in marker_images.items():
                if source['artifacts'].get(name)!=sha:
                    raise ValueError('phase markers do not describe actual loaded native words')
            join.attach(dict(entries=source['entries'],images=images,boundaries=markers['boundaries']))
        command=dict(op='VLAYER',idx=0,ncol=1,pos=0,toks=[source['prompt'][0]],job=1,generation=1)
        started=pins.snapshot();engine.run(command);ended=pins.snapshot()
        column=join.capture_column(0,engine.receipts[-1])
        # CTR in the column slot is reserved, unlike the actual working CTR.
        working=[]
        for die in range(2):
            values={n:pins.read_bytes(die,program.a[n],size,mem_words=2097152)
                    for n,(_,size) in REGIONS.items() if n in program.a}
            working.append(values)
        if pins.snapshot()!=ended:raise RuntimeError('field capture advanced actual clock')
        fields=out/'fields';fields.mkdir()
        for die,values in enumerate(column['values']):
            for name,payload in values.items():(fields/f'column_d{die}_{name}.bin').write_bytes(payload)
        for die,values in enumerate(working):
            for name,payload in values.items():(fields/f'working_d{die}_{name}.bin').write_bytes(payload)
        manifest={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in fields.iterdir()}
        final=pins.snapshot()
        if final['sys_fault'] or any(d['cpl_v'] or not d['db_rdy'] for d in final['dies']):
            raise RuntimeError('actual field run has live command/completion debt')
        pins.close()
        result=dict(verdict='COMPLETED_REDUCED_SOURCE_LAYER_FIELD_READBACK',**record,
            source_inputs=source_inputs,command=command,receipts=engine.receipts,fields=manifest,
            actual_context_edges=ended['cycle']-started['cycle'],
            actual_context_time_ps=ended['time_ps']-started['time_ps'],
            column_ctr_scope=column['CTR_scope'],router_ids_scope='actual H shared source only; attention SEL never routed IDs',
            router_probe_available=phase_markers is not None,
            numerical_oracle='other actual RTL run only',full_shape_qualified=False,
            measured_slot6_time_us=None,measured_overlap_us=None,adopt=False)
        if phase_markers is not None:
            # Lossless actual bit records; no numeric interpretation/oracle.
            def bits(value):
                if isinstance(value,bytes):return dict(bytes=len(value),hex=value.hex())
                if isinstance(value,dict):return {k:bits(v) for k,v in value.items()}
                if isinstance(value,(list,tuple)):return [bits(v) for v in value]
                return value
            (out/'source_movements.json').write_text(json.dumps(bits(join.movements),indent=2)+'\n')
            result['source_movement_time_scope']='stable source readback; no accepted issue/retire or overlap claim'
            result['source_movement_records']=len(join.movements)
            result['source_movement_sha256']=digest(out/'source_movements.json')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(error=str(error),**record,
            actual=pins.snapshot(),adopt=False),indent=2)+'\n')
        raise


def compare_fields(baseline_out,candidate_out):
    baseline_out,candidate_out=Path(baseline_out),Path(candidate_out)
    a,b=read_json(baseline_out/'result.json'),read_json(candidate_out/'result.json')
    if a['command']!=b['command'] or a['source_inputs']!=b['source_inputs']:
        raise ValueError('actual source-bound command/input identity differs')
    if set(a['fields'])!=set(b['fields']):raise ValueError('field census differs')
    mismatches=[]
    for name in sorted(a['fields']):
        left=(baseline_out/'fields'/name).read_bytes();right=(candidate_out/'fields'/name).read_bytes()
        if len(left)!=a['fields'][name]['bytes'] or digest(baseline_out/'fields'/name)!=a['fields'][name]['sha256']:
            raise ValueError('baseline field evidence changed')
        if len(right)!=b['fields'][name]['bytes'] or digest(candidate_out/'fields'/name)!=b['fields'][name]['sha256']:
            raise ValueError('candidate field evidence changed')
        if left!=right:
            first=next((i for i,(x,y) in enumerate(zip(left,right)) if x!=y),min(len(left),len(right)))
            mismatches.append(dict(field=name,first_byte=first))
    slower=b['actual_context_time_ps']>a['actual_context_time_ps']
    return dict(verdict='REJECTED_FIELD_MISMATCH' if mismatches else
                'REJECTED_SLOWER_ACTUAL_LAYER' if slower else 'REDUCED_LAYER_FIELDS_EXACT',
                mismatches=mismatches,baseline_context_edges=a['actual_context_edges'],
                candidate_context_edges=b['actual_context_edges'],
                baseline_context_time_ps=a['actual_context_time_ps'],candidate_context_time_ps=b['actual_context_time_ps'],
                measured_scope='one complete native source layer with SWAPIN/EMBED/LAYER/SWAPOUT; original behavioral memory/CDC/refresh',
                full_shape_qualified=False,composed_gain_us=None,measured_overlap_us=None,adopt=False)


def original_release(host,root,source_sha):
    """Read the actual predecessor host; never infer release from a local PID."""
    import inspect
    import subprocess
    if host not in ('ot-epyc1tb','ot-pve1','ot-agidock128'):
        raise ValueError('explicit owning fleet host required')
    script='from pathlib import Path\nimport hashlib,json\n'
    for fn in (read_json,digest,predecessor_released):script+=inspect.getsource(fn)+'\n'
    script+='print(json.dumps(predecessor_released('+repr(str(root))+','+repr(source_sha)+')))\n'
    response=subprocess.run(['ssh',host,'python3','-'],input=script,text=True,capture_output=True)
    if response.returncode:
        raise RuntimeError('original source owner remains held: '+response.stderr.strip())
    return dict(json.loads(response.stdout),owning_host=host)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--enable',action='store_true',required=True)
    p.add_argument('--stage',choices=('baseline','candidate'),required=True)
    p.add_argument('--baseline-source',type=Path,required=True)
    p.add_argument('--candidate-source',type=Path)
    p.add_argument('--candidate-result',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--backend-build',type=Path,required=True)
    p.add_argument('--callback-source',type=Path,required=True)
    p.add_argument('--predecessor-host',required=True)
    p.add_argument('--predecessor-root',type=Path,required=True)
    p.add_argument('--baseline-out',type=Path)
    p.add_argument('--phase-markers',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    # Before any launch, load, tick or output directory mutation.
    release=original_release(a.predecessor_host,a.predecessor_root,digest(a.baseline_source))
    baseline,origin,images=admit_source(a.baseline_source)
    witness=read_json(a.candidate_result)
    if a.stage=='baseline':
        if baseline['origin_sha256']!=witness['origin_sha256']:
            raise ValueError('baseline has another archived native source')
        for name,sha in witness['original_artifacts'].items():
            if baseline['artifacts'].get(name)!=sha:raise ValueError('baseline is not the admitted original')
        program=program_view(baseline,origin,witness,a.config)
        result=run_layer(a.baseline_source,baseline,images,program,build=a.backend_build,
                         callback_source=a.callback_source,out=a.out,enable=a.enable,phase_markers=a.phase_markers)
    else:
        if a.candidate_source is None or a.baseline_out is None:
            raise ValueError('actual baseline field readback and candidate source required')
        original=read_json(a.baseline_out/'result.json')
        if original['verdict']!='COMPLETED_REDUCED_SOURCE_LAYER_FIELD_READBACK' or original['source_manifest_sha256']!=digest(a.baseline_source):
            raise ValueError('actual matching baseline terminal field evidence required')
        candidate,origin,images=admit_source(a.candidate_source)
        memory=same_memory(baseline,candidate)
        if candidate['entries']!=witness['candidate_entries']:
            raise ValueError('candidate actual native entries differ')
        for name,sha in witness['candidate_artifacts'].items():
            if candidate['artifacts'].get(name)!=sha:raise ValueError('candidate actual native words differ')
        program=program_view(candidate,origin,witness,a.config)
        result=run_layer(a.candidate_source,candidate,images,program,build=a.backend_build,
                         callback_source=a.callback_source,out=a.out,enable=a.enable,phase_markers=a.phase_markers)
        verdict=compare_fields(a.baseline_out,a.out)
        verdict.update(predecessor_release=release,unchanged_source_memory=memory)
        (a.out/'comparison.json').write_text(json.dumps(verdict,indent=2)+'\n')
        result=verdict
    print(json.dumps(result,indent=2))
