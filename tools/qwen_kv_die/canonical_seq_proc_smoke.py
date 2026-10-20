import argparse,json,subprocess,hashlib
from pathlib import Path
from collections import Counter
a=argparse.ArgumentParser();a.add_argument('--models',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--yosys',default='yosys');a=a.parse_args();a.out.mkdir(parents=True,exist_ok=True)
top='module coupon(input CLK,D,RESETN,SETN,output A,Q); DFFASRHQNx1_ASAP7_75t_R a(.CLK(CLK),.D(D),.RESETN(RESETN),.SETN(SETN),.QN(A)); DFFHQNx1_ASAP7_75t_R q(.CLK(CLK),.D(D),.QN(Q)); endmodule\n';(a.out/'coupon.v').write_text(top)
cmd='read_verilog '+str(a.models/'canonical_ASR_normalized.v')+' '+str(a.models/'canonical_DFF_normalized.v')+' '+str(a.out/'coupon.v')+'; hierarchy -check -top coupon; flatten; proc; opt_expr; check -assert; write_json '+str(a.out/'proc.json')+'; async2sync; clk2fflogic; opt_clean; check -assert; write_json '+str(a.out/'lowered.json')
with (a.out/'proc.log').open('w') as h:rc=subprocess.run([a.yosys,'-p',cmd],stdout=h,stderr=subprocess.STDOUT).returncode
assert rc==0,'Yosys model lowering failed'
counts={}
for name in ['proc','lowered']:
 d=json.loads((a.out/(name+'.json')).read_text())['modules']['coupon'];counts[name]=dict(Counter(c['type'] for c in d['cells'].values()));assert all(t.startswith('$') for t in counts[name]),counts[name]
r=dict(pass_proc_async2sync_clk2fflogic=True,yosys=subprocess.check_output([a.yosys,'-V'],text=True).strip(),models={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.models.glob('canonical_*_normalized.v')},cell_inventory=counts);(a.out/'identity.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r),flush=True)
