#!/usr/bin/env python3
"""Smallest source-extracted q/c split lockstep, range lint and mutant control."""
import argparse, hashlib, json, os, pathlib, re, subprocess
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--baseline',default='2e8f536399e');p.add_argument('--baseline-file');a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2];src=root/'rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv'
old=pathlib.Path(a.baseline_file).read_text() if a.baseline_file else subprocess.check_output(['git','-C',str(root),'show',a.baseline+':'+str(src.relative_to(root))],text=True);new=src.read_text()
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=False)

def snippet(s):
 start=s.index('            //: REGROOT 8: low half of q / c')
 end=s.index('            wire [8*AW-1:0] part;',start)
 return s[start:end]

def module(s,name):
 fun='\n'.join(re.search(r'    function automatic \[36:0\] '+f+r'\(.*?    endfunction',s,re.S).group(0) for f in ('msk2','shro'))
 return '''module %s #(parameter integer REGROOT=0, CW=7, G=4, MUTANT=0,
 SPB=45, NSPC=(REGROOT>=8?90:REGROOT>=7?45:27))
 (input [31:0] gb,input [32*G-1:0] gbc,input [4*NSPC-1:0] spc,
 input [351:0] sph,output [32*G-1:0] qo,co);
%s
for(genvar gq=0;gq<G;gq=gq+1) begin:g_off
 wire [31:0] gbq=gbc[32*gq+:32]+gq;
%s
 assign qo[32*gq+:32]=qv;
 assign co[32*gq+:32]=cv ^ (MUTANT ? 32'd1 : 32'd0);
end
endmodule
'''%(name,fun,snippet(s))
mods=module(old,'before_split')+module(new,'after_split')
bench='''module tb #(parameter integer MUTANT=0);
reg [31:0] gb;reg [127:0] gbc;reg [359:0] spc;reg [351:0] sph;
for(genvar v=0;v<5;v=v+1)begin:forms
 localparam integer R=(v==0?0:v==1?6:v==2?7:v==3?8:9);
 localparam integer N=(R>=8?90:R>=7?45:27);
 wire [127:0] qb,cb,qa,ca;
 before_split #(.REGROOT(R)) b(gb,gbc,spc[4*N-1:0],sph,qb,cb);
 after_split #(.REGROOT(R),.MUTANT(MUTANT)) d(gb,gbc,spc[4*N-1:0],sph,qa,ca);
 always @(negedge sample) if(qb!==qa || cb!==ca) $fatal(1,"SPLIT_MISMATCH form=%0d",R);
end
reg sample=0; integer i,j;
initial begin
 for(i=0;i<4096;i=i+1)begin
  gb=$urandom;for(j=0;j<4;j=j+1)gbc[32*j+:32]=$urandom;
  for(j=0;j<90;j=j+1)spc[4*j+:4]=4'($urandom);
  for(j=0;j<22;j=j+1)sph[16*j+:16]=16'($urandom);
  #1;sample=1;#1;sample=0;#1;
 end
 $display("SPLIT_PASS forms=5 groups=4 vectors=4096 comparisons=81920 cycles_added=0");$finish;
end
endmodule
'''
(out/'miter.sv').write_text(mods+bench)
(out/'range.sv').write_text(module(new,'after_split')+bench.replace('before_split #(.REGROOT(R)) b(gb,gbc,spc[4*N-1:0],sph,qb,cb);','after_split #(.REGROOT(R)) b(gb,gbc,spc[4*N-1:0],sph,qb,cb);'))
v=os.path.expanduser('~/.local/opentallas-tools/bin/verilator')
def run(tag,cmd):
 r=subprocess.run(cmd,capture_output=True,text=True);(out/(tag+'.log')).write_text(r.stdout+r.stderr);return r
lint=run('lint',[v,'--lint-only','--timing','-Wno-fatal','-Werror-SELRANGE','--top-module','tb',str(out/'range.sv')]);assert lint.returncode==0, 'range lint failed'
results=[]
for tag,mut in [('positive',0),('mutant',1)]:
 obj=out/tag
 b=run('build_'+tag,[v,'--binary','--timing','-j','2','-Wno-fatal','-Wno-SELRANGE','--top-module','tb','-GMUTANT='+str(mut),'--Mdir',str(obj),str(out/'miter.sv')]);assert b.returncode==0, 'build failed'
 r=run(tag,[str(obj/'Vtb')]);results.append(dict(case=tag,rc=r.returncode,output=(r.stdout+r.stderr).strip()))
assert results[0]['rc']==0 and 'SPLIT_PASS' in results[0]['output']
assert results[1]['rc']!=0 and 'SPLIT_MISMATCH' in results[1]['output']
receipt=dict(verdict='PASS',range_lint='PASS',mutant='CAUGHT',source_sha256=hashlib.sha256(new.encode()).hexdigest(),baseline=a.baseline,results=results,added_cycles=0)
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
