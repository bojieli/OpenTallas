#!/usr/bin/env python3
"""Freeze merged control/metadata and both source-specific actual fixtures."""
import pathlib,subprocess,json,hashlib,sys,argparse
root=pathlib.Path(__file__).resolve().parents[2];p=argparse.ArgumentParser();p.add_argument('--workdir',required=True,type=pathlib.Path);p.add_argument('--parent-commit',required=True);a=p.parse_args();out=a.workdir.resolve()
subprocess.run([sys.executable,str(root/'tools/qwen_kv_die/numeric_stream_lifetime_prepare.py'),'--parent-commit',a.parent_commit,'--workdir',str(out)],check=True)
m=json.loads((out/'provenance.json').read_text());m['sources'].pop('rtl/test/qwen_kv_die/tb_qwen_numeric_stream_lifetime.sv')
for f in ['rtl/test/qwen_kv_die/tb_qwen_numeric_merged_lifetime.sv','rtl/test/qwen_kv_die/tb_qwen_numeric_merged_boundary.sv']:
 b=(root/f).read_bytes();q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
for f in ['rtl/physical/ot_qwen_tile_ctl_tp8_numeric_stream.sv','rtl/physical/ot_qwen_rom_tile_nkt_tp8_core_numeric_stream.sv','rtl/physical/ot_qwen_tile_tp8_numeric_stream_merged.sv']:
 b=subprocess.check_output(['git','show',a.parent_commit+':'+f],cwd=root);q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
m['runtime_inputs']={'native_profiles.hex':hashlib.sha256((out/'src/native_profiles.hex').read_bytes()).hexdigest()};m['parent_clock_roots']=22;m['physical_claim']=False;m['qualification_scope']='New immutable merged same-coherent-edge source, actual selected tile arithmetic/stalls/isolated resets/local two-operation held-offer boundary; no field/provider/lease/physical qualification.'
(out/'provenance.json').write_text(json.dumps(m,indent=2)+'\n')
