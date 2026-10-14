#!/usr/bin/env python3
"""Freeze actual posted SU/VM source, writer certificate and new lease fixture."""
import argparse,hashlib,json,pathlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
a.candidate=subprocess.check_output(['git','rev-parse',a.candidate],text=True).strip()
script=subprocess.check_output(['git','show','64e16e88d:rtl/test/qwen_vm_me/run_su_writer_quiescent.sh'],text=True)
files=re.findall(r'(?:rtl|physical)/[^\s]+\.(?:sv|v)',script)
files=[f for f in files if f!='rtl/test/qwen_vm_me/tb_qfd_su_writer_quiescent.sv']
files+=['rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_producer_lease_seq40.sv','rtl/physical/ot_qfd_vm_writer_command_fence.sv','rtl/test/qwen_vm_me/tb_qfd_vm_writer_lease_composition.sv']
manifest={'candidate':a.candidate,'writer_certificate_source':'64e16e88d','scope':'actual VMT0 posted-write store observation and command fence; no physical VM region or full token adoption','sources':{}}
for i,f in enumerate(dict.fromkeys(files)):
 commit=a.candidate if 'producer_lease_seq40' in f else '64e16e88d'
 b=subprocess.check_output(['git','show',commit+':'+f]) if f not in files[-2:] else pathlib.Path(f).read_bytes()
 q=a.out/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);manifest['sources'][f]=hashlib.sha256(b).hexdigest()
(a.out/'sources.txt').write_text('\n'.join(manifest['sources'])+'\n');(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
