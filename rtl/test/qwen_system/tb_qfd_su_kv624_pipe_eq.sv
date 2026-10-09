`timescale 1ns/1ps
// PIPE=1 vs PIPE=0 streaming equivalence (sys-takeover 2026-10-09): random masks, near-grid addresses (both
// strides, VBASE / 2*VBASE crossings, wrapped bases, off-by-one lanes) and near-E4M3 data, a new vector EVERY
// cycle; PIPE=1 outputs must equal PIPE=0 outputs one cycle later, including the sticky fault.  MUT=1 corrupts the
// PIPE=1 instance and must be detected.
module tb_qfd_su_kv624_pipe_eq;
 parameter integer MUT=0, N=20000;
 reg clk=0;always #5 clk=~clk;reg rst_n=0;
 reg [63:0] mask;reg [1535:0]addr;reg [2047:0]data;
 wire [63:0] om0,om1;wire [23:0]a00,a10,a01,a11;wire[511:0]od0,od1;wire f0,f1;
 ot_qfd_su_kv624 #(.PIPE(0)) d0(.clk(clk),.rst_n(rst_n),.i_mask(mask),.i_addr(addr),.i_data(data),.o_mask(om0),.o_a0(a00),.o_a1(a10),.o_data(od0),.fault(f0));
 ot_qfd_su_kv624 #(.PIPE(1),.MUT_ADDR(MUT)) d1(.clk(clk),.rst_n(rst_n),.i_mask(mask),.i_addr(addr),.i_data(data),.o_mask(om1),.o_a0(a01),.o_a1(a11),.o_data(od1),.fault(f1));
 reg [63:0] om0_d;reg[23:0]a00_d,a10_d;reg[511:0]od0_d;reg f0_d;
 always @(posedge clk) begin om0_d<=om0;a00_d<=a00;a10_d<=a10;od0_d<=od0;f0_d<=f0; end
 integer v,i,stride,base,mism=0,faults=0,cmp=0; reg [31:0] r;
 initial begin
  mask=0;addr=0;data=0;repeat(4)@(negedge clk);rst_n=1;
  for(v=0;v<N;v=v+1)begin
   if(f0||f1)begin faults=faults+1; rst_n=0;@(negedge clk);rst_n=1;repeat(2)@(negedge clk);end   // clear the sticky fault, then refill
   r=$random; stride=r[0]?1:16;
   case(r[3:1]) 0: base=2097152-r[11:4]; 1: base=4194304-r[11:4]*2; 2: base=r[9:4]; default: base=$unsigned($random)%4194304; endcase
   mask={$random,$random}; if(r[15:13]==0) mask=0; if(r[15:13]==1) mask=64'h1<<r[21:16];
   for(i=0;i<64;i=i+1)begin
    addr[24*i+:24]=24'(base+(i/32)*(r[22]?65536:0)+(i%32)*stride);
    if(r[23]&&($random%193==0)) addr[24*i+:24]=addr[24*i+:24]+24'(r[26:24]);
    r=$random; data[32*i+:32]={r[31],8'(121+r[7:4]%15),r[10:8],20'd0}; if(r[15:11]==0) data[32*i+:32]=0; if($random%211==0) data[32*i+:32]=$random;
   end
   @(negedge clk);
   if(v>8&&rst_n)begin cmp=cmp+1;
    if(om1!==om0_d||a01!==a00_d||a11!==a10_d||od1!==od0_d||f1!==f0_d) mism=mism+1; end
  end
  if(MUT!=0)begin if(mism>0)begin $display("NEG_DETECTED KV624PIPE mismatches %0d",mism);$finish;end $fatal(1,"mutant survived"); end
  if(mism!=0)$fatal(1,"PIPE mismatch %0d of %0d",mism,cmp);
  $display("PASS KV624PIPE equivalence cycles%0d fault_resets%0d",cmp,faults);$finish;
 end
endmodule
