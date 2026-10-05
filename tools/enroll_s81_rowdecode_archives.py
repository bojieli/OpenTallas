#!/usr/bin/env python3
"""Only Vpq/Vpb source-affected closure; no simulation, factory edit or host link."""
import argparse,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECORD=ROOT/'results/rtl/s81_rowdecode_enrollment_20261004'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd,cwd,log):
    with log.open('x') as f:rc=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT).returncode
    if rc:raise RuntimeError(f'exit{rc}; preserve {log}')
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline-root',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--admission',type=Path);a=p.parse_args()
    plan=json.loads((RECORD/'plan.json').read_text())
    if a.output_root.exists():raise ValueError('fresh successor required; no overwrite/retry')
    if a.execute:
        if socket.gethostname()==plan['forbidden_local_hostname']:raise ValueError('local heavy work prohibited')
        if not a.admission:raise ValueError('actual fleet admission required')
        admitted=json.loads(a.admission.read_text())
        if admitted.get('task')!='s81-rowdecode-enrollment' or admitted.get('host')!=socket.gethostname() or admitted.get('approved') is not True or admitted.get('threads',0)<2:
            raise ValueError('source-specific CPU/headroom admission absent')
    a.output_root.mkdir(parents=True);src=a.output_root/'source';src.mkdir()
    for e in plan['sources']:
        archive=RECORD/'source_inputs'/e['path'];target=src/e['path']
        if sha(archive)!=e['sha256']:raise ValueError('source package changed')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(archive,target)
    commands=[]
    for part in ['pq','pb']:
        cmd=json.loads((RECORD/(part+'_original_command.json')).read_text())['command'].copy()
        out=a.output_root/part;prefix='V'+part
        cmd[cmd.index('--Mdir')+1]=str(out.resolve());cmd[cmd.index('--build-jobs')+1]='2';cmd.remove('--build')
        commands.append({'part':part,'prefix':prefix,'generate':cmd,'make':['make','-C',str(out.resolve()),'-f',prefix+'.mk','-j','2','CXX=g++-11']})
    (a.output_root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    if not a.execute:print('SOURCE_STAGED_NO_BUILD',a.output_root);return
    receipt={'status':'RUNNING','pid':os.getpid(),'host':socket.gethostname(),'source_fix':plan['fix_commit'],'parts':[],
             'simulation':False,'host_relink':False,'unaffected_models_reused':True,'retries':0}
    rp=a.output_root/'receipt.json'
    def save():rp.write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    try:
        version=subprocess.check_output([commands[0]['generate'][0],'--version'],text=True).strip()
        compiler=subprocess.check_output(['g++-11','--version'],text=True).splitlines()[0]
        if '5.050' not in version or '11.4.0' not in compiler:raise ValueError('selected Verilator/GCC ABI version changed')
        receipt.update(verilator_version=version,compiler_version=compiler)
        for c in commands:
            part=c['part'];prefix=c['prefix'];old=a.baseline_root/part;out=a.output_root/part
            for name in [prefix+'.h','lib'+prefix+'.a',prefix+'.mk']:
                if not (old/name).is_file():raise ValueError('completed baseline model absent')
            entry={'part':part,'old_archive_sha256':sha(old/('lib'+prefix+'.a')),'started_ns':time.time_ns()}
            receipt['parts'].append(entry);save();shutil.copytree(old,out,copy_function=shutil.copy2)
            before={p.relative_to(out):(sha(p),p.stat().st_mtime_ns,p.stat().st_atime_ns) for p in out.iterdir() if p.suffix in ['.cpp','.h','.mk']}
            run(c['generate'],src,a.output_root/(part+'_generate.log'))
            changed=[]
            for rel,(digest,mtime,atime) in before.items():
                target=out/rel
                if target.exists() and sha(target)==digest:os.utime(target,ns=(atime,mtime))
                else:changed.append(str(rel))
            if sha(out/(prefix+'.h'))!=sha(old/(prefix+'.h')):raise ValueError('public model interface changed')
            for dep in out.glob('*.d'):
                text=dep.read_text();rebased=text.replace(str(old.resolve())+'/',str(out.resolve())+'/')
                if rebased!=text:dep.write_text(rebased)
            entry.update(generated_changed_files=changed,public_header_sha256=sha(out/(prefix+'.h')));save()
            run(c['make'],src,a.output_root/(part+'_make.log'))
            entry.update(status='BUILD_PASS',completed_ns=time.time_ns(),new_archive_sha256=sha(out/('lib'+prefix+'.a')),archive=str(out/('lib'+prefix+'.a')));save()
        receipt['status']='ARCHIVES_READY_NO_RUNTIME_OR_QUALIFICATION'
    except BaseException as exc:
        receipt.update(status='FAIL_PRESERVED',exception=repr(exc));save();raise
    finally:save()
if __name__=='__main__':main()
