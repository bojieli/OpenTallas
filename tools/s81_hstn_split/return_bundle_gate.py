#!/usr/bin/env python3
"""Exact generated six-lane forwarded station identity/edge proof plus mutant."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import dsrom_s81_fulldie as G
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();o=a.out.resolve();o.mkdir(parents=True,exist_ok=True)
ports={}
for i in range(6):ports.update({f'fi{i}':('input',1),f'di{i}':('input',70),f'fo{i}':('output',1),f'do{i}':('output',70)})
master='dsfd_stnv_70x6_proof';rtl=G.glue_rtl({'pdir':{master:ports},'glue':{}})
conna=[];connb=[]
for i in range(6):
 conna += [f'.fi{i}(ck[{i}])',f'.di{i}(data[{i}])',f'.fo{i}(fa[{i}])',f'.do{i}(da[{i}])']
 connb += [f'.fi{i}(fa[{i}])',f'.di{i}(da[{i}])',f'.fo{i}(fb[{i}])',f'.do{i}(db[{i}])']
tb='''`timescale 1ns/1ps
module tb;
reg [5:0] ck=0; reg [69:0] data[0:5]; wire [5:0] fa,fb; wire [69:0] da[0:5],db[0:5];
reg [69:0] ea[0:5]; integer seen[0:5];integer checks=0;integer n,l,b;reg [31:0] rng=32'h6c616e65;
'''+master+' a('+','.join(conna)+');\n'+master+' u_second('+','.join(connb)+');\n'+'''
genvar g; generate for(g=0;g<6;g=g+1) begin:lane
 initial begin #(0.1*g);forever #4.166 ck[g]=~ck[g];end
 always @(negedge ck[g])begin
  ea[g]=data[g];seen[g]=1;#0.001;
  if(da[g]!==ea[g]||fa[g]!==~ck[g])$fatal(1,"RETURN_BUNDLE FAIL first edge lane=%0d",g);checks=checks+1;
 end
 always @(posedge ck[g])begin
  #0.001;if(seen[g])begin
   if(db[g]!==ea[g]||fb[g]!==ck[g])$fatal(1,"RETURN_BUNDLE FAIL second edge lane=%0d",g);checks=checks+1;
  end
 end
end endgenerate
initial begin
 for(l=0;l<6;l=l+1)begin data[l]=0;seen[l]=0;ea[l]=0;end
 for(n=0;n<2188;n=n+1)begin
  #17;
  for(l=0;l<6;l=l+1)begin
   if(n<140)begin data[l]=(n<70)?70'b0:{70{1'b1}};data[l][n%70]=(n<70);data[l][(n+7*l)%70]=~data[l][(n+7*l)%70];end
   else for(b=0;b<70;b=b+1)begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);data[l][b]=rng[0];end
  end
 end
 #20;if(checks<50000)$fatal(1,"RETURN_BUNDLE FAIL coverage %0d",checks);
 $display("RETURN_BUNDLE PASS lanes=6 bits=70 depth=2 checks=%0d",checks);$finish;
end
endmodule
'''
(o/'tb.sv').write_text(tb);runs=[];needle='.i_d(di3[69:0])';assert rtl.count(needle)==1
for kind,src in [('exact',rtl),('lane3_wrong_source',rtl.replace(needle,'.i_d(di2[69:0])'))]:
 f=o/(kind+'.sv');f.write_text(src);c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(o/(kind+'.vvp')),str(R/'rtl/common/ot_fwd_link_stage.sv'),str(f),str(o/'tb.sv')],capture_output=True,text=True);assert c.returncode==0,c.stderr
 r=subprocess.run(['vvp',str(o/(kind+'.vvp'))],capture_output=True,text=True);(o/(kind+'.log')).write_text(r.stdout+r.stderr)
 ok=(r.returncode==0 and 'RETURN_BUNDLE PASS' in r.stdout) if kind=='exact' else(r.returncode!=0 and 'RETURN_BUNDLE FAIL' in r.stdout);assert ok,(kind,r.stdout)
 runs.append({'kind':kind,'exit':r.returncode,'expected_result_observed':ok,'generated_sha256':hashlib.sha256(src.encode()).hexdigest()})
receipt={'status':'PASS','scope':'Actual glue_rtl six independent70-bit forwarded lanes, two actual primitive stages, six equal-frequency phase offsets. Edge/identity proof only; physical clock phase, CTS and pin timing remain unqualified.','mutant':'Lane3 input reads lane2 instead of its own source; all real primitives and clocks preserved.','runs':runs,'source_sha256':{str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in [Path(__file__),R/'tools/dsrom_s81_fulldie.py',R/'rtl/common/ot_fwd_link_stage.sv']}}
(o/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt,indent=1))
