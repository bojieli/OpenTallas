#!/usr/bin/env python3
"""Reconstruct exact selected FQREG HP13 frontend and a default-off HEAD37 source successor.

Source preparation only. No Yosys, construction, simulation, physical binding or
source-selected image activation is launched. CALREG remains1 throughout.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FROZEN='c303af45e5b';AUTH='1a07d1e4ad2aed2bde61fa3307d827e41aa99e3e'
NF='results/arch/qw_headprep_1021/rrloc_projection/native_frontend'
CTX='results/qc_types_10_ctlm_1108'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 def show(ref,path):return subprocess.run(['git','-C',str(a.repo),'show',ref+':'+path],check=True,capture_output=True).stdout
 a.out.mkdir(parents=True,exist_ok=False);base=a.out/'baseline';candidate=a.out/'candidate'
 inv=json.loads(show(FROZEN,NF+'/input_source_inventory.json'))['files'];cmap=json.loads(show(AUTH,CTX+'/frontend_input_commits.json'))
 root={'physical_abstracts.v','physical_abstracts.json','full_generic_hp13.ys','construct_hp13.py','run_frontend.sh'};files={}
 for path,digest in inv.items():
  if path in root:continue
  b=show(cmap[path],path)
  if sha(b)!=digest:raise ValueError('frozen input differs: '+path)
  files[path]=b
 for name in ['physical_abstracts.v','physical_abstracts.json','full_generic_hp13.ys','construct_hp13_2.py']:
  b=show(FROZEN,NF+'/'+name)
  if name in inv and sha(b)!=inv[name]:raise ValueError('frozen recipe differs: '+name)
  files[name]=b
 for m in json.loads(files['physical_abstracts.json']):
  if m['source'] in files:continue
  for ref in [FROZEN,'4b215c0b3','8349f4a116626c59dfdb5ab8670f818514faa0e8']:
   try:b=show(ref,m['source'])
   except subprocess.CalledProcessError:continue
   if sha(b)==m['source_sha256']:files[m['source']]=b;break
  else:raise ValueError('frozen macro source unavailable: '+m['source'])
 # Exact current selected FQREG recipe: HEAD37 body, module alias, CALREG1.
 h=show(AUTH,'rtl/qwen_dv/headprep37/qfd_dv_cmd_cal_mu_head37.sv').decode()
 h=h.replace('module qfd_dv_cmd_cal_mu_head37 #(','module qfd_dv_cmd_cal_mu #(',1)
 old='    parameter integer CALREG = 0                    // QE3-CTLM3';new='    parameter integer CALREG = 1                    // CTLM-FQREG 11-08 frontend: [0] FQREG on; QE3-CTLM3'
 assert h.count(old)==1;h=h.replace(old,new,1);cal='rtl/qwen_dv/headprep13/frontend_fqreg/qfd_dv_cmd_cal_mu_fqreg.sv';files[cal]=h.encode()
 oldpath=' rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv ';ys=files['full_generic_hp13.ys'].decode();assert ys.count(oldpath)==1
 files['full_generic_hp13.ys']=ys.replace(oldpath,' '+cal+' ',1).encode()
 rows=[]
 for path,b in files.items():
  p=base/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  c=b.decode();patched=c
  if path.endswith('/qfd_tt_ctlm_dv_lpf_hp13.sv')or path.endswith('/qfd_tt_ctlm_dv_lpf_hp13_lp.sv'):
   needle='    parameter integer LAST_STAGE = 37,';assert c.count(needle)==1
   patched=c.replace(needle,'    parameter integer HEAD_STAGE37 = 0,\n'+needle,1)
   needle='.PRIVATE_CALR(PRIVATE_CALR), .F16WTN(F16WTN), .CAL_MUT(CAL_MUT)';assert patched.count(needle)==1
   patched=patched.replace(needle,'.HEAD_STAGE37(HEAD_STAGE37), '+needle,1)
   restored=patched.replace('    parameter integer HEAD_STAGE37 = 0,\n','',1).replace('.HEAD_STAGE37(HEAD_STAGE37), ','',1);assert restored==c
  elif path.endswith('/qfd_tt_ctlm_dv_lpf_hp13_parts.sv'):
   needle='    parameter integer LAST_STAGE = 37,';assert c.count(needle)==1
   patched=c.replace(needle,'    parameter integer HEAD_STAGE37 = 0,\n'+needle,1)
   needle='qfd_dv_cmd_cal_mu #(.MUT(CAL_MUT),';assert patched.count(needle)==1
   patched=patched.replace(needle,'qfd_dv_cmd_cal_mu #(.HEAD_STAGE37(HEAD_STAGE37), .MUT(CAL_MUT),',1)
   restored=patched.replace('    parameter integer HEAD_STAGE37 = 0,\n','',1).replace('.HEAD_STAGE37(HEAD_STAGE37), ','',1);assert restored==c
  q=candidate/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(patched)
  rows.append({'path':path,'baseline_sha256':sha(b),'candidate_sha256':sha(q.read_bytes()),'changed':patched!=c})
 for enabled in [0,1]:
  body=files['full_generic_hp13.ys'].decode().replace('chparam -set XPF_TRANSPORT_EDGES','chparam -set HEAD_STAGE37 '+str(enabled)+' -set XPF_TRANSPORT_EDGES',1)
  (candidate/f'frontend_head37_{enabled}.ys').write_text(body)
 rec={'schema':'opentallas.qc-head37-frozen-tt-frontend.v1','status':'SOURCE_READY_NOT_ELABORATED','frozen_input_inventory_commit':FROZEN,'selected_FQREG_recipe_commit':AUTH,'current_selected_native_sha256':'81f18c88024732039b2f11c36444cfabc5c6c355b19b92a4120938d3787bd544','current_selected_corepub1_sha256':'c09b67b7cc1ce904a5b956730d427d38832670eff839dfd2ccc38875bb974dbb','CALREG':1,'HEAD_STAGE37_default':0,'added_pipeline_edges':0,'changed_files':[r['path']for r in rows if r['changed']],'default_off_source_delta_reversible':True,'files':rows,'global_enable':False,'physical_binding_changed':False,'remaining':['native frontend off/on elaboration and minimum controller gate','reconstruct current source-bound core publisher after actual native netlist generation','actual48 selected loader/command/publication windows','physical source gate before adoption']}
 (a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('HEAD37_TT_FRONTEND_READY',len(rows),'files',len(rec['changed_files']),'changed CALREG1/default0')
if __name__=='__main__':main()
