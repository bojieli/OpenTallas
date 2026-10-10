`timescale 1ns/1ps
// Full-context prompt buffer:8192x18, eight tokens in32b slots, one1024x256 1R1W SRAM.
// SECDED(24,18) protects mutable tokens. Masked writes touch only the selected24b codeword.
// Read response holds when disabled, exactly one edge as the historical behavioral buffer.
// Uncorrectable words return zero and raise sticky fault before the package can launch a step.
module ot_qfd_prompt_sram #(parameter integer MUT=0)(
 input wire clk, rst_n, we, re,
 input wire [12:0] waddr, raddr,
 input wire [17:0] wdata,
 output wire [17:0] q,
 output reg fault
);
 function automatic [23:0] encode(input [17:0] d);
  integer i,j,k; reg [23:0] c;
  begin
   c=0;j=0;
   for(i=1;i<=23;i=i+1) if((i&(i-1))!=0) begin c[i-1]=d[j];j=j+1;end
   for(k=0;k<5;k=k+1) begin
    for(i=1;i<=23;i=i+1) if((i&(1<<k))!=0 && i!=(1<<k)) c[(1<<k)-1]=c[(1<<k)-1]^c[i-1];
   end
   c[23]=^c[22:0];encode=c;
  end
 endfunction
 // Return {UE, corrected-data}; a single error in the overall parity bit leaves data intact.
 function automatic [18:0] decode(input [23:0] x);
  integer i,j,k; reg [4:0] syn; reg odd,ue; reg [23:0] c; reg [17:0] d;
  begin
   syn=0;c=x;d=0;j=0;odd=^x;
   for(k=0;k<5;k=k+1) for(i=1;i<=23;i=i+1) if((i&(1<<k))!=0) syn[k]=syn[k]^x[i-1];
   ue=(syn!=0 && !odd) || (odd && syn>23);
   // Constant-bit compares avoid a variable-index barrel shifter on the SRAM read path.
   for(i=1;i<=23;i=i+1) if(odd && syn==i && MUT==0) c[i-1]=!x[i-1];
   for(i=1;i<=23;i=i+1) if((i&(i-1))!=0) begin d[j]=c[i-1];j=j+1;end
   decode={ue,ue?18'b0:d};
  end
 endfunction
 wire [23:0] enc=encode(wdata);
 wire [255:0] wd,mask,rd;
 genvar g;
 generate for(g=0;g<8;g=g+1) begin:g_slot
  assign wd[g*32+:32]={8'b0,enc};
  assign mask[g*32+:32]=(waddr[2:0]==g)?32'h00ffffff:32'b0;
 end endgenerate
 ot_sram_1r1w_1024x256_m2_r2c2 u_sram(
  .clk(clk),.r_ce_in(re),.r_addr_in(raddr[12:3]),.rd_out(rd),
  .w_ce_in(we),.w_addr_in(waddr[12:3]),.wd_in(wd),.w_mask_in(mask),
  .rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
 reg [2:0] lane;reg valid;
 always @(posedge clk or negedge rst_n) if(!rst_n) begin lane<=0;valid<=0;end
 else begin if(re) lane<=raddr[2:0];valid<=re;end
 wire [18:0] dec=decode(rd[lane*32+:24]);
 assign q=dec[17:0];
 always @(posedge clk or negedge rst_n) if(!rst_n) fault<=0;else if(valid && dec[18]) fault<=1;
endmodule
