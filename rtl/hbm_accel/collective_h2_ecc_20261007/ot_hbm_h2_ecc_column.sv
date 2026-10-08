// Additive full512bit operand column: real three128x256 1R1W macros.
// Model hbm_collective_h2_ecc_model.py; no physical timing/wholecore claim.
module ot_hbm_h2_ecc_column #(parameter integer ENABLE=0,COLUMN=0)(
 input wire clk,rst_n,input wire [31:0] generation,
 input wire w_ce,input wire [5:0] w_addr,input wire [511:0] w_data,
 input wire r_ce,input wire [5:0] r_addr,
 output wire out_valid,output wire [511:0] out_data,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:g_off
  assign out_valid=0;assign out_data=0;assign fault=0;
 end else begin:g_on
  initial if(COLUMN<0||COLUMN>7)$fatal(1,"h2 ECC column identity");
  wire collision=w_ce&&r_ce&&w_addr==r_addr;
  wire [63:0] write_identity={22'd0,1'b1,generation,3'(COLUMN),w_addr};
  wire [63:0] read_identity={22'd0,r_ce,generation,3'(COLUMN),r_addr};
  wire [767:0] macro_data;
  wire [767:0] encoded_write;
  for(genvar k=0;k<8;k=k+1)begin:g_encode
   assign encoded_write[k*72+:72]=encode64(w_data[k*64+:64]);
  end
  assign encoded_write[576+:72]=encode64(write_identity);
  assign encoded_write[767:648]=0;
  reg [647:0] capture0,capture1;
  reg [71:0] request0,request1,request2;
  reg [1:0] healthy;
  wire [65:0] req0=decode64(request0),req1=decode64(request1),req2=decode64(request2);
  wire [65:0] stored_identity=decode64(capture1[576+:72]);
  wire [7:0] payload_UE;
  for(genvar k=0;k<8;k=k+1)begin:g_decode
   wire [65:0] decoded=decode64(capture1[k*72+:72]);
   assign out_data[k*64+:64]=decoded[63:0];assign payload_UE[k]=decoded[65];
  end
  wire request_bad=req0[65]||req1[65]||req2[65];
  wire row_bad=req2[41]&&(stored_identity[65]||(|payload_UE)||stored_identity[63:0]!=req2[63:0]);
  assign fault=healthy!=2'b01||request_bad||collision||row_bad;
  assign out_valid=ENABLE&&rst_n&&req2[41]&&!fault;
  for(genvar m=0;m<3;m=m+1)begin:g_mem
   ot_sram_1r1w_128x256_m1_r2c2 u_storage(.clk(clk),
    .r_ce_in(r_ce&&rst_n&&!fault),.r_addr_in({1'b0,r_addr}),.rd_out(macro_data[m*256+:256]),
    .w_ce_in(w_ce&&rst_n&&!fault),.w_addr_in({1'b0,w_addr}),.wd_in(encoded_write[m*256+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  end
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin request0<=0;request1<=0;request2<=0;healthy<=2'b01;capture0<=0;capture1<=0;end
   else begin
    if(fault)healthy<=2'b10;
    if(!fault)begin
     request0<=encode64(read_identity);request1<=request0;request2<=request1;
     capture0<=macro_data[647:0];capture1<=capture0;
    end
   end
  end
 end endgenerate
endmodule
