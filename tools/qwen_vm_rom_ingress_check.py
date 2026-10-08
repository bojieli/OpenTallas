import pathlib,re,subprocess,json,hashlib
import argparse
p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,default=pathlib.Path('/home/ubuntu/OpenTallas'));p.add_argument('--out',type=pathlib.Path,default=pathlib.Path('/tmp/qwen-vm-rom-ingress-20261007'));p.add_argument('--adapter',type=pathlib.Path);a=p.parse_args();O=a.out;R=a.root;O.mkdir(parents=True,exist_ok=True);src=(a.adapter or O/'generated/ot_qwen_rom_vm_ingress_adapter.sv').read_text()
qual=src[src.index('    // Raw intents'):src.index('    localparam integer TAGW')]
start=src.index('                    for(integer k=0;k<NR;k=k+1)\n                        read_seat[k]<=encode64({6\'b0')
end=src.index('                    me_frame<=source_me_wanted;',start)
capture=src[start:end]
header='''module capture(input wire clk,rst_n,source_me_wanted,owned_capture,
input wire[2255:0]raw_read_en,raw_read_zero,input wire[2256*24-1:0]read_addr,
input wire[864:0]raw_write_en,input wire[865*24-1:0]write_addr,input wire[865*32-1:0]write_data);
import ot_gpu_w6_secded_pkg::*;
localparam ROM_INGRESS=1,NR=2256,NW=865,VX0=208,NVX=2048,HEAD_CACHE=0,W1_FRAME=0;
reg[71:0]read_seat[0:NR-1],write_seat[0:NW-1];
'''
reset="for(integer k=0;k<NR;k=k+1)read_seat[k]<=encode64(64'b0);\nfor(integer k=0;k<NW;k=k+1)write_seat[k]<=encode64(64'b0);"
body=header+qual+'\nalways @(posedge clk)begin if(!rst_n)begin\n'+reset+'\nend else if(owned_capture)begin\n'+capture+'\nend end\nendmodule\n'
(O/'capture.sv').write_text(body)
tb='''module tb;
import ot_gpu_w6_secded_pkg::*;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,source_me_wanted=0,owned_capture=0;
reg[2255:0]raw_read_en,raw_read_zero;reg[2256*24-1:0]read_addr;
reg[864:0]raw_write_en;reg[865*24-1:0]write_addr;reg[865*32-1:0]write_data;
capture dut(.*);
integer i,pass,n=0;reg[65:0]d;reg want;reg[71:0]held;
initial begin
raw_read_en='1;raw_read_zero=0;raw_write_en='1;
for(i=0;i<2256;i=i+1)read_addr[i*24+:24]=i;
for(i=0;i<865;i=i+1)begin write_addr[i*24+:24]=i;write_data[i*32+:32]=32'hface0000+i;end
repeat(2)@(negedge clk);rst_n=1;
for(pass=0;pass<2;pass=pass+1)begin
source_me_wanted=pass;owned_capture=1;@(negedge clk);owned_capture=0;
for(i=0;i<865;i=i+1)begin
 d=decode64(dut.write_seat[i]);want=(i>=784)||source_me_wanted;
 if(d[65]||d[56]!==want||d[55:32]!==i||d[31:0]!==32'hface0000+i)$fatal(1,"capture writer qualifier slot%0d",i);n=n+1;
end
for(i=0;i<2256;i=i+1)begin
 d=decode64(dut.read_seat[i]);want=(i<208)||source_me_wanted;
 if(d[65]||d[56]!==want||d[57]!==0||d[55:32]!==i)$fatal(1,"capture read qualifier slot%0d",i);n=n+1;
end
end
// Captured ME strobes/data must not be requalified by a later me intent.
held=dut.write_seat[35*16];source_me_wanted=0;write_data=0;
repeat(3)@(negedge clk);if(dut.write_seat[35*16]!==held)$fatal(1,"captured ME packet requalified");
// Zero-only invalid read is owned metadata, not an empty frame.
raw_read_en=0;raw_write_en=0;raw_read_zero='1;source_me_wanted=1;owned_capture=1;
@(negedge clk);owned_capture=0;
for(i=0;i<2256;i=i+1)begin d=decode64(dut.read_seat[i]);if(d[65]||d[56]!==0||d[57]!==1||d[31:0]!==0)$fatal(1,"zero flag lost");n=n+1;end
// Source changes on held service edges cannot mutate the owned protected seat.
held=dut.read_seat[208];raw_read_zero=0;read_addr=0;source_me_wanted=0;
repeat(3)@(negedge clk);if(dut.read_seat[208]!==held)$fatal(1,"owned frame recaptured");
// The new zero flag occupies the same SECDED-protected payload as enable/address.
d=decode64(held^72'd1);if(d[65]||d[57]!==1)$fatal(1,"single bit not corrected");
d=decode64(held^72'd3);if(!d[65])$fatal(1,"double bit not rejected");
$display("PASS existing-seat capture checks=%0d held ownership and protected zero metadata",n);$finish;
end
endmodule
'''
(O/'bench.sv').write_text(tb)
results=[]
for name in ['positive','bypass_me','omit_zero']:
 v=body
 if name=='bypass_me':v=v.replace('(!ROM_INGRESS || ingress>=784 || source_me_wanted)',"1'b1")
 if name=='omit_zero':v=v.replace("{6'b0,zero_intent[k],read_en[k]", "{6'b0,1'b0,read_en[k]")
 d=O/(name+'_hold');d.mkdir(exist_ok=True);(d/'capture.sv').write_text(v)
 cmd=['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(R/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'),str(d/'capture.sv'),str(O/'bench.sv')]
 p=subprocess.run(cmd,text=True,capture_output=True);(d/'build.log').write_text(p.stdout+p.stderr);p.check_returncode()
 p=subprocess.run(['vvp',str(d/'sim')],text=True,capture_output=True);(d/'run.log').write_text(p.stdout+p.stderr);assert (p.returncode==0)==(name=='positive'),p.stdout
 results.append(dict(name=name,exit=p.returncode,log=p.stdout));print(name,p.stdout)
(O/'gate_hold.json').write_text(json.dumps(dict(scope='Full2256/865 actual source-extracted protected CAP seat capture only. owned_capture is the parent CAP event input, not a tested full adapter ACK/admission FSM. Epoch remains existing adapter responsibility.',capture_slice_sha256=hashlib.sha256(capture.encode()).hexdigest(),cases=results),indent=2)+'\n')
