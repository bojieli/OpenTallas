#!/usr/bin/env python3
"""Source-extract the full64+16 E3 mechanism; compare ALL bits, including idle/reset.
Golden is immutable859fc source, candidate is exact working source. Not a VM/token gate.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
source=Path('rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv');candidate=source.read_text();gold=subprocess.check_output(['git','show','859fc9132:'+str(source)],text=True)
fields={'gm':1,'f_r0':20,'f_m':80,'f_d':2560,'su_k':192,'su_hit':64,'su_hs':16,'m_row':20,'m_mb':16,'m_data':512,'pl_w':6,'pl_row':120,'pl_mb':96,'pl_data':3072,'ge':4}
# Actual static source shape SQD=1, NK=4, NQ=4.
def wrapper(text,name,enabled):
 begin=text.index('    reg  [NRB-1:0]      bw_we;');end=text.index('    // skid queue state:',begin)
 body=text[begin:end]
 outputs={'bw_we':64,'bw_line':512,'bw_mask':1024,'bw_data':32768,'bw_src':192,'ws_we':16,'ws_line':160,'ws_mask':256,'ws_data':8192}
 pins=['input wire clk,rst_n,input wire[239:0]write_ck']+['input wire[%d:0]%s'%(w-1,n) for n,w in fields.items()]+['input wire[79:0]qrows,input wire[63:0]qmasks,input wire[2047:0]qdatas']+['output wire[%d:0]o_%s'%(w-1,n) for n,w in outputs.items()]
 header='module '+name+'('+','.join(pins)+');\nlocalparam NRB=64,NRBS=16,LAW=8,LAWS=10,RW=20,LNRB=6,LNRBS=4,NB=6,NQ=4,SQD=1,PAR_RB=1,WRITE_LEAVES='+str(enabled)+',WRITE_CLOCKS=1;\ngenvar g;\nwire[19:0]q_row[0:3];wire[15:0]q_mask[0:3];wire[511:0]q_data[0:3];\ngenvar z; generate for(z=0;z<4;z=z+1)begin assign q_row[z]=qrows[z*20+:20];assign q_mask[z]=qmasks[z*16+:16];assign q_data[z]=qdatas[z*512+:512];end endgenerate\n'
 return header+body+'\n'+''.join('assign o_%s=%s;\n'%(n,n)for n in outputs)+'endmodule\n',outputs
w0,outs=wrapper(gold,'gold',0);w1,_=wrapper(candidate,'dut',1)
helper=candidate[candidate.index('module ot_qfd_vm_write_register_t'):]
master=subprocess.check_output(['git','show','859fc9132:rtl/qwen_sys/vm_native_physical_20261015/qvm_bank_banked_native.sv'],text=True);master=master[master.index('module qvm_data256_native'):master.index('module qvm_bank_ctrl_native')]
ports=dict(fields,qrows=80,qmasks=64,qdatas=2048)
tb='module tb;parameter MUT=0;reg clk=0,rst_n=0;wire[239:0]write_ck={240{clk}};\n'+''.join('reg[%d:0]%s;\n'%(w-1,n) for n,w in ports.items())
for k in ['g','d']:tb+=''.join('wire[%d:0]%s_%s;\n'%(w-1,k,n)for n,w in outs.items())
conn='.clk(clk),.rst_n(rst_n),.write_ck(write_ck),'+','.join('.%s(%s)'%(n,n)for n in ports)
for module,k in [('gold','g'),('dut','d')]:tb+=module+' u_'+k+'('+conn+','+','.join('.o_%s(%s_%s)'%(n,k,n)for n in outs)+');\n'
tb+='integer i,j,checks=0;reg[31:0]rng=32\'h31415926;function[31:0]next;input[31:0]x;reg[31:0]y;begin y=x^(x<<13);y=y^(y>>17);next=y^(y<<5);end endfunction\ninitial begin\n'
tb+='for(i=0;i<3000;i=i+1)begin\nclk=0;rst_n=(i%97!=0);\n'
for n,w in ports.items():tb+='for(j=0;j<%d;j=j+1)begin rng=next(rng);%s[j]=rng[0];end\n'%(w,n)
tb+='#3;clk=1;#2;\n'
for n in outs:tb+='if(g_%s !== d_%s)begin $display("FAIL %s cycle%%0d",i);$fatal;end\n'%(n,n,n)
tb+='checks=checks+43184;end\n$display("PASS exact E3 all43184bits checks%0d",checks);$finish;end endmodule\n'
# Mutant corrupts actual selected half-data connectivity, proving every payload comparison live.
mut=helper.replace('.d(data[511:256])','.d(data[255:0])',1)
(a.out/'design.sv').write_text('`define OT_QFD_VM_PARTITIONED_CLOCKS\n'+w0+w1+helper+master)
results=[]
for m,h in [(0,helper),(1,mut)]:
 f=a.out/f'm{m}.sv';f.write_text('`define OT_QFD_VM_PARTITIONED_CLOCKS\n'+w0+w1+h+master+tb)
 binary=a.out/f'm{m}.vvp';build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(f)],text=True,capture_output=True);(a.out/f'm{m}.build.log').write_text(build.stdout+build.stderr);assert build.returncode==0,build.stderr
 run=subprocess.run(['vvp',str(binary)],text=True,capture_output=True);(a.out/f'm{m}.run.log').write_text(run.stdout+run.stderr);assert (run.returncode==0)==(m==0),run.stdout
 results.append(dict(mutant=m,exit=run.returncode,output=run.stdout.strip()))
summary=dict(scope='source-exact full64BW+16WS E3 component only; no fullVM/native token/physical claim',golden_commit='859fc9132',candidate_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),golden_sha256=hashlib.sha256(gold.encode()).hexdigest(),results=results)
(a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
