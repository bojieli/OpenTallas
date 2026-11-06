module tb;
reg clk=0, rst_n=0;
reg [143:0] bank_status;
reg [2:0] hub_status;
reg ring_fault,ring_fault_late;
wire [18:0] ref0,ref2,dut0,dut2,mdata,mlate,mwarm;
reg [18:0] delay0=0,delay2=0;
status_reference #(.DMUT(0)) r0(.*,.vmstat(ref0));
status_reference #(.DMUT(2)) r2(.*,.vmstat(ref2));
ot_vms_status_static_pc #(.DMUT(0)) d0(.*,.vmstat(dut0));
ot_vms_status_static_pc #(.DMUT(2)) d2(.*,.vmstat(dut2));
status_mut_data md(.*,.vmstat(mdata));
status_mut_late ml(.*,.vmstat(mlate));
status_mut_warm mw(.*,.vmstat(mwarm));
always @(posedge clk or negedge rst_n)
 if (!rst_n) begin delay0<=0;delay2<=0;end
 else begin delay0<=ref0;delay2<=ref2;end
integer checks=0,errors=0,mdiffs=0,ldiffs=0,wdiffs=0;
task step;
 begin clk=0;#2;clk=1;#2;
  if(dut0!==delay0 || dut2!==delay2) begin
   errors++; if(errors<5)$display("DIFF rst=%b d0=%h r0=%h d2=%h r2=%h",rst_n,dut0,delay0,dut2,delay2);
  end
  checks+=2;
  if(mdata!==delay0)mdiffs++;
  if(mlate!==delay0)ldiffs++;
  if(mwarm!==delay0)wdiffs++;
 end
endtask
integer episode,k,b;
initial begin
 bank_status=0;hub_status=0;ring_fault=0;ring_fault_late=0;
 for(episode=0;episode<200;episode++)begin
  clk=0;rst_n=0;#2;step();
  rst_n=1;
  for(k=0;k<64;k++)begin
   for(b=0;b<8;b++)begin
    bank_status[b*18+:16]=(k%7==0)?16'hffff:16'($urandom_range(0,2047));
    bank_status[b*18+16+:2]=(k%16<8)?2'b0:2'($urandom());
   end
   hub_status=(k%16<8)?3'b0:3'($urandom());
   ring_fault=(k%16<8)?1'b0:1'($urandom());ring_fault_late=k[0];
   step();
  end
 end
 $display("STATUS_STAGE_EQ checks=%0d errors=%0d data_mutant=%0d late_mutant=%0d warmup_mutant=%0d pin_cycles=1",checks,errors,mdiffs,ldiffs,wdiffs);
 if(errors || !mdiffs || !ldiffs || !wdiffs)$fatal(1,"status pipeline miter or mutant failed");
 $finish;
end
endmodule
