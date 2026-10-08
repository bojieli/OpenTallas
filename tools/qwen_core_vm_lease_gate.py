from pathlib import Path
import re,subprocess,json,hashlib
from qwen_core_vm_lease import apply
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--core-source',type=Path,required=True);args=ap.parse_args()
P=args.out.resolve();P.mkdir(parents=True,exist_ok=False);source=args.core_source.resolve()
s=apply(source.read_text());(P/'core_leased.sv').write_text(s)
eq='\n'.join(re.findall(r'    assign (?:me_en|vm_me_wanted) = .*?;',s,re.S));assert eq.count('assign')==2
body='''module cone #(parameter VM_OWNED_LEASE=1,ME_STALL=1,ME_IDLE_GATE=1)(input rst_n_i,me_mem_ok_i,me_idle,me_wake,vm_me_lease,output me_en,vm_me_wanted);\n'''+eq+'\nendmodule\n'
tb='''module tb #(parameter NEG=0);reg r,m,i,w,l;wire e,intent;integer k,n=0;reg expected;
cone #(.VM_OWNED_LEASE(NEG?0:1)) dut(r,m,i,w,l,e,intent);
initial begin
for(k=0;k<32;k=k+1)begin {r,m,i,w,l}=k;#1;
 expected=!r||(m&&(!i||w));
 if(intent!==expected)$fatal(1,"original enable altered");
 if(e!==(!r||(expected&&l)))$fatal(1,"unpaid ME edge");n=n+1;end
// CAP with no ME frame followed by original intent rise and ADMIT without ME lease.
r=1;m=0;i=0;w=0;l=0;#1;if(intent!==0)$fatal; m=1;#1;
if(intent!==1||e!==0)$fatal(1,"unpaid held-frame intent rise");
l=1;#1;if(e!==1)$fatal(1,"paid ME edge missing");
$display("PASS direct lease enable truth table32 + held-frame intent rise");$finish;end endmodule\n'''
(P/'lease_cone.sv').write_text(body+tb);rows=[]
for neg in [0,1]:
 r=subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.NEG={neg}','-o',str(P/f'lease{neg}'),str(P/'lease_cone.sv')],capture_output=True,text=True);r.check_returncode()
 r=subprocess.run(['vvp',str(P/f'lease{neg}')],capture_output=True,text=True);(P/f'lease{neg}.log').write_text(r.stdout+r.stderr)
 rows.append(dict(negative=neg,passed=(r.returncode==0 if not neg else r.returncode!=0 and 'unpaid ME edge' in r.stdout),output=r.stdout))
j=dict(status='pass' if all(x['passed'] for x in rows) else 'fail',cases=rows,scope='Actual emitted enable equation with direct opt-in lease; Boolean component only, not gated-clock or ACK FSM integration',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,Path(__file__).with_name('qwen_core_vm_lease.py'),P/'core_leased.sv',P/'lease_cone.sv',Path(__file__)]});(P/'lease_result.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2));assert j['status']=='pass'
