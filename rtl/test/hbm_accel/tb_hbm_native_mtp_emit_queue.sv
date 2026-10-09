`timescale 1ns/1ps
module tb_hbm_native_mtp_emit_queue;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,jv=0,hr=0,dr=0,nd=0,xf=0;reg [37:0] emit=0;
 wire jr,er,hv,dv,fault;wire [80:0] hd;wire [20:0] count;wire [2:0] status;
 integer sent=0,received=0,cycle=0;
 ot_hbm_native_mtp_emit_queue #(.ENABLE(1)) dut(.clk(clk),.rst_n(rst_n),.external_fault(xf),.job_v(jv),.job_rdy(jr),.job_id(32'h87654321),.job_generation(4'ha),.job_epoch(8'hf1),.emit(emit),.native_done(nd),.native_status(3'd2),.emit_ready(er),.host_v(hv),.host_ready(hr),.host_data(hd),.host_done_v(dv),.host_done_ready(dr),.host_status(status),.accepted_count(count),.fault(fault));
 always @(posedge clk) if(rst_n && hv && hr)begin
 if(hd!=={8'hf1,4'ha,32'h87654321,20'(received),17'(131071-received)})$fatal(1,"token lost/reordered/identity");received=received+1;end
 initial begin
 @(negedge clk);rst_n=1;jv=1;@(negedge clk);jv=0;
 while(sent<40)begin
 emit={20'(sent),17'(131071-sent),1'b1};hr=cycle>100 && cycle%3==0;
 @(posedge clk);if(er)sent=sent+1;#1;
 if(dv||fault)$fatal(1,"early completion/fault");if(cycle>1000)$fatal(1,"deadlock");
 @(negedge clk);cycle=cycle+1;
 end
 emit=0;nd=1;@(negedge clk);nd=0;
 if(dv)$fatal(1,"done before drain");hr=1;
 while(!dv)begin @(negedge clk);end
 if(received!=40||count!=40||status!=2)$fatal(1,"final commit count");
 dr=1;@(negedge clk);dr=0;jv=1;@(negedge clk);jv=0;
 // Wrong index must fault without inventing a committed token.
 emit={20'd1,17'd4,1'b1};nd=1;@(negedge clk);emit=0;nd=0;
 if(!fault||!dv||count!=0||status!=4)$fatal(1,"bad index not rejected");
 $display("PASS finite8 fullpressure40 ordered commits plus bad index");$finish;
 end
endmodule
