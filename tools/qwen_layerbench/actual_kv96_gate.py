"""Actual current native KV boot parent parameters, 96/77 config ABI and cost.
Run through ot-run; source tree is read-only. No full boot/G5 timing claim.
"""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('tree',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo/'tools/qwen_layerbench/kv_dieslice'))
 import native_boot_ages as ages
 fixture=repo/'results/rtl/native_boot_abi_1713';out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);src=out/'src';src.mkdir()
 folder=a.tree/'rtl/qwen_sys/static_kv_die_20261017'
 parent=(folder/'qkd_kvs_ctl_nc32.sv').read_text();face=(folder/'qkd_kv_ctl_nc32_face.sv').read_text()
 expected=dict(MUT=0,DIECFG=1,NRST=43,LINKCFG=1,ESCFG=1,DIECAP=1,AGES=1,MU=1,WMUT=0,SRQ=2,DSTG=1)
 match=re.search(r'qkd_static_kv_boot_dispatch_mu_nc32\s*#\((.*?)\)\s*u_boot\s*\(',parent,re.S)
 assert match,'actual u_boot missing';actual={k:int(v) for k,v in re.findall(r'\.(\w+)\((\d+)\)',match[1])};assert actual==expected,(actual,expected)
 match=re.search(r'qkd_kv_die_cfg_a_c32\s*#\((.*?)\)\s*u_dcfg\s*\(',parent,re.S)
 rx={k:int(v) for k,v in re.findall(r'\.(\w+)\((\d+)\)',match[1])};assert rx==dict(NRST=43,CAP=1,AGES=1,MUT=0),rx
 assert ages.control(parent)==parent,'actual parent not already qualified AGES1'
 assert ages.dispatch(face)==face,'actual dispatcher not already qualified AGES1'
 hashes={}
 paths=[folder/x for x in ['qkd_kvs_ctl_nc32.sv','qkd_kv_ctl_nc32_face.sv','qkd_kv_ctl_c32_boot.sv','qkd_kv_ctl_c32_dcfg.sv','qkd_kv_ctl_c32_misc.sv']]+[a.tree/'rtl/lib/ot_s32_cells.sv']
 for p in paths:shutil.copy2(p,src/p.name);hashes[str(p.relative_to(a.tree))]=hashlib.sha256(p.read_bytes()).hexdigest()
 for name in ['tb_actual_kv96.sv','legacy_dispatch.sv']:shutil.copy2(fixture/name,src/name)
 shutil.copy2(fixture/'target10_b19.hex',out/'target10.hex')
 command=['verilator','--binary','--timing','-Wno-fatal','-j','4','--top-module','tb','--Mdir',str(out/'obj'),'-o','sim']
 command +=[str(src/x) for x in ['tb_actual_kv96.sv','legacy_dispatch.sv','qkd_kv_ctl_nc32_face.sv','qkd_kv_ctl_c32_boot.sv','qkd_kv_ctl_c32_dcfg.sv','qkd_kv_ctl_c32_misc.sv','ot_s32_cells.sv']]
 with (out/'build.log').open('w')as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (out/'run.log').open('w')as log:subprocess.run([str(out/'obj/sim')],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
 output=(out/'run.log').read_text();assert 'PASS ACTUAL_PARENT_PARAMS' in output,output
 result=dict(status='PASS',actual_parent_params=actual,actual_receiver_params=rx,control_idempotent=True,dispatch_idempotent=True,source_hashes=hashes,image_sha256=hashlib.sha256((out/'target10.hex').read_bytes()).hexdigest(),output=output,native_config_word_cycles_added=19,at_833ps_minimum_added_ns=15.827,host_framing='not priced by this component gate',scope='actual dispatcher/config receiver; not whole boot or G5')
 (out/'gate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
