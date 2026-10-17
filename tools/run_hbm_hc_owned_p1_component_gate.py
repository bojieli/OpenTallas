#!/usr/bin/env python3
"""Run one explicitly admitted frozen P1 component; audit before C++ make."""
import hashlib,json,re,subprocess
from pathlib import Path
TOP='tb_hgi_hc_owned_p1_sys1_prepared'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,r):p.write_text(json.dumps(r,indent=2)+'\n')
def main():
 out=Path.cwd();r=json.loads((out/'prepared.json').read_text())
 for d in r['dependency_sources']:assert sha(out/'frozen'/d['path'])==d['sha256'],d['path']
 for n,h in r['fixture_sha256'].items():assert sha(out/n)==h,n
 for p,h in r['new_source_sha256'].items():
  if p.startswith('rtl/test/'):assert sha(out/'frozen'/p)==h,p
 dump(out/'running.json',{'stage':'elaboration','one_pinned_job':True,'scope':'one ownedrow+declaredcollectivemixes P1 component, not canonicalwholeprofile'})
 cmd=r['build_command_NOT_RUN'];cmd=[x for x in cmd if x!='--build'];j=cmd.index('-j');cmd[j:j+2]=[]
 with (out/'elaborate.log').open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o','elaborate.resources',*cmd],stdout=log,stderr=subprocess.STDOUT)
 if rc:dump(out/'terminal.json',{'status':'ELABORATE_FAIL','returncode':rc});return rc
 warnings=[];accepted=[];fatal=[]
 text=(out/'elaborate.log').read_text()
 prefix=out/'frozen/rtl/hdc/ot_hdc_prefix.sv'
 prefix_ok=sha(prefix)=='98f2492a22012ffbaae49ac8405c2af693e16cb7bcdfafc5eb66db7943240587'
 for line in text.splitlines():
  m=re.match(r'%Warning-([A-Z0-9_]+): (.*)',line)
  if not m:continue
  typ,msg=m.groups();warnings.append({'type':typ,'message':msg})
  if typ=='UNOPTFLAT' and prefix_ok and 'ot_hdc_prefix.sv:' in msg and re.search(r"\.(?:g|p|t)(?:\[[^]]+\])?'",msg):
   accepted.append({'type':typ,'message':msg,'basis':'Exact98f indexedprefixsource: all arraylevel LHS=l+1, RHS=l only; level0 operands; finiteclog2 directedacyclicgraph, no hardware combinationalcycle'})
  elif typ in ('LATCH','MULTIDRIVEN','UNOPTFLAT','SELRANGE','PINMISSING','PINNOTFOUND','PINCONNECTEMPTY','UNDRIVEN','IMPLICIT','BLKANDNBLK'):fatal.append({'type':typ,'message':msg})
 dump(out/'warning_audit.json',{'warnings':warnings,'accepted_exact_prefix_DAG_only':accepted,'unresolved':fatal,'broad_latch_or_multidriver_waiver':False})
 if fatal:dump(out/'terminal.json',{'status':'WARNING_AUDIT_FAIL','Cxx_make_started':False,'unresolved':fatal});return 2
 dump(out/'running.json',{'stage':'Cxx_make','elaboration_audit_passed':True})
 with (out/'make.log').open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o','make.resources','make','-C','obj','-f','V'+TOP+'.mk','-j','4'],stdout=log,stderr=subprocess.STDOUT)
 if rc:dump(out/'terminal.json',{'status':'MAKE_FAIL','returncode':rc});return rc
 verdict={}
 for case,cmd in zip(['positive','owned_weight_mutant','VM_payload_mutant'],r['runtime_commands_NOT_RUN']):
  with (out/(case+'.log')).open('x') as log:rc=subprocess.call(['/usr/bin/time','-v','-o',case+'.resources',*cmd],stdout=log,stderr=subprocess.STDOUT)
  logtext=(out/(case+'.log')).read_text();passed=(rc==0 and 'HC_OWNED_P1_COMPONENT PASS' in logtext) if case=='positive' else (rc!=0 and ('owned row independently differs' in logtext if case=='owned_weight_mutant' else 'actual VM declared gather mismatch' in logtext))
  verdict[case]={'exit_code':rc,'expected_verdict_met':passed,'log_sha256':sha(out/(case+'.log'))};print(case,rc,logtext[-900:],flush=True)
  dump(out/'verdicts.json',verdict)
  if not passed:dump(out/'terminal.json',{'status':'POSITIVE_FAIL' if case=='positive' else 'MUTANT_INVALID','verdicts':verdict,'qualification':False});return 3
 for d in r['dependency_sources']:assert sha(out/'frozen'/d['path'])==d['sha256']
 dump(out/'terminal.json',{'status':'PASS','verdicts':verdict,'all_frozen_dependency_hashes_verified':True,'scope':'P1 ownedrow0 rank3,24 declaredpostcollectivemixes via24realVM,106generatedSRAM sourceinstances/equalphase92; not canonicalwholeprofile/actualHCOLL/physicalqualification','prepared_sha256':sha(out/'prepared.json'),'warning_audit_sha256':sha(out/'warning_audit.json')});return 0
if __name__=='__main__':raise SystemExit(main())
