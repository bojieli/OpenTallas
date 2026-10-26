#!/usr/bin/env python3
"""Selected chain3 root profile: exact delivered-reset canonical source, current runtime.
Physical pins/outline come from the reviewed chain3 E-clock view. Synth-only until
new netlist LEC, actual clock C1-5 and geometry/canary gates pass.
"""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;R=HERE.parents[2]
EXPECTED='5cd6679d901745ced7b2b003841087ba65363b9f94344ee13c39564d540142dd'
def save(p,j):p.write_text(json.dumps(j,indent=1)+'\n')
def convert(src,out,canonical):
 src,out,canonical=map(lambda x:Path(x).resolve(),(src,out,canonical));assert not out.exists();assert hashlib.sha256(canonical.read_bytes()).hexdigest()==EXPECTED
 f=json.load(open(src/'freeze.json'));assert f['rtl_top']=='ot_hgi_coll_tkm_tp192_root_core';assert f['pins']==3575
 old=f['module'];new=old+'__delivered_reset';oldcan=f['rtl_top'];newcan=oldcan+'__delivered_reset'
 shutil.copytree(src,out,ignore=shutil.ignore_patterns('run','views','lec','signoff*','*.log','FAIL_*'))
 for p in list((out/'rtl').glob('*.sv')):
  if p.name==oldcan+'.sv':p.unlink();continue
  t=p.read_text().replace(old,new).replace(oldcan,newcan);q=p.with_name(p.name.replace(old,new));q.write_text(t)
  if q!=p:p.unlink()
 shutil.copyfile(canonical,out/'rtl'/canonical.name)
 q=out/'config.mk';q.write_text(q.read_text().replace(old,new).replace(oldcan,newcan))
 q=out/'rtl/portlist.txt'
 if q.exists():q.write_text(q.read_text().replace(oldcan,newcan))
 s=json.load(open(out/'face_shell.json'));s['module']=new;s['core']=new+'__fcore';s['core_def_file']=s['core_def_file'].replace(old,new);s['delivered_reset']={'port':'rst_n','max_private_release_cycles':3,'data_cycle_delta':0,'timed':True};s['files']=[x.replace(old,new) for x in s['files']];save(out/'face_shell.json',s)
 q=out/'constraint.sdc';t=q.read_text();t=t.replace("# reset: async assert, released by the partition's reset synchroniser one cycle ahead (recovery at 1 T)","# Delivered synchronous reset: timed416.5max/-40min, privatebufferdepth3; no local async falsepath.");assert 'set_input_delay -max 416.5000 -clock vclk [get_ports {rst_n}]' in t;assert 'set_false_path' not in t;q.write_text(t)
 for n in ['straps.py','lec.py','selrange_gate.py','vclk_corner.tcl','postcts_gate.tcl','pinreg_measure.tcl']:shutil.copyfile(R/'tools/die_plan'/n,out/n)
 subprocess.run([sys.executable,'-I',str(R/'tools/die_plan/signoff.py'),'bundle',str(out)],check=True)
 prev=f.pop('kit_hash');f.update(module=new,design=new,view=new,rtl_top=newcan,source_kit_hash=prev,rtl_overrides={canonical.name:{'path':str(canonical),'sha256':EXPECTED}},delivered_reset={'port':'rst_n','max_private_release_cycles':3,'data_cycle_delta':0,'timed':True,'input_max_ps':416.5,'input_min_ps':-40,'domain':'one833ps clk/buffer_clk domain; onlydie-rootasyncinputexception'},pins_file=str(out/'pins.json'),plan_delta_required='root hardcore module/view and clock budget_owner -> delivered_reset identity; private resetmax3; samechain3pins anddata0 cycles')
 f['face_shell']['core']=new+'__fcore';f['runtime_bundle']={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in ['signoff.py','sdc_lint.py','face_guard.py','io_hold_qualification.py','pair_skew.tcl','clock_family.tcl','lec.py','vclk_corner.tcl','postcts_gate.tcl','pinreg_measure.tcl']};f['kit_hash']=hashlib.sha256(json.dumps(f,sort_keys=True).encode()).hexdigest()[:16];save(out/'freeze.json',f)
 print(json.dumps(dict(kit=str(out),hash=f['kit_hash'],module=new,canonical=newcan,pins=f['pins'],reset=f['delivered_reset'])))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('source');a.add_argument('output');a.add_argument('canonical');x=a.parse_args();convert(x.source,x.output,x.canonical)
