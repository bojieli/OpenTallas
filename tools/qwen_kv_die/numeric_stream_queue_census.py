import json,pathlib,subprocess,hashlib
p=pathlib.Path.cwd();y='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys';records=[]
for depth in [2,8]:
 cmd=f'read_verilog -sv ot_qwen_numeric_stream_queue.sv; chparam -set ENABLE 1 -set DEPTH {depth} ot_qwen_numeric_stream_queue; hierarchy -top ot_qwen_numeric_stream_queue; proc; opt; memory_map; opt; write_json census{depth}.json; stat'
 with(p/f'census{depth}.log').open('w')as f:subprocess.run([y,'-p',cmd],stdout=f,stderr=subprocess.STDOUT,check=True)
 m=json.loads((p/f'census{depth}.json').read_text())['modules']['ot_qwen_numeric_stream_queue'];flops={};bits=0
 for c in m['cells'].values():
  if 'dff' in c['type'].lower():
   n=len(c['connections']['Q']);bits+=n;flops[c['type']]=flops.get(c['type'],0)+n
 records.append({'depth':depth,'Q_bits':bits,'cell_flop_bits':flops,'source_sha256':hashlib.sha256((p/'ot_qwen_numeric_stream_queue.sv').read_bytes()).hexdigest(),'yosys':subprocess.check_output([y,'-V'],text=True).strip(),'command':cmd})
(p/'census_receipt.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(records,indent=2))
