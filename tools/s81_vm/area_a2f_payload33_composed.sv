`timescale 1ns/1ps
`default_nettype none
// Pure-wiring opt-in front; 16 independently clocked payload33 leaves.
// Existing slice/controller/field/fault masters are unchanged. Each controller
// observes its four local payload epochs; all 16 epochs feed the global OR.
module s81_a2f_controlled_split4m_payload33(
 input wire ck_header,input wire [15:0] ck_payload,
 input wire [3:0] ck_control,ck_fault,input wire [27:0] ck_meta,input wire [127:0] ck_data,
 input wire rst_header_n,input wire [15:0] rst_payload_n,
 input wire [3:0] rst_control_n,rst_fault_n,input wire [27:0] rst_meta_n,input wire [127:0] rst_data_n,
 input wire [52:0] i_v,input wire [741:0] i_row,input wire [423:0] i_tag,
 input wire [847:0] i_mask,input wire [27135:0] i_data,
 output wire [127:0] o_slice_v,output wire [1791:0] o_slice_row,
 output wire [1023:0] o_slice_tag,output wire [511:0] o_mask,
 output wire [16383:0] o_data,output wire [15:0] o_fault
);
 wire [52:0] header_v;
 wire [741:0] header_row;wire [423:0] header_tag;
 wire [2:0] header_epoch;wire [47:0] payload_epoch;wire [47:0] control_payload_epoch;
 s81_a2_payload33_epoch_groups u_epoch_groups(payload_epoch,control_payload_epoch);
 wire [423:0] src_bank;
 s81_a2_w0_header u_header(ck_header,rst_header_n,i_v,i_row,i_tag,header_v,header_row,header_tag,header_epoch);
 genvar s,x,q,b;
 generate for(s=0;s<53;s=s+1)begin:raw_bank
  assign src_bank[8*s+:8]=i_row[14*s+:8];
 end
 for(x=0;x<4;x=x+1)begin:payload
  wire [6783:0] di,dout;wire [211:0] mi,mout;
  for(s=0;s<53;s=s+1)begin:source
   assign di[128*s+:128]=i_data[512*s+128*x+:128];
   assign mi[4*s+:4]=i_mask[16*s+4*x+:4];
  end
  s81_a2_w0_payload_split4 u_payload(ck_payload[4*x+:4],rst_payload_n[4*x+:4],mi,di,mout,dout,payload_epoch[12*x+:12]);
  wire [31:0] vo;wire [447:0] ro;wire [127:0] mo;wire [255:0] to;wire [4095:0] dataout;
  s81_a2f_slice_split4m u_front(ck_control[x],ck_meta[7*x+:7],ck_fault[x],ck_data[32*x+:32],
   rst_control_n[x],rst_meta_n[7*x+:7],rst_fault_n[x],rst_data_n[32*x+:32],
   i_v,src_bank,header_epoch,control_payload_epoch[12*x+:12],header_row,mout,header_tag,dout,
   vo,ro,mo,to,dataout,o_fault[4*x+:4]);
  for(q=0;q<4;q=q+1)begin:quarter
   for(b=0;b<8;b=b+1)begin:bank
    assign o_slice_v[x*32+q*8+b]=vo[q*8+b];
    assign o_slice_row[(x*32+q*8+b)*14+:14]=ro[(q*8+b)*14+:14];
    assign o_slice_tag[(x*32+q*8+b)*8+:8]=to[(q*8+b)*8+:8];
    assign o_mask[(q*8+b)*16+x*4+:4]=mo[(q*8+b)*4+:4];
    assign o_data[(q*8+b)*512+x*128+:128]=dataout[(q*8+b)*128+:128];
   end
  end
 end endgenerate
endmodule
`default_nettype wire
