from pathlib import Path
import sys,re,json,hashlib,subprocess
P=Path(__file__).parent;R=Path('/home/ubuntu/OpenTallas')
sys.path.insert(0,str(P))
from qwen_core_vm_raw_boundary import apply
src=Path('/tmp/qwen-core-kv-boundary-20261007/final_gate/full1/core.sv')
normal=Path('/tmp/qwen-vm-normalizer-return-20261007/normalizer.sv')
cap=Path('/tmp/qwen-vm-rom-ingress-20261007/capture.sv')
base=src.read_text();raw=apply(base);(P/'core_raw.sv').write_text(raw)
# Verify all payloads are actual engine output port connections, with no altered payload logic.
for signal in ['vw_me_addr','vw_me_mask','vw_me_data','vw_mx_addr','vw_mx_mask','vw_mx_data']:
 assert len(re.findall(r'\.\w+\('+signal+r'\)',base))==1,signal
cones=[]
for n,text in enumerate([base,raw]):
 eq='\n'.join(re.findall(r'    assign vw_(?:me|mx)_we = [^;]+;',text));assert eq.count('assign')==2
 cones.append(f'''module core_boundary{n}(input wire[47:0]me_o_we,input wire me_mx_we,me_en,output wire[47:0]vw_me_we,output wire vw_mx_we);
localparam G=6144,SMIN=7,VM_OWNED_RAW={n};
{eq}
endmodule\n''')
(P/'cones.sv').write_text(''.join(cones))
tb='''module tb #(parameter NEG=0);
import ot_gpu_w6_secded_pkg::*;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,wanted=0,owned=0,lease=0;
reg[48:0]we;reg[49*24-1:0]addr;reg[49*16-1:0]mask;reg[865*32-1:0]data;
wire[48:0]cw0,cw1;wire[864:0]en0,en1;
wire[865*32-1:0]wa0,wa1,wd0,wd1;reg[865*24-1:0]a0,a1;
core_boundary0 b0(we[47:0],we[48],wanted,cw0[47:0],cw0[48]);
core_boundary1 b1(we[47:0],we[48],wanted,cw1[47:0],cw1[48]);
'''
for d in [0,1]:
 tb+=f'''ot_qwen_rom_vm_request_normalizer #(.ENABLE(1)) n{d}(
 .me_wanted(1'b1),.scalar_re(2240'd0),.scalar_raddr(53760'd0),.seq_re(1'b0),.seq_rword(16'd0),
 .word_we(cw{d}),.word_waddr(addr),.word_wmask(mask),.scalar_we(65'd0),.scalar_waddr(1560'd0),
 .seq_we(1'b0),.seq_wword(16'd0),.ordered_write_data(data),.backend_read_data(72192'd0),
 .write_en(en{d}),.write_addr(wa{d}),.write_data(wd{d}));
 always @* begin for(integer j{d}=0;j{d}<865;j{d}=j{d}+1)a{d}[j{d}*24+:24]=wa{d}[j{d}*32+:24]; end
 capture c{d}(.clk(clk),.rst_n(rst_n),.source_me_wanted({"1'b1" if d==0 else "(NEG==1 ? wanted&&lease : NEG==2 ? 1'b1 : wanted)"}),.owned_capture(owned),
 .raw_read_en(2256'd0),.raw_read_zero(2256'd0),.read_addr(54144'd0),.raw_write_en(en{d}),.write_addr(a{d}),.write_data(wd{d}));
'''
tb+='''integer i,f,k,checks=0;reg[71:0]held[0:864];reg[65:0]decoded;
// Full packet alternative includes every ME/MX word's enable, address, mask and data.
reg[49*553-1:0]fallback;reg[553-1:0]packet;reg[864:0]expect_en;
initial begin
we=0;addr=0;mask=0;data=0;repeat(2)@(negedge clk);rst_n=1;
for(f=0;f<8;f=f+1)begin
 wanted=f%2;lease=0;
 for(i=0;i<49;i=i+1)begin
  we[i]=((i+f)%3!=0);addr[i*24+:24]=((i+f)%7==0)?24'hffffff:((i+f)%5==0)?65536:i*19+f;
  mask[i*16+:16]=16'hf0a5^(f<<i%8);
  for(k=0;k<16;k=k+1)data[(i*16+k)*32+:32]=32'hb0000000+i*256+k+f;
  // Baseline packet-stage acceptance at the same source epoch.
  fallback[i*553+:553]={we[i]&&wanted,addr[i*24+:24],mask[i*16+:16],data[i*512+:512]};
 end
 owned=1;@(negedge clk);owned=0;
 for(i=0;i<865;i=i+1)begin
  if(a0[i*24+:24]!==wa0[i*32+:24] || a1[i*24+:24]!==wa1[i*32+:24])$fatal(1,"address packing changed");
  if(c0.write_seat[i]!==c1.write_seat[i])$fatal(1,"core/collar epoch mismatch frame%0d slot%0d",f,i);
  held[i]=c1.write_seat[i];decoded=decode64(held[i]);
  if(i<784)begin
   packet=fallback[(i/16)*553+:553];
   expect_en[i]=packet[552]&&packet[512+i%16]&&(packet[528+:24]<65536);
   if(decoded[56]!==expect_en[i]||decoded[31:0]!==packet[(i%16)*32+:32])$fatal(1,"fallback payload mismatch");
   if(decoded[56]&&decoded[55:32]!==((packet[528+:24]<<4)+(i%16)))$fatal(1,"fallback address mismatch");
  end
  checks=checks+1;
 end
 // Held epoch immunity, including dropping original enable while admission lease stays low.
 wanted=~wanted;data=~data;addr=~addr;mask=~mask;we=~we;
 repeat(3)@(negedge clk);
 for(i=0;i<865;i=i+1)if(c1.write_seat[i]!==held[i])$fatal(1,"held packet changed");
end
$display("PASS actual core equations/full normalizer/protected CAP cone checks=%0d held packets exact; full-packet fallback stream exact",checks);$finish;
end
endmodule
'''
(P/'tb.sv').write_text(tb)
rows=[]
for neg in [0,1,2]:
 cmd=['iverilog','-g2012','-s','tb',f'-Ptb.NEG={neg}','-o',str(P/f'sim{neg}'),str(R/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'),str(P/'cones.sv'),str(normal),str(cap),str(P/'tb.sv')]
 r=subprocess.run(cmd,capture_output=True,text=True);(P/f'compile{neg}.log').write_text(r.stdout+r.stderr);r.check_returncode()
 r=subprocess.run(['vvp',str(P/f'sim{neg}')],capture_output=True,text=True);(P/f'run{neg}.log').write_text(r.stdout+r.stderr)
 passed=(r.returncode==0 and 'PASS actual core' in r.stdout) if neg==0 else (r.returncode!=0 and 'core/collar epoch mismatch' in r.stdout)
 rows.append(dict(negative=neg,passed=passed,exit=r.returncode,output=r.stdout));print(rows[-1])
record=dict(status='pass' if all(x['passed'] for x in rows) else 'fail',cases=rows,
 scope='Actual emitted full-shape core two write equations and unchanged engine payload wires, full49word/865seat normalizer and source-extracted protected CAP cone. Not full controller or ACK FSM/clock enrollment.',
 source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,P/'core_raw.sv',P/'qwen_core_vm_raw_boundary.py',normal,cap,P/'cones.sv',P/'tb.sv',Path(__file__)]},
 unresolved=['Original pre-lease source enable exported independently of VM lease','Actual wrapper CAP event and all native source clocks enrollment','Atomic binding of raw core+normalizer+collar','Actual core and collar SS/FF physical closure'])
(P/'result.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['status']=='pass'
