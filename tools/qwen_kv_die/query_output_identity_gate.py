#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
r=pathlib.Path('rtl/physical/ot_qwen_tile_query_output_identity.sv');b=pathlib.Path('rtl/test/qwen_kv_die/tb_qwen_tile_query_output_identity.sv');s=r.read_text()
cases={'positive':s,'early_output':s.replace('valid[44]','valid[43]').replace('metadata[44]','metadata[43]'),'forced_allocated':s.replace('valid[43:0],query_issue_v','valid[43:0],1\'b1'),'truncated32':s.replace('query_version,query_sequence','query_version,query_sequence[31:0]')};records={}
with tempfile.TemporaryDirectory(prefix='qwen-output-id-') as tmp:
 for name,content in cases.items():
  path=pathlib.Path(tmp)/f'{name}.sv';path.write_text(content);exe=path.with_suffix('.vvp');x=subprocess.run(['iverilog','-g2012','-s','tb_qwen_tile_query_output_identity','-o',str(exe),str(path),str(b)],capture_output=True,text=True);assert x.returncode==0,x.stderr
  x=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/f'{name}.log').write_text(x.stdout+x.stderr);records[name]={'exit':x.returncode,'source_sha256':hashlib.sha256(content.encode()).hexdigest()};assert (x.returncode==0)==(name=='positive'),name
(a.out/'record.json').write_text(json.dumps({'status':'OUTPUT_IDENTITY_MAILBOX_UNIT_ONLY_FULL_NATIVE_BINDING_PENDING','source_sha256':hashlib.sha256(r.read_bytes()).hexdigest(),'bench_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'cases':records},indent=2)+'\n')
