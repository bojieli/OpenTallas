from pathlib import Path
import json,subprocess,hashlib
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--gate-dir',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args();G=args.gate_dir;O=args.out;O.mkdir(parents=True,exist_ok=False);R=args.root
ports=json.loads((G/'full0/original.json').read_text())['modules']['ot_qwen_rom_core']['ports'];indices={n:i for i,n in enumerate(ports)}
fields=sorted(n for n in ports if n.startswith('u_me.i_'));width=sum(len(ports[n]['bits']) for n in fields);assert width==379
s=(G/'full_tb.sv').read_text();x=[]
for d in [0,1]:
 sig=lambda n:f'o{d}_{indices[n]}'
 payload='{'+','.join(sig(n) for n in fields)+'}'
 x+=[f'wire[378:0] broadcast{d};wire broadcast_valid{d};',
 f'ot_hdc_delay #(.W(379),.D(1)) bi{d}(.clk({sig("u_me.clk")}),.rst_n(rst_n),.d({payload}),.q(broadcast{d}));',
 f'ot_hdc_delay #(.W(1),.D(1),.RESET(1)) bg{d}(.clk({sig("u_me.clk")}),.rst_n(rst_n),.d({sig("u_me.go")} && (bm{d}==0)),.q(broadcast_valid{d}));']
x+=['integer broadcast_checks=0;always @(negedge clk)begin if(!rst_n)broadcast_checks=0;else begin if(broadcast_valid0!==broadcast_valid1)$fatal(1,"broadcast valid mismatch");if(broadcast_valid0)begin if(broadcast0!==broadcast1)$fatal(1,"broadcast packet mismatch");broadcast_checks=broadcast_checks+1;end end end']
s=s.replace('\nendmodule\n','\n'+'\n'.join(x)+'\nendmodule\n',1)
s=s.replace('$display("PASS full controller','$display("BROADCAST checks=%0d",broadcast_checks);if(broadcast_checks<32)$fatal(1,"broadcast coverage");$display("PASS full controller')
(O/'tb.sv').write_text(s);rows=[]
for stall,neg in [(0,0),(1,0),(0,2)]:
 name=f's{stall}_n{neg}'
 cmd=['iverilog','-g2012','-I'+str(R/'rtl/hdc'),'-s','tb',f'-Ptb.STALL={stall}',f'-Ptb.NEG={neg}','-o',str(O/name),str(G/'core0.v'),str(G/('core_bad.v' if neg else 'core1.v')),str(O/'tb.sv'),str(R/'rtl/hdc/ot_hdc_delay.sv'),str(R/'rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv'),str(R/'rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv'),str(R/'rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv')]
 r=subprocess.run(cmd,text=True,capture_output=True);(O/(name+'.compile.log')).write_text(r.stdout+r.stderr);r.check_returncode()
 r=subprocess.run(['vvp',str(O/name)],text=True,capture_output=True);(O/(name+'.log')).write_text(r.stdout+r.stderr)
 passed=(r.returncode==0 and 'BROADCAST checks=32' in r.stdout) if not neg else (r.returncode!=0 and 'broadcast packet mismatch' in r.stdout)
 rows.append(dict(stall=stall,negative=neg,passed=passed,output=r.stdout));print(rows[-1])
j=dict(status='pass' if all(x['passed'] for x in rows) else 'fail',scope='One actual379-bit instruction broadcast stage and matching go delay at actual source-derived gated ME clocks; full controller, real KV bridge retained. Existing41 stages compose the same identity; no engine arithmetic simulation.',rows=rows,source_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),O/'tb.sv',R/'rtl/hdc/ot_hdc_delay.sv',R/'rtl/hdc/ot_qwen_me_array_w12.sv']});(O/'result.json').write_text(json.dumps(j,indent=2)+'\n');assert j['status']=='pass'
