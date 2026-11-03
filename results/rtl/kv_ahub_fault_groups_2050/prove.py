from pathlib import Path
import argparse, importlib.util, hashlib, json, subprocess, sys
parser=argparse.ArgumentParser(description='Reproduce the same-edge fault coupon on an explicit actual AHUB source')
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
parser.add_argument('--helper',type=Path,default=Path(__file__).resolve().parents[3]/'physical/die_plan/qwen_kvsys/cores/harden/ahub_fault_groups.py')
a=parser.parse_args()
root=a.out.resolve(); root.mkdir(parents=True,exist_ok=False)
spec=importlib.util.spec_from_file_location('fg',a.helper);fg=importlib.util.module_from_spec(spec);spec.loader.exec_module(fg)
src=a.source.read_text(); out=fg.factor_fault_capture(src,'qkd_ahub_static_core_la_ck7');(root/'candidate.sv').write_text(out)
old=fg.OLD_CAPTURE.replace('gqv[2]','gq')
new=fg.NEW_CAPTURE.replace('gqv[2]','cq[0]').replace('gqv[5+4*fg_a+fg_s]','cq[1+4*fg_a+fg_s]')
base='''module m(input clk,rst_n,m_issue, input [15:0] lm_seen, input [3:0] issue,done_seen,input [255:0] zflat,input [63:0] zmask,input start_q,sq,act_q,other_fault, output eq);
wire [63:0] zseen[0:3];
for(genvar a=0;a<4;a=a+1) assign zseen[a]=zflat[64*a+:64];
reg gq;reg [16:0] cq;reg gf,cf;
always @(posedge clk or negedge rst_n) if(!rst_n)gq<=0;else begin
'''+old+'''
end
always @(posedge clk or negedge rst_n) if(!rst_n)cq<=0;else begin
'''+new+'''
end
wire captured=CAPTURED;
always @(posedge clk or negedge rst_n)if(!rst_n)gf<=0;else if(start_q)gf<=sq;else if(act_q&&(gq||other_fault))gf<=1;
always @(posedge clk or negedge rst_n)if(!rst_n)cf<=0;else if(start_q)cf<=sq;else if(act_q&&(captured||other_fault))cf<=1;
assign eq=(gq==captured)&&(gf==cf);
endmodule
'''
res={}
for name,cap in [('normal','(|cq)'),('mutant','(|cq[15:0])')]:
 (root/f'{name}.sv').write_text(base.replace('CAPTURED',cap))
 command=f'read_verilog -sv {name}.sv; hierarchy -top m; proc; flatten; async2sync; opt; sat -seq 3 -tempinduct -set-init-zero -prove eq 1 -verify -show-inputs -show-outputs'
 p=subprocess.run(['yosys','-Q','-p',command],cwd=root,text=True,capture_output=True)
 (root/f'{name}.log').write_text(p.stdout+p.stderr);res[name]={'returncode':p.returncode,'proved':'SUCCESS!' in p.stdout,'counterexample':'FAIL!' in p.stdout}
res['actual_source_sha256']=hashlib.sha256(src.encode()).hexdigest();res['candidate_sha256']=hashlib.sha256(out.encode()).hexdigest();res['added_flops']=16;res['cycles_added']=0
(root/'result.json').write_text(json.dumps(res,indent=2)+'\n')
assert res['normal']['returncode']==0 and res['normal']['proved'],res
assert res['mutant']['returncode']!=0 and res['mutant']['counterexample'],res
print(json.dumps(res))
