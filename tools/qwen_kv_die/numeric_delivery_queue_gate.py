#!/usr/bin/env python3
"""Isolated queue capacity candidate; no production binding or CDC qualification."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
r=pathlib.Path('rtl/physical/ot_qwen_tile_numeric_delivery_queue.sv');b=pathlib.Path('rtl/test/qwen_kv_die/tb_qwen_tile_numeric_delivery_queue.sv');s=r.read_text()
cases={'positive':s,'all_query':s.replace('numeric_has_query,numeric_query_seq,numeric_d',"1'b1,numeric_query_seq,numeric_d"),'truncate_sequence':s.replace('numeric_query_seq,numeric_d',"8'd0,numeric_query_seq[31:0],numeric_d"),'stopped_credit_sync':s.replace('read_sync1<=read_gray;read_sync2<=read_sync1;','if(output_step)begin read_sync1<=read_gray;read_sync2<=read_sync1;end')}
records={}
with tempfile.TemporaryDirectory(prefix='qwen-numeric-queue-') as tmp:
 for name,content in cases.items():
  path=pathlib.Path(tmp)/f'{name}.sv';path.write_text(content);exe=path.with_suffix('.vvp')
  run=subprocess.run(['iverilog','-g2012','-s','tb_qwen_tile_numeric_delivery_queue','-o',str(exe),str(path),str(b)],capture_output=True,text=True);assert run.returncode==0,run.stderr
  run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/f'{name}.log').write_text(run.stdout+run.stderr)
  records[name]={'exit':run.returncode,'source_sha256':hashlib.sha256(content.encode()).hexdigest()}
  assert (run.returncode==0)==(name=='positive'),name
(a.out/'record.json').write_text(json.dumps({'status':'ISOLATED_EIGHT_ENTRY_CAPACITY_COMPONENT_NO_PRODUCTION_CDC_OR_COST_ADOPTION','source_sha256':hashlib.sha256(r.read_bytes()).hexdigest(),'bench_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'storage_bits':4808,'pointer_and_sync_bits':32,'sticky_fault_bits':1,'cases':records},indent=2)+'\n')
