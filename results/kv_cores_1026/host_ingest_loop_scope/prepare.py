from pathlib import Path
import subprocess,json,sys
wt=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True,parents=True)
rel='rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv'
gold=subprocess.check_output(['git','-C',str(wt),'show','1d85ca644:'+rel],text=True)
(out/'gold.sv').write_text(gold.replace('module qkd_host_native_engine #','module qkd_host_native_engine_gold #'))
(out/'candidate.sv').write_bytes((wt/rel).read_bytes())
for f in ('rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv','physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v'):
 (out/Path(f).name).write_bytes(subprocess.check_output(['git','-C',str(wt),'show','HEAD:'+f]))
ports={'d_rdy':1,'in_rdy':1,'w_v':1,'w_addr':32,'w_data':256,'r_v':1,'r_addr':32,'done_v':1,'done_tag':8,'busy':1,'n_sectors':32,'n_beats':32}
inputs='clk,clk_bank,clk_out,rst_n,d_v,d_data,in_v,in_data,w_rdy,r_rdy,rd_v,rd_data'.split(',')
b='''`timescale 1ns/1fs
module tb #(parameter integer MUT=0);
reg clk=0; always #0.4165 clk=~clk;
wire [1:0] clk_bank={2{clk}};wire clk_out=clk;reg rst_n=0;
reg d_v=0,in_v=0,w_rdy=1,r_rdy=1,rd_v=0;
reg[255:0]d_data=0,rd_data=0;reg[511:0]in_data=0;
reg[255:0] dm[0:7];reg[511:0]pm[0:2047];
integer di=0,pi=0,done=0,cy=0,words=0;
realtime previous_edge=0;
always @(posedge clk)begin
 if(previous_edge>0 && (($realtime-previous_edge<0.832999999)||($realtime-previous_edge>0.833000001)))
  $fatal(1,"clock period must be exactly 833 ps");
 previous_edge=$realtime;
end
'''
for suffix in ['g','c']:
 for p,w in ports.items():b+=f'wire [{w-1}:0] {p}_{suffix};\n'
 mod='qkd_host_native_engine_gold' if suffix=='g' else 'qkd_host_native_engine'
 mut='0' if suffix=='g' else 'MUT'
 b+=f'{mod} #(.HDMAX(128),.KVHMAX(2),.QPIPE(2),.QMUT({mut})) u_{suffix}(\n'+',\n'.join([f'.{p}({p})' for p in inputs]+[f'.{p}({p}_{suffix})' for p in ports])+');\n'
b+='''initial begin
$readmemh("desc.mem",dm);$readmemh("pay.mem",pm);
repeat(5) @(negedge clk);rst_n=1;
end
always @(negedge clk) if(rst_n) begin
 d_v=di<8;d_data=dm[di<8?di:7];
 in_v=pi<2048;in_data=pm[pi<2048?pi:2047];
 w_rdy=(cy%11!=3)&&(cy%11!=4);end
always @(posedge clk) if(rst_n)begin
 if(d_v&&d_rdy_g)di=di+1;
 if(in_v&&in_rdy_g)pi=pi+1;
 if(done_v_g)done=done+1;
 if(w_v_g&&w_rdy)words=words+1;
 cy=cy+1;
 #0.01;
'''
for p in ports:
 cond=''
 if p in ('w_addr','w_data'):cond='w_v_g && '
 if p=='r_addr':cond='r_v_g && '
 if p=='done_tag':cond='done_v_g && '
 b+=f'if({cond}({p}_g !== {p}_c))$fatal(1,"LOCKSTEP {p} cycle=%0d",cy);\n'
b+='''if(done==8)begin $display("PASS INGEST_LOCKSTEP cycles=%0d beats=%0d sectors=%0d",cy,pi,words);$finish;end
if(cy>100000)$fatal(1,"completion missing di=%0d pi=%0d done=%0d",di,pi,done);
end
endmodule
'''
(out/'tb.sv').write_text(b)
# Parameterized production-shape lint top, with every engine input exposed.
inwidth={'clk':1,'clk_bank':2,'clk_out':1,'rst_n':1,'d_v':1,'d_data':256,'in_v':1,'in_data':512,
         'w_rdy':1,'r_rdy':1,'rd_v':1,'rd_data':256}
names=list(inwidth)+list(ports)
lint='module lint_top('+','.join(names)+');\n'
for p,w in inwidth.items():lint+=f'input [{w-1}:0] {p};\n'
for p,w in ports.items():lint+=f'output [{w-1}:0] {p};\n'
lint+='qkd_host_native_engine #(.HDMAX(128),.KVHMAX(2),.QPIPE(2)) u_eng('+','.join(f'.{p}({p})' for p in names)+');\nendmodule\n'
(out/'lint_top.sv').write_text(lint)
f='physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v'
(out/Path(f).name).write_bytes(subprocess.check_output(['git','-C',str(wt),'show','HEAD:'+f]))
