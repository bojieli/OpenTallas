#!/usr/bin/env python3
"""Prepare default-off protocol miter with immutable production descriptor words."""
import argparse,hashlib,json,pathlib,shutil,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workdir',required=True,type=pathlib.Path);a=p.parse_args();out=a.workdir.resolve();out.mkdir(parents=True,exist_ok=True)
profile=out/'profile_parent'
subprocess.run([sys.executable,str(root/'tools/qwen_kv_die/xcache_parent_prepare.py'),'--parent-commit','7cbe00c33','--workdir',str(profile)],check=True)
shutil.copy(profile/'src/native_profiles.hex',out/'native_profiles.hex')
m={'source_claim':'default-off dictionary miter; production IB379 descriptors, synthetic full32-root keys','sources':{},'program':json.loads((profile/'provenance.json').read_text())['program'],'profiles_sha256':hashlib.sha256((out/'native_profiles.hex').read_bytes()).hexdigest()}
for f in ['rtl/physical/ot_qwen_xcontext_protocol.sv','rtl/test/qwen_kv_die/tb_qwen_xcontext_protocol.sv','rtl/test/qwen_kv_die/tb_qwen_xcontext_wrap.sv']:
 b=(root/f).read_bytes();q=out/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
(out/'provenance.json').write_text(json.dumps(m,indent=2)+'\n')
