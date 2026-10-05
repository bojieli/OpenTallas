#!/usr/bin/env python3
"""Fail-closed single local source trace, no retries, under aggregate cgroup.
Run only --service inside exact systemd unit; source snapshots/model presealed.
"""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time
import dsrom_PAR2_runtime_consumer_calibration as O
M=O.M
ROOT=M.ROOT;B=O.O.B

def verified_caps(cp,affinity):
 caps={k:(cp/k).read_text().strip() for k in ['memory.max','memory.swap.max']}
 caps['affinity']=sorted(affinity);caps['cgroup_path']=str(cp)
 caps['cpuset_file_present']=(cp/'cpuset.cpus.effective').exists()
 caps['CPU_enforcement']='taskset/CPUAffinity inherited by all descendants; compiler-j2 and all Verilator contexts threads1'
 if caps['cpuset_file_present']:caps['cpuset.cpus.effective']=(cp/'cpuset.cpus.effective').read_text().strip()
 assert caps['memory.max']==str(8*1024**3) and caps['memory.swap.max']=='0' and caps['affinity']==[30,31], 'aggregate caps unavailable; NO FALLBACK'
 return caps

def main(a):
 out=a.out;out.mkdir(parents=True,exist_ok=False)
 rec=dict(result='FAIL',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),stages=[],caps={},prediction_sha256=M.sha(a.preparation/'prediction.json'),source_manifest_sha256=M.sha(B/'sources.json'))
 def save(): (out/'record.json').write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n')
 save()
 try:
  assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip(),'dirty source worktree'
  cg=next(l.split(':',2)[2] for l in pathlib.Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::'))
  cp=pathlib.Path('/sys/fs/cgroup')/cg.lstrip('/')
  rec['caps']=verified_caps(cp,os.sched_getaffinity(0));save()
  unit=os.environ['DSROM_UNIT']
  props=subprocess.check_output(['systemctl','--user','show',unit,'--property=RuntimeMaxUSec','--property=MemoryMax','--property=MemorySwapMax','--property=AllowedCPUs','--property=CPUAffinity'],text=True);rec['caps']['systemd_properties']=props
  assert 'RuntimeMaxUSec=5min' in props or 'RuntimeMaxUSec=300000000' in props
  pins=json.loads((B/'sources.json').read_text())
  for f,h in pins.items():assert M.sha(B/'pinned'/f)==h,'source snapshot mismatch '+f
  rec['source_sha256']=pins
  rec['fixture_sha256']={p.name:M.sha(p) for p in B.iterdir() if p.is_file()}
  rec['calibration_fixture_sha256']={p.name:M.sha(p) for p in O.B.iterdir() if p.is_file()}
  rec['compiler_sha256']=M.sha(M.V);rec['compiler_version']=subprocess.check_output([str(M.V),'--version'],text=True).strip();assert rec['compiler_version'].startswith('Verilator 5.050')
  rec['options']=['--cc','-O3','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','--threads','1','-DV41_RT','-DRT_CUT','FAST1','PP1','BP0','PHW10','NP4096','NBF724','R128','make-j2','OPT_FAST=-O2','OPT_SLOW=-O1']
  save();start=time.monotonic();compile_deadline=start+240
  def run(name,cmd,deadline):
   t=time.monotonic();log=out/(name+'.log')
   with log.open('w') as f:
    p=subprocess.Popen([str(x) for x in cmd],cwd=out,stdout=f,stderr=subprocess.STDOUT)
    while p.poll() is None:
     if time.monotonic()>deadline:
      p.terminate();p.wait(timeout=3);raise RuntimeError(name+' declared deadline exceeded')
     size=sum(x.stat().st_size for x in out.rglob('*') if x.is_file())
     if size>1024**3:p.terminate();p.wait(timeout=3);raise RuntimeError('aggregate generated files exceed1GiB')
     time.sleep(.2)
   rec['stages'].append(dict(name=name,argv=[str(x) for x in cmd],returncode=p.returncode,seconds=round(time.monotonic()-t,3),log_sha256=M.sha(log)));save()
   if p.returncode:raise RuntimeError(name+' failed; STOP FIRST FAILURE')
  common=[B/'pinned'/p for p in M.COMMON+M.W10]
  models=[('cut','dsrom_runtime_consumers',['rtl/v41die/ot_v41_spine_w17w10.sv','rtl/v41die/ot_v41_rom_adapt.sv'],['-GNP=4096','-GR=128','-GNBF=724','-GPHW=10','-GVAW=30','-GBST=17','-GFAST=1','-GPP=1','-GBP=0']),('pq','dsrom_source_pair',['rtl/v41die/ot_v41_pair_w17w10.sv']+M.ROM,['-GPHW=10','-GBF16=0','-GXF=4','-GFAST=1','-GPP=1','-GBP=0']),('pb','dsrom_source_pair',['rtl/v41die/ot_v41_pair_w17w10.sv']+M.ROM,['-GPHW=10','-GBF16=1','-GXF=8','-GFAST=1','-GPP=1','-GBP=0']),('retn','ot_v41_retn_w17w10',['rtl/v41die/ot_v41_retn_w17w10.sv'],['-GRD=64','-GRST=1','-GBYPASS=1']),('root','dsrom_source_root',[],['-GD=128','-GQD=128'])]
  template_root=out
  if a.reuse_templates:
   template_root=a.reuse_templates
   prior=json.loads((template_root/'record.json').read_text())
   assert all(pins.get(k)==v for k,v in prior['source_sha256'].items()) and prior['compiler_sha256']==rec['compiler_sha256']
   for name,h in prior['fixture_sha256'].items():
    if name in ['dsrom_source_pair.sv','dsrom_source_root.sv']:assert M.sha(B/name)==h,'retained pair/root observer changed'
   receipt=json.loads((B/'retained_templates.json').read_text())
   for f,h in receipt['archive_and_header_sha256'].items():assert M.sha(template_root/f)==h,'retained template changed'
   rec['retained_template_source_commit']=prior['source_commit'];rec['retained_template_receipt_sha256']=M.sha(B/'retained_templates.json');save()
  assert a.reuse_templates and a.reuse_cut, 'all five retained templates required; no HDL rebuild fallback'
  cutprior=json.loads((a.reuse_cut/'record.json').read_text())
  assert cutprior['source_sha256']==pins and cutprior['compiler_sha256']==rec['compiler_sha256']
  assert cutprior['fixture_sha256']['dsrom_runtime_consumers.sv']==M.sha(B/'dsrom_runtime_consumers.sv')
  cr=json.loads((O.B/'retained_cut.json').read_text())
  assert cutprior['source_commit']==cr['source_commit']
  for f,h in cr['archive_and_header_sha256'].items():assert M.sha(a.reuse_cut/f)==h,'retained cut changed'
  rec['retained_cut_receipt_sha256']=M.sha(O.B/'retained_cut.json');save()
  for prefix,top,files,params in []:
   wrap=[B/(top+'.sv')] if top.startswith('dsrom_') else []
   run('verilate_'+prefix,[M.V,'--cc','-O3','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','--threads','1','--top-module',top,'--prefix','V'+prefix,'--Mdir',out/prefix,'-DV41_RT','-DRT_CUT',*params,*wrap,*[B/'pinned'/p for p in files],*common],compile_deadline)
   run('build_'+prefix,['make','-C',out/prefix,'-f','V'+prefix+'.mk','-j2','V'+prefix+'__ALL.a','OPT_FAST=-O2','OPT_SLOW=-O1'],compile_deadline)
  vroot=M.V.parent.parent/'share/verilator'
  # Derive installed include directory from compiler-owned -V; no fallback.
  import re
  vv=subprocess.check_output([str(M.V),'-V'],text=True);vroot=pathlib.Path(re.search(r'VERILATOR_ROOT\s*=\s*(\S+)',vv).group(1))
  incl=[vroot/'include',vroot/'include/vltstd']+[(a.reuse_cut/p if p=='cut' else template_root/p) for p,_,_,_ in models]
  runtime=[vroot/'include'/p for p in ['verilated.cpp','verilated_threads.cpp','verilated_dpi.cpp']]
  run('link',['g++','-std=c++20','-O2','-pthread','-DNP=4096','-DNR=128','-DNBF=724','-DPHW=10','-DVAW=30',*['-I'+str(p) for p in incl],O.B/'host.cpp','-Wl,--start-group',*[(a.reuse_cut/p if p=='cut' else template_root/p)/('V'+p+'__ALL.a') for p,_,_,_ in models],'-Wl,--end-group',*runtime,'-o',out/'gate'],compile_deadline)
  rec['binary_sha256']=M.sha(out/'gate');save()
  run('runtime',[out/'gate',a.preparation/'img',out/'actual.jsonl'],min(start+290,time.monotonic()+30))
  events=[json.loads(x) for x in (out/'actual.jsonl').read_text().splitlines()]
  rec['calibration']=O.compare(a.preparation,events)
  rec['actual_counts']=dict(__import__('collections').Counter(x['kind'] for x in events))
  rec['actual_journal_sha256']=M.sha(out/'actual.jsonl')
  rec['drained']=any(x['kind']=='all_source_root_writer_drained' for x in events)
  rec['result']='PASS' if rec['calibration']['result']=='PASS' and rec['drained'] else 'FAIL'
  rec['scope']='Current r5 L0.I66 native adapter/EID/ROM_BST17 spine+fullfield+exacttileROMmemoryprocess CONE; nonzero synthetic1 weights/input; actualpostNBA destination visibility. Otherwritersinactive/fullcore scheduler/collbusy/physicalPAR2interdie/hardprovider/SSFF/fulltoken unqualified.'
 except BaseException as e:rec['error']=repr(e)
 finally:
  rec['finish_monotonic']=time.monotonic()
  if 'cp' in locals():rec['cgroup_finish']={k:(cp/k).read_text().strip() for k in ['memory.peak','memory.events','memory.current']}
  save()
 return 0 if rec['result']=='PASS' else 1
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--reuse-cut',type=pathlib.Path,required=True);p.add_argument('--reuse-templates',type=pathlib.Path,required=True);p.add_argument('--preparation',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();sys.exit(main(a))
