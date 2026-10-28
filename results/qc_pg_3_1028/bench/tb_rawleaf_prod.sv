`timescale 1ns/1ps
// QC-PG-3: production BUSY-state stimulus for one A0 lane-slice leaf (8 lanes = 2 positions x 4 groups).
// Production matvec: one ROM row a cycle -> v_d = 1 on every busy cycle; w = INT8 weights expanded exactly to BF16
// (FP32 word, low 16 bits 0, gaussian-like int8 values); x = one BF16-exact activation per group, new k every cycle;
// first_d for the first IL = 8 cycles of each 256-cycle output block (circulating accumulator restart); split constant 0.
// Versus the Codex correctness-stress bench (v 25 %, inf/nan specials) this is the steady busy state.
module tb_rawleaf_prod;
reg clk=0,rst_n=0,v_d=0,first_d=0;reg[3:0]split_d=0;reg[255:0]w_d=0;reg[127:0]x_d=0;
wire[63:0]t_out;wire[49:0]fault_q;
always #0.41665 clk=~clk;
ot_qwen_tile_lsl_rawfault_m3 dut(.*);
integer c,j,nz=0,seed=7;
function automatic [31:0] bf16_of_int8(input integer v);
  integer m,e,a; reg sg; reg [7:0] man;
  begin
    if (v==0) bf16_of_int8=32'd0;
    else begin
      sg=(v<0); a=sg?-v:v; e=0; m=a;
      while(m>1) begin m=m>>1; e=e+1; end
      man=(a<<(7-e)); bf16_of_int8={sg,8'(127+e),man[6:0],16'd0};
    end
  end
endfunction
function automatic integer gauss8(input integer d);
  integer k,acc;
  begin acc=0; for(k=0;k<4;k=k+1) begin acc=acc+($urandom%41)-20; end gauss8=acc; end
endfunction
function automatic [31:0] act_bf16(input integer d);
  reg [31:0] r;
  begin r=$urandom; act_bf16={r[31],8'd120+{5'd0,r[30:28]},r[22:16],16'd0}; end
endfunction
initial begin $dumpfile("rawleaf_prod.vcd");$dumpvars(0,tb_rawleaf_prod);end
initial begin
repeat(4)@(posedge clk);#0.01;rst_n=1;split_d=4'd0;
for(c=0;c<4096;c=c+1)begin
 @(negedge clk);v_d=1;first_d=((c%256)<8);
 for(j=0;j<8;j=j+1)w_d[j*32+:32]=bf16_of_int8(gauss8(0));
 for(j=0;j<4;j=j+1)x_d[j*32+:32]=act_bf16(0);
 @(posedge clk);#0.01;if(|t_out)nz=nz+1;
end
v_d=0;repeat(40)@(posedge clk);
if(nz<1000)$fatal(1,"RAWLEAF_PROD vacuous nz=%0d",nz);
$display("RAWLEAF_PROD_PASS cycles=%0d nonzero_out=%0d",c,nz);$finish;
end
endmodule
