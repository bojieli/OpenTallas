#!/usr/bin/env python3
"""Prove the exact source credit function for all counts and legal lengths."""
import hashlib,json,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[2]
src=root/'rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv'
s=src.read_text();function=re.search(r'    function automatic credit_room\(.*?    endfunction',s,re.S).group()
out=Path('../credit_sat').resolve();out.mkdir(exist_ok=True)
rows=[]
for depth,mut in [(32,False),(64,False),(128,False),(64,True)]:
 f=function.replace('(len<=3)','(len<=2)')if mut else function
 tag=f'qd{depth}'+('_mutant'if mut else '')
 h=out/(tag+'.sv')
 h.write_text(f'''module tb(input wire[{depth.bit_length()-1}:0]n,input wire[3:0]len,output wire ok);
 localparam integer QD={depth},QW={depth.bit_length()-1};
{f}
 wire original=(32'(n)+32'(len))<=QD;
 assign ok=(len<1||len>4)||(original==credit_room(n,len));
endmodule
''')
 cmd=['yosys','-p',f'read_verilog -sv {h}; prep -top tb; sat -verify -prove ok 1 -show n,len']
 r=subprocess.run(cmd,text=True,capture_output=True);log=r.stdout+r.stderr
 (out/(tag+'.log')).write_text(log)
 gate=(r.returncode!=0 and 'proof did fail' in log)if mut else(r.returncode==0 and 'SUCCESS' in log)
 rows.append(dict(depth=depth,mutant=mut,returncode=r.returncode,pass_gate=gate,harness_sha256=hashlib.sha256(h.read_bytes()).hexdigest()))
x=dict(schema='opentallas.bw_credit_source_sat.v1',rtl_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),function_sha256=hashlib.sha256(function.encode()).hexdigest(),tool=subprocess.check_output(['yosys','-V'],text=True).strip(),cases=rows)
(out/'receipt.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x));assert all(r['pass_gate']for r in rows)
