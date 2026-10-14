#!/usr/bin/env python3
"""Freeze original split parent and default-off request-mode repair fixture."""
import argparse,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workdir',required=True,type=pathlib.Path);a=p.parse_args();out=a.workdir.resolve()
subprocess.run([sys.executable,str(root/'tools/qwen_kv_die/xcache_parent_prepare.py'),'--parent-commit','1ac31de60','--split-cache','--workdir',str(out)],check=True)
m=json.loads((out/'provenance.json').read_text());m['sources'].pop('rtl/test/qwen_kv_die/tb_qwen_xcache_split_parent.sv')
for f in ['rtl/test/qwen_kv_die/tb_qwen_xcache_mode_parent.sv','rtl/physical/ot_qwen_xcache_context32.sv']:
 b=(root/f).read_bytes();q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
m['mode_capture_scope']='reference production pre-update request state in harness; physical mode/context export not yet bound'
(out/'provenance.json').write_text(json.dumps(m,indent=2)+'\n')
