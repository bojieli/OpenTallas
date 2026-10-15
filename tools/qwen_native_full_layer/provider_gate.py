#!/usr/bin/env python3
"""Source-bound native Q/KV provider transport gate; no die/rate qualification."""
import argparse, hashlib, json, subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 d='rtl/qwen_sys/redesign_qwen/'
 core=[d+n+'.sv' for n in ('ot_qfd_su_kv_native_posted','ot_qfd_native_q_reader','ot_qfd_native_kv_commit_fence','ot_qfd_native_kv_row_provider','ot_qfd_native_qkv_provider')]
 common=core+['rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv']
 jobs=[]
 for name,params,expect in [('positive',{},'NATIVE_KV_PASS'),('historical',{'HEADS':2},'NATIVE_KV_PASS'),('lane',{'MUT_LANE':1},'NATIVE_KV_FAIL data_errors='),('tag',{'MUT_TAG':1},'NATIVE_KV_FAIL data_errors='),('mask',{'MUT_MASK':1},'NATIVE_KV_FAIL data_errors=')]+[('reject'+str(i),{'FAULTCASE':i},'NATIVE_KV_REJECT_PASS') for i in range(1,5)]:
  jobs.append(('native_'+name,'tb_native',[core[0],'rtl/test/qwen_su_kv_native/tb_native.sv'],params,expect))
 for name,param,expect in [('positive',None,'PROVIDER_PASS'),('row','MUT_ROW','PROVIDER_FAIL data_errors'),('qbeat','MUT_QBEAT','PROVIDER_FAIL data_errors'),('ack','MUT_ACK','PROVIDER_ACK_REJECT_PASS'),('early','MUT_COMMIT','PROVIDER_FAIL'),('qstale','MUT_RSP','PROVIDER_Q_REJECT_PASS')]:
  jobs.append(('provider_'+name,'tb_provider',common+['rtl/test/qwen_su_kv_native/tb_provider.sv'],{param:1} if param else {},expect))
 for name,param,expect in [('positive',None,'PROVIDER_PASS'),('ack','MUT_ACK','PROVIDER_ACK_REJECT_PASS'),('qstale','MUT_RSP','PROVIDER_Q_REJECT_PASS'),('qrepeat','MUT_QRESTART','PROVIDER_Q_RESTART_REJECT_PASS'),('qrfence','MUT_QRFENCE','PROVIDER_Q_FENCE_REJECT_PASS')]:
  jobs.append(('top_'+name,'tb_provider_top',common+['rtl/test/qwen_su_kv_native/tb_provider_top.sv'],{param:1} if param else {},expect))
 rows=[];files=set()
 for name,top,sources,params,expect in jobs:
  files.update(sources);binary=a.out/(name+'.vvp')
  cmd=['iverilog','-g2012','-s',top]+['-P'+top+'.'+k+'='+str(v) for k,v in params.items()]+['-o',str(binary)]+[str(a.root/f) for f in sources]
  c=subprocess.run(cmd,capture_output=True,text=True,timeout=120);(a.out/(name+'.compile.log')).write_text(c.stdout+c.stderr)
  if c.returncode:raise RuntimeError(name+' compile failed')
  r=subprocess.run(['vvp',str(binary)],capture_output=True,text=True,timeout=120);output=r.stdout+r.stderr;(a.out/(name+'.log')).write_text(output)
  matching=[line for line in output.splitlines() if line.startswith(expect)]
  if r.returncode or not matching:raise RuntimeError(name+' missing observed verdict '+expect)
  if 'data_errors' in expect and not any(int(line.split('data_errors')[1].lstrip('=').split()[0])>0 for line in matching):raise RuntimeError(name+' mutant did not corrupt data')
  if name=='provider_early' and not any(int(line.split('early')[1].split()[0])>0 for line in matching):raise RuntimeError('commit mutant did not release early')
  rows.append({'name':name,'params':params,'compile_exit':c.returncode,'simulator_exit':r.returncode,'observed':matching,'verdict_sha256':hashlib.sha256(output.encode()).hexdigest()});binary.unlink();print(name+': '+matching[-1],flush=True)
 receipt={'scope':'NATIVE_PROVIDER_COMPONENT_CONTROL_TRANSPORT','production_memory':False,'physical_rate_qualified':False,'source_sha256':{f:hashlib.sha256((a.root/f).read_bytes()).hexdigest() for f in sorted(files)},'cases':rows}
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
