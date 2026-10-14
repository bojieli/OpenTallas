#!/usr/bin/env python3
"""Freeze immutable production context/query or accepted-descriptor fixture."""
import argparse,hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workdir',required=True,type=pathlib.Path);p.add_argument('--parent-commit',required=True);p.add_argument('--accepted-ib',action='store_true');a=p.parse_args();out=a.workdir.resolve()
subprocess.run([sys.executable,str(root/'tools/qwen_kv_die/xcache_parent_prepare.py'),'--parent-commit',a.parent_commit,'--split-cache','--workdir',str(out)],check=True)
m=json.loads((out/'provenance.json').read_text());m['sources'].pop('rtl/test/qwen_kv_die/tb_qwen_xcache_split_parent.sv')
f='rtl/physical/ot_qwen_rom_tile_nkt_tp8_core_ctx.sv';b=subprocess.check_output(['git','show',a.parent_commit+':'+f],cwd=root);q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
bench='rtl/test/qwen_kv_die/tb_qwen_actual_query_ledger.sv'
f='rtl/physical/ot_qwen_context_admission.sv';b=subprocess.check_output(['git','show',a.parent_commit+':'+f],cwd=root);q=out/'src'/f;q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
for f in [bench,'rtl/physical/ot_qwen_xcache_context32.sv']:
 b=(root/f).read_bytes();q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
for f in ['rtl/physical/ot_qwen_tile_tp8_context_events.sv','rtl/physical/ot_qwen_rom_tile_nkt_tp8_core_grouped_ctx.sv','rtl/physical/ot_qwen_tile_kids_grouped.sv','rtl/physical/ot_qwen_tile_tx8_capture.sv','rtl/physical/ot_qwen_xcache_context32_events.sv']:
 b=subprocess.check_output(['git','show',a.parent_commit+':'+f],cwd=root);q=out/'src'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest()
f='rtl/physical/ot_qwen_xdelivery_lifetime.sv';b=subprocess.check_output(['git','show','f9bb1fc09:'+f],cwd=root);q=out/'src'/f;q.write_bytes(b);m['sources'][f]=hashlib.sha256(b).hexdigest();m['lifetime_commit']='f9bb1fc09'
m['qualification_scope']='actual production registered query ports and acceptance snapshot; source version/provider/ACK and physical delivery unqualified'
(out/'provenance.json').write_text(json.dumps(m,indent=2)+'\n')
