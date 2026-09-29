#!/usr/bin/env python3
"""Run emitted bounded Qwen runtime composition; G4 is the qualified size.

G64 controller-only resource probe is allowed. Full G64 requires a separately
qualified reference build; this tool deliberately rejects a fresh flat G64
reference compilation rather than repeating its known memory failure.
"""
import argparse,hashlib,json,pathlib,resource,subprocess,time,re
ap=argparse.ArgumentParser()
ap.add_argument('--workdir',type=pathlib.Path,required=True)
ap.add_argument('--controller-only',action='store_true')
ap.add_argument('--verilator',default='verilator')
ap.add_argument('--scale-wcs-base',type=int,choices=(0,1),default=0)
args=ap.parse_args();out=args.workdir.resolve()
parameters=json.loads((out/'parameters.json').read_text());G=parameters['groups']
if G!=4 and not args.controller_only:
 raise SystemExit('Full G64 requires qualified bounded reference compilation; do not rerun flat G64')
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
 resource.setrlimit(resource.RLIMIT_CPU,(300,300))
records=[]
def run(name,cmd):
 start=time.monotonic()
 p=subprocess.run(['/usr/bin/time','-f','%M','-o',str(out/(name+'.rss')),*map(str,cmd)],cwd=out,capture_output=True,text=True,timeout=360,preexec_fn=limits)
 (out/(name+'.log')).write_text(p.stdout+p.stderr)
 records.append({'name':name,'command':list(map(str,cmd)),'seconds':time.monotonic()-start,'returncode':p.returncode,'max_child_rss_kib':(out/(name+'.rss')).read_text().strip()})
 (out/'result.json').write_text(json.dumps({'status':'running' if not p.returncode else 'fail','steps':records},indent=2)+'\n')
 if p.returncode:raise RuntimeError(f'{name} failed; see {out/(name+".log")}')
common=['ot_hdc_fpu.sv','ot_hdc_fp32_mul_pipe.sv','ot_hdc_fastfp.sv','ot_hdc_delay.sv','ot_hdc_sfu.sv','ot_fp32_add_rne_pipe.sv']
tops=['replay_controller'] if args.controller_only else ['replay_controller','replay_matvec_ref','ot_hdc_matvec_mac_group',*[f'replay_bank{n}' for n in parameters['bank_add_variants']]]
for top in tops:
 if top in ('replay_controller','replay_matvec_ref'):
  files=[('controller.sv' if top=='replay_controller' else 'reference.sv'),*common]
  params=[f'-GG={G}','-GW=16','-GINT8_WEIGHT=1',f'-GINT8_SCALE_WCS_BASE={args.scale_wcs_base}']
 else:
  files=['kernels.sv',*([f'bank{top[-1]}.sv'] if top.startswith('replay_bank') else []),*common];params=[]
 directory=out/top
 run('verilate_'+top,[args.verilator,'--cc','-Wno-fatal','-Wno-TIMESCALEMOD','--top-module',top,'--Mdir',directory,*params,*files])
 run('build_'+top,['make','-C',directory,'-f',f'V{top}.mk','-j2',f'V{top}__ALL.a'])
if args.controller_only:
 (out/'result.json').write_text(json.dumps({'status':'controller_build_only','groups':G,'steps':records},indent=2)+'\n');raise SystemExit(0)
version=subprocess.check_output([args.verilator,'-V'],text=True)
vroot=re.search(r'VERILATOR_ROOT\s*=\s*(\S+)',version).group(1)
runtime=[vroot+'/include/verilated.cpp']
major=int(re.search(r'Verilator (\d+)',subprocess.check_output([args.verilator,'--version'],text=True)).group(1))
if major>=5:runtime.append(vroot+'/include/verilated_threads.cpp')
run('link',['g++','-std=c++14','-O0','-pthread','-I'+vroot+'/include',*['-I'+str(out/t) for t in tops],out/'main.cpp',*[out/t/f'V{t}__ALL.a' for t in tops],*runtime,'-o',out/'gate'])
run('simulate',[out/'gate'])
assert 'PASS generic runtime composition' in (out/'simulate.log').read_text()
mutant=subprocess.run([str(out/'gate'),'--wrong-edge'],cwd=out,capture_output=True,text=True,timeout=10)
(out/'mutant.log').write_text(mutant.stdout+mutant.stderr)
assert mutant.returncode!=0 and 'FAIL case=' in mutant.stdout
pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.suffix in ('.sv','.cpp')}
result={'status':'pass','scale_wcs_base':args.scale_wcs_base,'parameters':parameters,'steps':records,'source_sha256':pins,'runner_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'verilator_version':subprocess.check_output([args.verilator,'--version'],text=True).strip(),'verdict':(out/'simulate.log').read_text().strip(),'negative_control':mutant.stdout.strip(),'claim_boundary':'Synthetic complete G4 matvec interface equivalence, no fullshape token or physical performance proof.'}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['verdict'])
