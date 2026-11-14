#!/usr/bin/env python3
"""Focused source isolation and existing synthetic default-programme comparison."""
import argparse, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, types
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path.cwd());ap.add_argument('--main-ref',default='9556712d49');ap.add_argument('--verilator',default=shutil.which('verilator') or str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'));a=ap.parse_args();root=a.root.resolve()
def prior(ref,path):return subprocess.check_output(['git','-C',str(root),'show',ref+':'+path],text=True)
def tokens(text):return ' '.join(re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S).split())
checks=[]
with tempfile.TemporaryDirectory() as tmp:
 for rel,ref,engine in [('rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv','84b3a53d7e^',False),('rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv','7239ea0c89^',True)]:
  for selected in (False,True):
   baseline='4b3430fb52' if selected else ref
   pp=Path(tmp)/'prior.sv';pp.write_text(prior(baseline,rel));flags=['-DOT_SVC_MERGE_H4','-DOT_ATTN_HCORE','-DOT_SVC_H8_REUSE_RT2']+(['-DOT_SVC_NATIVE_RT2_CALENDAR'] if selected else [])
   values=[]
   for source in (pp,root/rel):
    value=subprocess.check_output([a.verilator,'-E','-P',*flags,str(source)],text=True)
    if engine and not selected:value=value[:value.index('endmodule')+len('endmodule')]
    values.append(tokens(value))
   checks.append(dict(source=rel,selected=selected,reference=baseline,equal=values[0]==values[1]))
 # Reuse the production synthetic image/schedule fixture unchanged; compare
 # every byte/timestamp and done/span digest to the requested current main.
 rel='tools/s81_dv/layer_prog/lower_svc.py';base=types.ModuleType('lower_svc_optin_baseline');base.__file__=str(root/rel);sys.modules[base.__name__]=base
 sys.path.insert(0,str(root/'tools/s81_dv/layer_prog'));os.environ.pop('OT_SVC_NATIVE_RT2_CALENDAR',None)
 exec(compile(prior(a.main_ref,rel),base.__file__,'exec'),base.__dict__)
 spec=importlib.util.spec_from_file_location('svc_optin_fixture',root/'tools/s81_dv/layer_prog/test_lower_svc_h8.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
 for heads,rows in ((16,128),(8,32),(8,128)):
  images=[]
  for mod in (base,fixture.L):
   job=fixture.synth(heads=heads,T=rows,mod=mod);schedule=fixture.run(job,mod=mod);images.append(fixture.digest(job,schedule,mod=mod))
  checks.append(dict(source=rel,selection='default',reference=a.main_ref,heads=heads,rows=rows,equal=images[0]==images[1]))
record=dict(status='PASS' if all(c['equal'] for c in checks) else 'FAIL',checks=checks,scope='Source preprocessing and default production compiler bytes/schedule only. No global H8 timing or geometry qualification.')
print(json.dumps(record,indent=2));sys.exit(0 if record['status']=='PASS' else 1)
