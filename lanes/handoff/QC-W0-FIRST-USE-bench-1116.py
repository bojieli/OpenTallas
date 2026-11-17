from pathlib import Path
import re,json,hashlib
r=Path('/srv/opentallas-scratch2/claude/qc-types-r/w0_lec_diag_1116/first_use');r.mkdir(exist_ok=True)
src=Path('/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44/group44/src_804_complete')
f=src/'rtl/physical/qfd_dv_lane_h_su_mem9.sv';text=f.read_text();body=text[text.index('module qfd_dv_lane_h_su_mem9 '):].split(');',1)[0]
ports=[]
for line in body.splitlines():
 match=re.match(r'\s*(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(.*)',line)
 if match:
  direction,width,names=match.groups()
  for name in names.rstrip().rstrip(',').split(','):
   name=name.strip()
   if name:ports.append((direction,width or '',name))
assert len(ports)>55,len(ports)
# Keep exact actual head/EXP wiring. Other leaf responses held quiet, actual vector-memory operands zero.
a=['`timescale 1ns/1ps','module tb;','reg clk=0; always #5 clk=~clk;']
for d,w,n in ports:
 a.append(('reg ' if d=='input' else 'wire ')+w+' '+n+('=0;' if d=='input' and n!='clk' else ';') if n!='clk' else '')
a+=['wire [31:0] exp_y; wire exp_vo,exp_fault;', 'ot_hdc_sfu_exp_t dut_exp(.clk(clk),.rst_n(rst_n),.v(sx_exp_v),.x(sx_exp_x),.y(exp_y),.vo(exp_vo),.fault(exp_fault));']
con=[]
for d,w,n in ports:
 val={'sy_exp_y':'exp_y','sy_exp_vo':'exp_vo','sy_exp_f':'exp_fault'}.get(n,n);con.append('.'+n+'('+val+')')
a+=['qfd_dv_lane_h_su_mem9 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(44),.KV_WR_PIPE(1),.SEGMENTED_MEMORY_DELAY(1)) dut_head('+','.join(con)+');', '''integer cycle=0,epoch=0,reset_edges=0,accepted=0,sent=0,consumed=0,outputs=0,retired=0;
integer first_accept=-1,first_exp=-1,first_consumer=-1,first_output=-1;
reg observing=0;
always @(posedge clk) begin
 cycle=cycle+1;
 if (!rst_n) reset_edges=reset_edges+1;
 if(observing) begin
  if (dut_head.u_h.u_lane.e_v) begin accepted=accepted+1; if(first_accept<0)first_accept=cycle; end
  if (sx_exp_v) begin sent=sent+1;if(first_exp<0)first_exp=cycle; end
  if (dut_exp.u_exp.vd[dut_exp.u_exp.T_R1]) begin
    consumed=consumed+1;if(first_consumer<0)first_consumer=cycle;
    if(dut_exp.u_exp.lo_d[30] !== 1'b0) $fatal(1,"UNSAFE consumer bit30 cycle=%0d",cycle);
  end
  if(exp_vo)begin outputs=outputs+1;if(first_output<0)first_output=cycle;
    if(exp_y !== 32'h3f800000 || exp_fault !== 0) $fatal(1,"WRONG valid exp y=%h fault=%b",exp_y,exp_fault);
  end
  if(retire)retired=retired+1;
 end
end
task run_epoch(input integer which);
 integer k;
 begin
  epoch=which;observing=0;rst_n=0;emit0=0;live=0;accept=0;reset_edges=0;
  // Deliberately poison the exact failing state before cold/warm held reset.
  dut_exp.u_exp.a_lo[30]=1'b1;dut_exp.u_exp.d_lo.g_line.line[126]=1'b1;
  repeat(64)@(negedge clk);
  if(dut_exp.u_exp.lo_d[30] !== 0)$fatal(1,"heldreset didnotflush");
  $display("RESET epoch=%0d heldedges=%0d a_lo30=%b d_lo126=%b rt=%b",which,reset_edges,dut_exp.u_exp.a_lo[30],dut_exp.u_exp.d_lo.g_line.line[126],dut_exp.rt);
  accepted=0;sent=0;consumed=0;outputs=0;retired=0;first_accept=-1;first_exp=-1;first_consumer=-1;first_output=-1;
  rst_n=1;observing=1;live=1;accept=1;emit0=1;
  // Earliest externally supplied stream begins immediately on reset release.
  repeat(12)@(negedge clk);emit0=0;accept=0;
  repeat(250)@(negedge clk);
  if(accepted==0 || sent==0 || consumed!=sent || outputs!=sent)$fatal(1,"NO/TRUNCATED stream a=%0d s=%0d c=%0d o=%0d",accepted,sent,consumed,outputs);
  $display("FIRST_USE epoch=%0d first_head_emit=%0d first_exp_send=%0d first_exp_consumer=%0d first_valid_output=%0d accepted=%0d sent=%0d consumer=%0d outputs=%0d retired=%0d",which,first_accept,first_exp,first_consumer,first_output,accepted,sent,consumed,outputs,retired);
 end
endtask
initial begin
 cls=1;i_sfu=1;ma=0;mb=0;ad=0;va_q=0;vb_q=0;vc_q=0;fin_th=1;i_last_r=1;
 run_epoch(0);run_epoch(1);$display("FIRST_USE_PASS cold+warm actualheadMEM44+actualEXP noaddedboot");$finish;
end
endmodule''']
(r/'tb.sv').write_text('\n'.join(a)+'\n')
files=['rtl/physical/qfd_dv_lane_h_su_mem9.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_vstream_sfu_t.sv','rtl/hdc/ot_hdc_sfu_q.sv','rtl/hdc/ot_hdc_sfu.sv']
(r/'files.txt').write_text('\n'.join(str(src/x) for x in files)+'\n')
(r/'source_receipt.json').write_text(json.dumps({x:hashlib.sha256((src/x).read_bytes()).hexdigest() for x in files},indent=2)+'\n')
(r/'run.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd '+str(r)+'\niverilog -g2012 -s tb -o sim -c files.txt tb.sv >build.log 2>&1\nvvp -n sim >run.log 2>&1\ncat run.log\n')
with (r/'files.txt').open('a') as o:
 for n in ['ot_sram_1r1w_32x64_m1','ot_sram_1r1w2c_128x64_m1']:o.write(str(src/'physical/asap7_memory_macros_v2'/n/(n+'.v'))+'\n')
print('ports',len(ports))
