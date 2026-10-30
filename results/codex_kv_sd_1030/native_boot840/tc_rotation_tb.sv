`timescale 1ps/1fs

module one #(parameter integer INIT=0,PHASE=0)(output reg done=0,output wire ready,fault,output wire[15:0]q);
reg clk=0,fclk=0,rst=0;always begin #416.5 clk=1;#416.5 clk=0;end
initial begin #(PHASE);forever begin #416.5 fclk=1;#416.5 fclk=0;end end
reg [15:0]d=16'hcafe;always @(posedge fclk)d<={d[14:0],d[15]^d[13]^d[12]^d[10]};
integer cycle=0,base=0,epoch=0;always @(posedge clk)cycle<=cycle+1;
ot_dp_clk_landing #(.W(16)) dut(fclk,clk,rst,d,q,ready,fault);
always @(posedge ready) if(ready===1'b1)$display("READY init=%0d phase=%0d epoch=%0d cycles=%0d timeps=%0.3f",INIT,PHASE,epoch,cycle-base,$realtime);
initial begin dut.u_ring.tc=INIT;
repeat(20)@(negedge clk);base=cycle;rst=1;
repeat(120)@(negedge clk);if(ready!==1||fault!==0)$fatal(1,"cold fail");
rst=0;repeat(25)@(negedge clk);base=cycle;epoch=1;rst=1;
repeat(120)@(negedge clk);if(ready!==1||fault!==0)$fatal(1,"warm fail");
done=1;
end
endmodule
module group #(parameter integer PHASE=0)(output wire done);
wire[7:0]r,f,fin;wire[15:0]q[0:7];reg clk=0;always begin #416.5 clk=1;#416.5 clk=0;end
genvar i;generate for(i=0;i<8;i=i+1)begin:g
 one #(.INIT(i),.PHASE(PHASE)) o(fin[i],r[i],f[i],q[i]);
end endgenerate
integer checks=0,j;
always @(posedge clk)begin
 #0.001;
 for(j=1;j<8;j=j+1)begin
  if(r[j]!==r[0]||f[j]!==f[0])$fatal(1,"status mismatch phase%0d tc%0d",PHASE,j);
  if(r[0]===1'b1 && f[0]===1'b0)begin
   if(q[j]!==q[0])$fatal(1,"data/status transport phase%0d tc%0d q%h/%h",PHASE,j,q[j],q[0]);
   checks=checks+1;
  end
 end
end
assign done=&fin;
always @(posedge done)$display("ROTATION_PASS phase=%0d pointwisechecks=%0d warm_writer_retained=1",PHASE,checks);
endmodule
module tb;
wire[15:0]done;genvar j;
generate for(j=0;j<16;j=j+1)begin:g
localparam integer PH=(j==15)?832:(j*55);
group #(.PHASE(PH)) x(done[j]);
end endgenerate
initial begin wait(&done);$display("ALL_ROTATIONS_PASS phasecases16 initial_tc8 cold_warm2");$finish;end
endmodule
