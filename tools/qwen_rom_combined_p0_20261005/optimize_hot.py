#!/usr/bin/env python3
"""Recompile one measured hot native C++ TU; retain every RTL/model/leaf source.

No Verilator, model regeneration, all-object rebuild or live archive mutation.
The candidate uses the previous passing PATCH prefix as its exact baseline;
only the changed compiler vehicle executes, once, under the existing guard.
"""
import argparse,hashlib,json,os,re,shlex,shutil,subprocess,threading,time
from pathlib import Path
from run_full import fresh,observe,stage


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plan(parent,out):
    out.mkdir();(out/'src').mkdir()
    die=parent/'die';src=die/'Vdie___024root__220.cpp';old=die/'Vdie__ALL.a'
    commands=[shlex.split(l) for l in (parent/'compile.log').read_text().splitlines()
              if l.startswith('g++-15 ') and l.endswith('-c '+src.name)]
    if len(commands)!=1:raise ValueError('exact actual hot TU compile command missing')
    before=commands[0];after=list(before)
    opts=[x for x in before if re.fullmatch('-O[0-3sg]',x)]
    if opts!=['-Os']:raise ValueError('actual hot optimization differs from checked -Os')
    after[after.index('-Os')]='-O3'
    # Existing size-optimized PCH cannot be consumed as a speed-optimized PCH.
    # Parse the identical generated header; no PCH/model is regenerated.
    after[after.index('Vdie__pch.h.fast')]='Vdie__pch.h'
    after[after.index('-c')+1]=str(src)
    obj=out/(src.stem+'.o');after+=['-fno-fast-math','-ffp-contract=off','-o',str(obj)]
    gate=parent/'native_gate_02b0256ee'
    link=json.loads((gate/'commands.json').read_text())
    link['link']=[str(out/'Vdie__ALL.a') if x==str(old) else str(out/'gate_test') if x==str(gate/'gate_test') else x for x in link['link']]
    link['binary']=str(out/'gate_test')
    record=dict(status='PREPARED_NOT_COMPILED',parent=str(parent),old_archive=str(old),old_archive_sha256=sha(old),
        hot_source=str(src),hot_source_sha256=sha(src),hot_source_bytes=src.stat().st_size,
        original_command=before,candidate_command=after,cwd=str(die),object=str(obj),archive=str(out/'Vdie__ALL.a'),
        baseline_gate=str(gate),commands=link,source_identical=True,model_regenerated=False,leaf_archives_rebuilt=False,
        estimated_compile_GiB=16,estimate_not_AS_cap=True,required_compile_CPUs=1,required_runtime_CPUs=16,
        compiler_peak='measure actual runner/descendant RSS; no priorpeak claim or guessed perprocess cap',
        adopted=False,full_token_pass=False,physical_qualified=False)
    (out/'plan.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ['hot_source','hot_source_bytes','hot_source_sha256','old_archive_sha256','estimated_compile_GiB']}))


def child(a):
    out=a.output;r=json.loads((out/'plan.json').read_text())
    fresh(out,a.phase,1 if a.phase=='compile' else 16)
    stop=threading.Event();t=threading.Thread(target=observe,args=(out,a.phase,stop));t.start()
    try:
        if a.phase=='compile':
            if sha(r['hot_source'])!=r['hot_source_sha256'] or sha(r['old_archive'])!=r['old_archive_sha256']:
                raise RuntimeError('immutable input changed')
            (out/'hot_compile_command.json').write_text(json.dumps(r['candidate_command'],indent=2)+'\n')
            (out/'tmp').mkdir()
            compile_env=os.environ.copy();compile_env['TMPDIR']=str(out/'tmp')
            with (out/'hot_compile.log').open('x') as log:
                rc=subprocess.run(r['candidate_command'],cwd=r['cwd'],env=compile_env,stdout=log,stderr=subprocess.STDOUT).returncode
            (out/'hot_compile.exit').write_text(str(rc)+'\n')
            if rc:raise RuntimeError('hot CXX failed; preserve original')
            # Replacement in a NEW full archive; all other members remain byte-identical.
            shutil.copyfile(r['old_archive'],r['archive'])
            stage(out,'archive_replace',['ar','rcs',r['archive'],r['object']])
            stage(out,'driver_link',r['commands']['link'])
            (out/'archive_sha256.txt').write_text(sha(r['archive'])+'\n')
        else:
            cmd=[r['commands']['binary'],*r['commands']['runtime_args']]
            cmd[cmd.index(r['commands']['old_run'])]=str(out/'candidate')
            (out/'candidate').mkdir()
            env=os.environ.copy();env.update(RT_THREADS='16',RT_PROGRESS='128',QWEN_P0_NATIVE_PROFILE='1',QWEN_P0_NATIVE_DIRTY='1',QWEN_P0_NATIVE_REENTRY_SKIP='1')
            with (out/'candidate.log').open('x') as log:
                p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
                (out/'candidate_pid.json').write_text(json.dumps(dict(pid=p.pid,time=time.time())))
                rc=p.wait()
            (out/'candidate.exit').write_text(str(rc)+'\n')
            if rc:raise RuntimeError('changed compiler prefix failed')
            baseline=Path(r['baseline_gate'])
            old=(baseline/'patch/events.txt').read_bytes();new=(out/'candidate/events.txt').read_bytes()
            lines=[re.findall(r'P0_NATIVE_GATE terminal .*',x)[-1] for x in [(baseline/'patch.log').read_text(),(out/'candidate.log').read_text()]]
            kv=[re.search('kv_hash=(\\w+)',l).group(1) for l in lines]
            walls=[float(re.search(r'wall=([\d.]+)',l).group(1)) for l in lines]
            exact=old==new and kv[0]==kv[1]
            result=dict(status='PASS_COMPILER_EQUIVALENCE' if exact else 'FAIL_COMPILER_EQUIVALENCE',
                baseline_reused_not_replayed=True,source_sha256=r['hot_source_sha256'],old_archive_sha256=r['old_archive_sha256'],new_archive_sha256=sha(r['archive']),
                traces_sha256=[hashlib.sha256(x).hexdigest() for x in [old,new]],kv_hash=kv,terminal=lines,wall_seconds=walls,
                measured_speedup=walls[0]/walls[1],adopted=exact and walls[1]<walls[0],full_token_pass=False,physical_qualified=False)
            (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
            if not exact:raise RuntimeError('compiler changed trace/KV; no adoption')
    finally:stop.set();t.join()


def dispatch(a):
    for phase,cpus in [('compile',1),('gate',16)]:
        while True:
            try:fresh(a.output,phase+'_pre',cpus);break
            except RuntimeError:print('WAIT_CPU '+phase,flush=True);time.sleep(20)
        cmd=['/srv/opentallas-scratch/admit.sh','16','--','python3',__file__,'--output',str(a.output),'--phase',phase]
        with (a.output/(phase+'_supervisor.log')).open('x') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
        (a.output/(phase+'_supervisor.exit')).write_text(str(rc)+'\n')
        if rc:raise RuntimeError(phase+' failed; no automaticreplay')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--parent',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--phase',choices=['prepare','dispatch','compile','gate'],required=True);a=p.parse_args()
    if a.phase=='prepare':plan(a.parent,a.output)
    else:
        try:dispatch(a) if a.phase=='dispatch' else child(a)
        except Exception as e:
            (a.output/(a.phase+'_terminal.json')).write_text(json.dumps(dict(status='FAIL_'+a.phase.upper(),reason=str(e)))+'\n');raise
