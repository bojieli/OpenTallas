#!/usr/bin/env python3
"""Exercise existing bind-case guards, stopping before any module indexing.

Only copied metadata and private source symlinks/copies are mutated. The real
resolver main() and git/source guards run unchanged. Both parser/cache entries
after the byte guards are intercepted with a BaseException sentinel; no body
index, elaboration, compiler, or simulator can run in this check.
"""
import argparse
import hashlib
import importlib.util
import json
import pickle
import traceback
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class GuardBoundaryReached(BaseException):pass


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['tool','repo','shipping-root','top-v','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--ref',required=True)
    p.add_argument('--wrong-ref',required=True)
    a=p.parse_args()
    for name in ['tool','repo','shipping_root','top_v','out']:setattr(a,name,getattr(a,name).resolve())
    a.out.mkdir(parents=True,exist_ok=False)
    source=a.shipping_root/'src';pbpath=a.shipping_root/'bind/bind/port_bind.json';casepath=pbpath.parent/'bind_case.json'
    pb=json.loads(pbpath.read_text());case=json.loads(casepath.read_text())
    module_spec=importlib.util.spec_from_file_location('guarded_actual_dv_rtl_kit',a.tool)
    K=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(K)
    original_loader=K.load_dpb;original_loads=pickle.loads;calls=0
    def boundary(*args,**kwargs):
        nonlocal calls
        calls+=1
        raise GuardBoundaryReached('SOURCE_BYTE_GUARDS_PASSED_STOP_BEFORE_MODULE_INDEX')
    def guarded_loader(*args,**kwargs):
        D=original_loader(*args,**kwargs);D.parse_modules=boundary;return D
    K.load_dpb=guarded_loader;pickle.loads=boundary
    cases={}
    try:
        for name in ['exact_positive_guard_control','wrong_ref','missing_recorded_file','snapshot_byte_mismatch','recorded_defines_mismatch']:
            directory=a.out/name;fixture=directory/'snapshot/src';fixture.mkdir(parents=True)
            def remap(value):
                if isinstance(value,str) and value.startswith(str(source)+'/'):
                    return str(fixture/value[len(str(source))+1:])
                return value
            local_pb=dict(pb);local_pb['rtl_roots']=[remap(x) for x in pb['rtl_roots']]
            local_pb['rtl_files']=[remap(x) for x in pb['rtl_files']]
            local_case=dict(case);local_case['port_bind_cmd']=[remap(x) for x in case['port_bind_cmd']]
            required=[source/'tools/die_port_bind.py']+[Path(x) for x in pb['rtl_files'] if str(x).startswith(str(source)+'/')]
            for original in required:
                target=fixture/original.relative_to(source)
                if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(original)
            memory=fixture/'rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv'
            assert memory.is_symlink()
            mutation={}
            if name=='missing_recorded_file':memory.unlink();mutation=dict(path=str(memory),operation='unlink private symlink only')
            if name=='snapshot_byte_mismatch':
                payload=memory.read_bytes();memory.unlink();memory.write_bytes(payload+b'\n// guard negative: changed private snapshot byte identity\n')
                mutation=dict(path=str(memory),original_sha256=hashlib.sha256(payload).hexdigest(),mutant_sha256=sha(memory))
            if name=='recorded_defines_mismatch':
                local_pb['defines']=pb['defines']+['BIND_GUARD_MUTANT_DEFINE']
                mutation=dict(original=pb['defines'],mutant=local_pb['defines'])
            pp=directory/'port_bind.json';cp=directory/'bind_case.json'
            pp.write_text(json.dumps(local_pb,indent=1)+'\n');cp.write_text(json.dumps(local_case,indent=1)+'\n')
            argv=['--repo',str(a.repo),'--ref',a.wrong_ref if name=='wrong_ref' else a.ref,
                '--port-bind',str(pp),'--bind-case',str(cp),'--top-v',str(a.top_v),
                '--top','s0N_aggregate','--out',str(directory/'unexecuted_kit'),
                '--prefer-list','tools/s81_dv/frame_bench.f','--prefer-list','tools/s81_dv/svc_rs/rs_files.sh']
            before=calls;error=None;phase=False
            try:
                K.main(argv)
                error='UNEXPECTED_MAIN_RETURN'
            except GuardBoundaryReached as e:phase=True;error=str(e)
            except BaseException as e:
                error=''.join(traceback.format_exception(type(e),e,e.__traceback__))
            expected_phase=name=='exact_positive_guard_control'
            passed=phase==expected_phase and (phase or 'UNEXPECTED_MAIN_RETURN'!=error)
            if name=='missing_recorded_file':passed &= 'FileNotFoundError' in error
            if name=='snapshot_byte_mismatch':passed &= 'recorded bind input differs from immutable ref' in error
            if name=='recorded_defines_mismatch':passed &= 'AssertionError' in error
            if name=='wrong_ref':passed &= any(x in error for x in ['recorded bind input absent at source ref','recorded bind input differs from immutable ref'])
            log=directory/'raw_guard.log';log.write_text(error+'\n')
            cases[name]=dict(passed=bool(passed),argv=['python3',str(a.tool)]+argv,
                mutation=mutation,source_guard_boundary_reached=phase,post_guard_boundary_calls=calls-before,
                module_bodies_indexed=0,compiler_or_simulator_invoked=False,
                metadata_sha256=dict(port_bind=sha(pp),bind_case=sha(cp)),raw_guard_log_sha256=sha(log),exception=error)
    finally:pickle.loads=original_loads;K.load_dpb=original_loader
    result=dict(schema='opentallas.s81.executed_bind_pure_guards.v1',status='PASS' if all(c['passed'] for c in cases.values()) else 'FAIL',
        resolver_sha256=sha(a.tool),source_ref=a.ref,wrong_ref=a.wrong_ref,original_port_bind_sha256=sha(pbpath),
        original_bind_case_sha256=sha(casepath),cases=cases,guards_modified=False,
        interception='only post-byte-guard pickle.loads and D.parse_modules; BaseException stops even cached path before indexing',
        compiler_or_simulator_invoked=False,source_snapshots_modified=False)
    (a.out/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],{n:c['passed'] for n,c in cases.items()})
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
