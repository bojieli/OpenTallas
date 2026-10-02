"""Source-bound, fail-closed released-checkpoint KV campaign. No token/decode.

Run only under reviewed committed GO and actual kernel affinity and measured host headroom.
No elapsed-time, CPU-time, FSIZE or address-space cap is installed here.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def head(root):return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
def require(ok,reason):
    if not ok:raise ValueError(reason)


def preflight(proposal, admission, go_commit, runtime=True):
    original=Path(proposal['original_source_root']);additive=Path(proposal['additive_source_root'])
    require(proposal['original_source_commit']=='870c5fe581b768df28dd2998b2d0aecc24510c23','fixed historical frame')
    require(head(original)==proposal['original_source_commit'],'original clean source commit')
    require(head(additive)==admission['additive_source_commit']==proposal['additive_source_commit'],'additive source commit')
    for root in (original,additive):require(not subprocess.check_output(['git','status','--porcelain'],cwd=root),'source root dirty')
    committed=json.loads(subprocess.check_output(['git','show',go_commit+':'+admission['admission_record_path']],cwd=additive))
    require(committed==admission and admission['admitted'] is True,'committed exact GO')
    require(admission['native_decode'] is False and admission['production_SCORES_PV_arithmetic'] is False,'operator-only GO scope')
    helpers={'qwen_kv_observation_adapter.py','qwen_kv_observation_verify.py','qwen_kv_observed_native.py','qwen_kv_reference_u8.py','qwen_kv_released_operator_gate.py','qwen_kv_campaign_prepare.py','qwen_kv_campaign_run.py','qwen_kv_campaign_launcher.py','qwen_native_terminal_replay.py'}
    require(set(proposal['additive_source_sha256'])=={str((additive/'tools'/name).resolve())for name in helpers},'complete additive source inventory')
    for file,want in proposal['additive_source_sha256'].items():require(sha(file)==want,'additive helper pin')
    archive=Path(admission['native_archive'])
    oldgo=json.loads((archive/'GO.json').read_text())
    require(proposal['original_source_sha256']==oldgo['source_sha256'] and oldgo['source_commit']==proposal['original_source_commit'],'complete original admitted frame')
    for file,want in proposal['original_source_sha256'].items():
        path=archive/Path(file).name if Path(file).is_absolute() else original/file
        require(sha(path)==want,'original admitted source pin')
    for file,want in proposal['capture_file_sha256'].items():require(sha(file)==want,'preserved capture pin')
    require(sha(archive/'native/terminal.json')==proposal['native_terminal_sha256'],'native terminal pin')
    require(sha(archive/'native/post_execution_comparisons.json')==proposal['comparison_sha256'],'independent comparison pin')
    for name,want in admission['extra_file_sha256'].items():require(sha(name)==want,'validator/index helper pin')
    require(admission['memory_reservation_bytes']==proposal['resource_model']['proposed_memory_reservation_bytes'],'priced RAM scheduling reservation')
    require(admission['FSIZE']==admission['AS']=='unlimited' and admission['wall_limit'] is None,'uncapped costly-job policy')
    if runtime:
        require(set(os.sched_getaffinity(0))==set(admission['cpus']),'exact enforced kernel affinity')
        for kind in (resource.RLIMIT_CPU,resource.RLIMIT_FSIZE,resource.RLIMIT_AS):
            require(resource.getrlimit(kind)==(resource.RLIM_INFINITY,resource.RLIM_INFINITY),'unexpected process cap')
        unit=subprocess.check_output(['systemctl','--user','show',admission['unit'],'-p','RuntimeMaxUSec','--value'],text=True).strip()
        require(unit=='infinity','actual unlimited service runtime')
    available_RAM=int(next(row.split()[1]for row in Path('/proc/meminfo').read_text().splitlines()if row.startswith('MemAvailable:')))*1024
    require(available_RAM>=admission['minimum_memavailable_bytes'],'fresh measured RAM admission')
    disk=os.statvfs(admission['output_parent']);available=disk.f_bavail*disk.f_frsize
    require(available>=admission['disk_reserve_bytes']+admission['priced_incremental_output_bytes'],'fresh disk admission')
    return dict(status='PASS_SOURCE_RESOURCE_PREFLIGHT',runtime=runtime,disk_available_bytes=available,CPU_quota_claim=False)


def run(proposal_path, admission_path, go_commit):
    proposal=json.loads(Path(proposal_path).read_text());admission=json.loads(Path(admission_path).read_text())
    require(sha(proposal_path)==admission['proposal_sha256'],'exact proposal bytes')
    out=Path(admission['output']);out.mkdir(exist_ok=False);start=time.monotonic()
    try:
        write(out/'preflight.json',preflight(proposal,admission,go_commit))
        original=Path(proposal['original_source_root']);additive=Path(proposal['additive_source_root'])
        sys.path.insert(0,str(additive/'tools'));sys.path.insert(0,str(original/'tools'))
        import importlib.metadata as metadata
        for name,want in admission['runtime_package_versions'].items():require(metadata.version(name)==want,'runtime package pin '+name)
        for path,want in admission['runtime_file_sha256'].items():require(sha(path)==want,'runtime executable/library pin')
        require(sys.version.split()[0]==admission['python_version'],'Python version pin')
        import h3_qwen_bounded_native as N
        from qwen_native_terminal_replay import replay
        from qwen_kv_reference_u8 import produce
        from qwen_kv_released_operator_gate import run as operator
        from qwen_kv_observation_verify import verify
        native=json.load(gzip.open(original/'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz','rt'))
        archive=Path(admission['native_archive']);validator=Path(admission['strict_validator'])
        write(out/'strict_input_review.json',replay(archive,additive,admission['checkpoint_index'],archive/'qualified_images.json',validator))
        spec=importlib.util.spec_from_file_location('V',validator);V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
        print(json.dumps(dict(event='PHASE_REFERENCE_START',elapsed_s=time.monotonic()-start)),flush=True)
        expected=produce(native,proposal['checkpoint_snapshot'],archive/'native',out/'reference')
        reference_pins={p.name:sha(p)for p in(out/'reference').iterdir()if p.is_file()}
        operator_admission=dict(source_file_sha256={str(p.resolve()):sha(p)for p in [original/'tools/h3_qwen_bounded_native.py',original/'tools/h3_qwen_complete_native.py',additive/'tools/qwen_kv_observation_adapter.py',additive/'tools/qwen_kv_observation_verify.py',additive/'tools/qwen_kv_released_operator_gate.py']},native_sha256=proposal['native_sha256'],reference_file_sha256=reference_pins)
        write(out/'reference_identity.json',reference_pins)
        result=operator(native,N,out/'reference',out/'observed',operator_admission,V.verify_kv_journal,enabled=True)
        # Bind freshly observed U8 to actual prior decoded read hashes, without rerunning the token.
        rows=[json.loads(x)for x in(archive/'native/native_progress.jsonl').read_text().splitlines()]
        review=verify(native,out/'observed',V.verify_kv_journal,expected,rows)
        write(out/'preserved_native_readhash_review.json',review)
        verdict=dict(status='PASS_RELEASED_CHECKPOINT_KV_OPERATOR_AND_PRIOR_READ_HASHES',GO_commit=go_commit,elapsed_s=time.monotonic()-start,operator=result,prior_read_hash_review=review,native_decode=False,production_lifecycle_qualified=False,actual_RTL=False,physical_credit=False,rate_credit=False)
    except BaseException as error:
        write(out/'terminal.json',dict(status='FAIL_INCOMPLETE_PRESERVED',error=repr(error),elapsed_s=time.monotonic()-start,native_decode=False,no_automatic_retry=True));raise
    write(out/'terminal.json',verdict);print(json.dumps(verdict),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--proposal',type=Path,required=True);p.add_argument('--admission',type=Path,required=True);p.add_argument('--go-commit',required=True)
    a=p.parse_args();run(a.proposal,a.admission,a.go_commit)
