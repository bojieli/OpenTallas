#!/usr/bin/env python3
"""Freeze source-specific actual native tile admission fixture (ot-run gate)."""
import argparse,pathlib,subprocess,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--parent-commit',required=True);p.add_argument('--workdir',required=True,type=pathlib.Path);a=p.parse_args();out=a.workdir.resolve()
subprocess.run([sys.executable,str(root/'tools/qwen_kv_die/xcache_production_prepare.py'),'--parent-commit',a.parent_commit,'--accepted-ib','--workdir',str(out)],check=True)
m=json.loads((out/'provenance.json').read_text());m['sources'].pop('rtl/test/qwen_kv_die/tb_qwen_xcache_accepted_ib.sv')
for f in ['rtl/physical/ot_qwen_context_admission.sv','rtl/test/qwen_kv_die/tb_qwen_actual_admission.sv']:
 b=subprocess.check_output(['git','show',a.parent_commit+':'+f],cwd=root)if 'test/'not in f else(root/f).read_bytes();q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
m['qualification_scope']='actual production post-IREG admission, accepted payload and callback under pauses; no global consumers, CDC, seals or arithmetic qualification'
(out/'provenance.json').write_text(json.dumps(m,indent=2)+'\n')
