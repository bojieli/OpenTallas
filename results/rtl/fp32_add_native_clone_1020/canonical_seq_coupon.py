import re,json,hashlib,subprocess,argparse
from pathlib import Path
ap=argparse.ArgumentParser(description='Source-pinned binary functional coupons for ONLY ASAP7 DFFHQNx1 and DFFASRHQNx1, directly against canonical PDK UDPs.')
ap.add_argument('--pdk-seq',required=True,type=Path);ap.add_argument('--pdk-sha256',required=True);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--imported-model',type=Path);a=ap.parse_args()
p=a.out;p.mkdir(parents=True,exist_ok=True);raw=a.pdk_seq.read_text();assert hashlib.sha256(raw.encode()).hexdigest()==a.pdk_sha256,'PDK source identity changed';(p/'canonical_SEQ.v').write_text(raw);udp=re.search(r'primitive altos_dff_sr_0\b.*?endprimitive',raw,re.S).group();license=raw[:raw.index('`')];norm="""// Functional binary-state normalization of the pinned PDK DFFASRHQN UDP.
// RESETN active-low presets inverted Q; SETN active-low clears it.
// Both low clears, per altos_dff_sr_0 and clear_preset_var1=L.
module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);
 wire asr_clear = ~SETN;
 wire asr_set = ~RESETN & SETN;
 always @(posedge CLK or posedge asr_set or posedge asr_clear)
  if(!SETN) QN<=1'b0; else if(!RESETN) QN<=1'b1; else QN<=~D;
endmodule
""";(p/'canonical_ASR_normalized.v').write_text(license+norm)

tb="""module tb;
reg ck=0,d=0,rn=1,sn=1;wire gold,got;integer ini,rv,sv,dv,cv,prev,next,checks=0;
altos_dff_sr_0 refudp(gold,1'b0,ck,~d,~rn,~sn,1'b0);
DFFASRHQNx1_ASAP7_75t_R dut(.CLK(ck),.D(d),.RESETN(rn),.SETN(sn),.QN(got));
initial begin
 for(ini=0;ini<2;ini=ini+1)for(rv=0;rv<2;rv=rv+1)for(sv=0;sv<2;sv=sv+1)for(dv=0;dv<2;dv=dv+1)begin
  ck=0;rn=ini?0:1;sn=ini?1:0;#2;rn=1;sn=1;#2;d=dv;rn=rv;sn=sv;#2;ck=1;#2;
  checks=checks+1;if(gold!==got)begin $display("ASR_UDP_FAIL ini=%0d rn=%0d sn=%0d d=%0d canonical=%b normalized=%b",ini,rv,sv,dv,gold,got);$fatal(1);end
  ck=0;#2;checks=checks+1;if(gold!==got)$fatal(1,"ASR_UDP_FAIL hold");
 end
 for(ini=0;ini<2;ini=ini+1)for(cv=0;cv<2;cv=cv+1)for(dv=0;dv<2;dv=dv+1)for(prev=0;prev<4;prev=prev+1)for(next=0;next<4;next=next+1)begin
  ck=0;rn=ini?0:1;sn=ini?1:0;#2;rn=1;sn=1;#2;d=dv;#2;ck=cv;#2;
  rn=prev[1];sn=prev[0];#2;checks=checks+1;if(gold!==got)begin $display("ASR_TRANS_FAIL previous prev=%b next=%b clk=%b init=%b d=%b gold=%b got=%b",prev[1:0],next[1:0],ck,ini[0],dv[0],gold,got);$fatal(1);end
  rn=next[1];sn=next[0];#2;checks=checks+1;if(gold!==got)begin $display("ASR_TRANS_FAIL prev=%b next=%b clk=%b init=%b d=%b gold=%b got=%b",prev[1:0],next[1:0],ck,ini[0],dv[0],gold,got);$fatal(1);end
  d=~d;#2;checks=checks+1;if(gold!==got)$fatal(1,"ASR_TRANS_FAIL datahold");
  ck=0;#2;checks=checks+1;if(gold!==got)$fatal(1,"ASR_TRANS_FAIL falling");
 end
 $display("ASR_UDP_PASS checks=%0d",checks);$finish;end
endmodule
""";(p/'asr_udp_tb.v').write_text(license+udp+'\n'+tb);cmd=['iverilog','-g2012','-s','tb','-o',str(p/'asr_udp.vvp'),str(p/'asr_udp_tb.v'),str(p/'canonical_ASR_normalized.v')];subprocess.run(cmd,check=True);r=subprocess.run(['vvp',str(p/'asr_udp.vvp')],capture_output=True,text=True);(p/'asr_udp.log').write_text(r.stdout+r.stderr);print(r.stdout,flush=True);assert r.returncode==0
(p/'canonical_model_identity.json').write_text(json.dumps(dict(canonical_SEQ_sha256=hashlib.sha256((p/'canonical_SEQ.v').read_bytes()).hexdigest(),normalized_sha256=hashlib.sha256((p/'canonical_ASR_normalized.v').read_bytes()).hexdigest(),udp_tb_sha256=hashlib.sha256((p/'asr_udp_tb.v').read_bytes()).hexdigest(),checks=544,domain='all binary D/reset states and all16 reset-pair transitions at each stable clock level from each initial q, including both-low releases, data hold, falling clock; notifier/timing violations outside fault-free contract',iverilog=subprocess.check_output(['iverilog','-V'],stderr=subprocess.DEVNULL,text=True).splitlines()[0]),indent=1)+'\n')

udp_plain=re.search(r'primitive altos_dff \(.*?endprimitive',raw,re.S).group()
plain="module DFFHQNx1_ASAP7_75t_R(input CLK,D,output reg QN); always @(posedge CLK) QN<=~D; endmodule\n"
(p/'canonical_DFF_normalized.v').write_text(license+plain)
dtb="""module tb;reg ck=0,d=0;wire gold,got;integer ini,prev,next,checks=0;
altos_dff refudp(gold,1'b0,ck,~d,1'b0);DFFHQNx1_ASAP7_75t_R dut(ck,d,got);
initial begin
 for(ini=0;ini<2;ini=ini+1)for(prev=0;prev<4;prev=prev+1)for(next=0;next<4;next=next+1)begin
  ck=0;d=!ini[0];#2;ck=1;#2;ck=0;#2;d=prev[0];#2;ck=prev[1];#2;
  checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL previous");
  d=next[0];#2;checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL datahold");
  ck=next[1];#2;checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL clock");
  ck=0;#2;checks=checks+1;if(gold!==got)$fatal(1,"DFF_UDP_FAIL falling");
 end
 $display("DFF_UDP_PASS checks=%0d",checks);$finish;end endmodule
"""
(p/'dff_udp_tb.v').write_text(license+udp_plain+'\n'+dtb)
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'dff_udp.vvp'),str(p/'dff_udp_tb.v'),str(p/'canonical_DFF_normalized.v')],check=True)
r=subprocess.run(['vvp',str(p/'dff_udp.vvp')],capture_output=True,text=True);(p/'dff_udp.log').write_text(r.stdout+r.stderr);print(r.stdout,flush=True);assert r.returncode==0
identity=json.loads((p/'canonical_model_identity.json').read_text());identity['plain_dff_checks']=128;identity['plain_dff_model_sha256']=hashlib.sha256((p/'canonical_DFF_normalized.v').read_bytes()).hexdigest();identity['plain_dff_tb_sha256']=hashlib.sha256((p/'dff_udp_tb.v').read_bytes()).hexdigest();identity['scope']='ONLY DFFHQNx1 and DFFASRHQNx1; no other library cells qualified by these coupons';(p/'canonical_model_identity.json').write_text(json.dumps(identity,indent=1)+'\n')

if a.imported_model:
 imported=a.imported_model.read_text();identity=json.loads((p/'canonical_model_identity.json').read_text());identity['imported_model_sha256']=hashlib.sha256(imported.encode()).hexdigest();identity['imported_results']={}
 for tag,typ in [('asr','DFFASRHQNx1_ASAP7_75t_R'),('dff','DFFHQNx1_ASAP7_75t_R')]:
  match=re.search(r'module '+typ+r'\b.*?endmodule',imported,re.S)
  if not match:identity['imported_results'][typ]={'present':False};continue
  model=p/(tag+'_imported.v');model.write_text(match.group()+'\n');exe=p/(tag+'_imported.vvp');subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(p/(tag+'_udp_tb.v')),str(model)],check=True);run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(p/(tag+'_imported.log')).write_text(run.stdout+run.stderr);identity['imported_results'][typ]=dict(present=True,rc=run.returncode,pass_canonical_coupon=run.returncode==0,model_sha256=hashlib.sha256(model.read_bytes()).hexdigest());print(tag,'IMPORTED',run.returncode,flush=True)
 patched=imported
 for typ,file in [('DFFASRHQNx1_ASAP7_75t_R','canonical_ASR_normalized.v'),('DFFHQNx1_ASAP7_75t_R','canonical_DFF_normalized.v')]:
  block=re.search(r'module '+typ+r'\b.*?endmodule',(p/file).read_text(),re.S).group();patched,n=re.subn(r'module '+typ+r'\b.*?endmodule',block,patched,count=1,flags=re.S)
 (p/'library_model_pdk.v').write_text(patched);identity['normalized_library_sha256']=hashlib.sha256(patched.encode()).hexdigest();(p/'canonical_model_identity.json').write_text(json.dumps(identity,indent=1)+'\n')
