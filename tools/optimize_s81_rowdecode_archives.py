#!/usr/bin/env python3
"""One strict-O2 minimum archive build; no Verilator/frontend/HDL execution."""
import argparse,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path
FLAGS='-O2 -fno-fast-math -ffp-contract=off -fno-associative-math -fno-unsafe-math-optimizations'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    a=argparse.ArgumentParser();a.add_argument('--corrected-root',type=Path,required=True);a.add_argument('--output-root',type=Path,required=True);args=a.parse_args()
    if socket.gethostname()!='vm-xry57mhfyn':raise ValueError('admitted AGI128 host required; no local compile')
    prior=json.loads((args.corrected_root/'receipt.json').read_text())
    if prior['status']!='ARCHIVES_READY_NO_RUNTIME_OR_QUALIFICATION' or prior['source_fix']!='be155754b5edbf51b780c0db1afcee0f949d6580':raise ValueError('corrected terminal archive source required')
    if args.output_root.exists():raise ValueError('unique fresh O2 object root required; no retry/overwrite')
    args.output_root.mkdir(parents=True)
    record={'status':'RUNNING','pid':os.getpid(),'source_fix':prior['source_fix'],'compiler_policy':FLAGS,'threads':2,'parts':[],
       'frontend_or_RTL_regenerated':False,'simulation':False,'host_relink':False,'retries':0,'old_archives_preserved':True}
    rp=args.output_root/'receipt.json'
    def save():rp.write_text(json.dumps(record,indent=2)+'\n')
    save()
    try:
        for part in ('pq','pb'):
            prefix='V'+part;old=args.corrected_root/part;dest=args.output_root/part
            # All compiler outputs are omitted. Every object in this successor
            # is unique and compiled under the same strict-O2 policy.
            shutil.copytree(old,dest,ignore=shutil.ignore_patterns('*.o','*.a','*.gch','*.d'))
            header=sha(old/(prefix+'.h'))
            cpp_before={p.name:sha(p) for p in dest.glob('*.cpp')}
            cmd=['make','-C',str(dest.resolve()),'-f',prefix+'.mk','-j','2','CXX=g++-11',
                 'OPT_FAST='+FLAGS,'OPT_SLOW='+FLAGS,'OPT_GLOBAL='+FLAGS]
            entry={'part':part,'command':cmd,'started_ns':time.time_ns(),'input_archive_sha256':sha(old/('lib'+prefix+'.a'))}
            record['parts'].append(entry);save()
            log=args.output_root/(part+'_make.log')
            with log.open('x') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
            entry['exit_code']=rc;save()
            if rc:raise RuntimeError(f'{part} make exit{rc}; preserve firstfailure')
            commands=[s for s in log.read_text().splitlines() if s.startswith('g++-11 ') and (' -c ' in s or ' -o ' in s)]
            if not commands:raise ValueError('actual compilation command evidence absent')
            for command in commands:
                for flag in FLAGS.split():
                    if flag not in command.split():raise ValueError('strict compiler flag absent')
                tokens=command.split()
                if any(t in tokens for t in ['-O0','-O1','-O3','-Os','-Ofast','-ffast-math','-fassociative-math','-funsafe-math-optimizations','-ffp-contract=fast']):raise ValueError('unsafe/unselected compiler flags')
            if sha(dest/(prefix+'.h'))!=header:raise ValueError('public header changed')
            for name,digest in cpp_before.items():
                if sha(dest/name)!=digest:raise ValueError('corrected generated CXX source changed')
            entry.update(status='STRICT_O2_BUILD_PASS',completed_ns=time.time_ns(),archive=str(dest/('lib'+prefix+'.a')),
                 archive_sha256=sha(dest/('lib'+prefix+'.a')),public_header_sha256=header,
                 actual_compilation_commands=len(commands),original_generated_CXX_unchanged=True)
            save()
        record['status']='STRICT_O2_ARCHIVES_READY_NO_RUNTIME_OR_QUALIFICATION'
    except BaseException as exc:
        record.update(status='FAIL_PRESERVED',exception=repr(exc));save();raise
    finally:save()
if __name__=='__main__':main()
