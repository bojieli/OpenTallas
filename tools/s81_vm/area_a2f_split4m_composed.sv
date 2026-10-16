`timescale 1ns/1ps
`default_nettype none
module s81_a2f_slice_split4m(
 input wire ck_control,input wire [6:0] ck_meta,input wire ck_fault,input wire [31:0] ck_data,
 input wire rst_control_n,input wire [6:0] rst_meta_n,input wire rst_fault_n,input wire [31:0] rst_data_n,
 input wire [52:0] src_v,input wire [423:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 input wire [741:0] i_row,input wire [211:0] i_mask,input wire [423:0] i_tag,input wire [6783:0] i_data,
 output wire [31:0] o_v,output wire [447:0] o_row,output wire [127:0] o_mask,
 output wire [255:0] o_tag,output wire [4095:0] o_data,output wire [3:0] fault
);
 wire [671:0] ids;wire [31:0] dv;wire [63:0] ds;wire [3:0] fc,fm;wire [31:0] fd;
 wire [1377:0] mi;wire [831:0] mo;
 s81_a2f_control4_resetlocal u_control(ck_control,rst_control_n,src_v,src_bank,header_epoch,payload_epoch,ids,dv,ds,fc);
 genvar s,k,q,b;
 generate for(s=0;s<53;s=s+1)begin:meta_in
  assign mi[26*s+:26]={i_tag[8*s+:8],i_mask[4*s+:4],i_row[14*s+:14]};
 end
 for(k=0;k<8;k=k+1)begin:field
  wire [847:0] di;wire [511:0] dout;wire [31:0] unused_v;
  for(s=0;s<53;s=s+1)begin:src assign di[16*s+:16]=i_data[128*s+16*k+:16];end
  s81_a2f_field16_split4 u_data(ck_data[4*k+:4],rst_data_n[4*k+:4],di,ids,dv,ds,unused_v,dout,fd[4*k+:4]);
  for(q=0;q<4;q=q+1)begin:quarter
   for(b=0;b<8;b=b+1)begin:bank
    assign o_data[(q*8+b)*128+16*k+:16]=dout[(q*8+b)*16+:16];
   end
  end
 end
 for(q=0;q<4;q=q+1)begin:meta_out
  for(b=0;b<8;b=b+1)begin:bank
   assign {o_tag[(q*8+b)*8+:8],o_mask[(q*8+b)*4+:4],o_row[(q*8+b)*14+:14]}=mo[(q*8+b)*26+:26];
  end
 end endgenerate
 s81_a2f_meta26_split4 u_meta(ck_meta,rst_meta_n,mi,ids,dv,ds,o_v,mo,fm);
 // join input order per quarter = A2 {fd[7:0], fm, fc}
 wire [39:0] fj;
 generate for(q=0;q<4;q=q+1)begin:fjq
  assign fj[10*q+:10]={fd[28+q],fd[24+q],fd[20+q],fd[16+q],fd[12+q],fd[8+q],fd[4+q],fd[q],fm[q],fc[q]};
 end endgenerate
 s81_a2f_fault_join4 u_fault(ck_fault,rst_fault_n,fj,fault);
endmodule

// Wires-only parent: five W0 roots and four slice fronts, 41 roots each (32 data + 7 metadata + control + fault).
// Candidate only: actual threshold control and seven standard field4 metadata leaves; no production adoption.
module s81_a2f_controlled_split4m(
 input wire ck_header,input wire [3:0] ck_payload,
 input wire [3:0] ck_control,ck_fault,input wire [27:0] ck_meta,input wire [127:0] ck_data,
 input wire rst_header_n,input wire [3:0] rst_payload_n,
 input wire [3:0] rst_control_n,rst_fault_n,input wire [27:0] rst_meta_n,input wire [127:0] rst_data_n,
 input wire [52:0] i_v,input wire [741:0] i_row,input wire [423:0] i_tag,
 input wire [847:0] i_mask,input wire [27135:0] i_data,
 output wire [127:0] o_slice_v,output wire [1791:0] o_slice_row,
 output wire [1023:0] o_slice_tag,output wire [511:0] o_mask,
 output wire [16383:0] o_data,output wire [15:0] o_fault
);
 wire [52:0] header_v;
 wire [741:0] header_row;wire [423:0] header_tag;
 wire [2:0] header_epoch;wire [11:0] payload_epoch;
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
  s81_a2_w0_payload u_payload(ck_payload[x],rst_payload_n[x],mi,di,mout,dout,payload_epoch[3*x+:3]);
  wire [31:0] vo;wire [447:0] ro;wire [127:0] mo;wire [255:0] to;wire [4095:0] dataout;
  s81_a2f_slice_split4m u_front(ck_control[x],ck_meta[7*x+:7],ck_fault[x],ck_data[32*x+:32],
   rst_control_n[x],rst_meta_n[7*x+:7],rst_fault_n[x],rst_data_n[32*x+:32],
   i_v,src_bank,header_epoch,payload_epoch,header_row,mout,header_tag,dout,
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
// Reuse the standard field4 hard master for all26 metadata bits; two padded bits never escape.
module s81_a2f_meta26_split4(
 input wire [6:0] ck,rst_n,input wire [1377:0] i_data,input wire [671:0] i_sel,
 input wire [31:0] i_drain_v,input wire [63:0] i_drain_slot,
 output wire [31:0] o_v,output wire [831:0] o_data,output wire [3:0] fault
);
 wire [223:0] vv;wire [27:0] ff;
 genvar k,s,b,j;
 generate for(k=0;k<7;k=k+1)begin:bitslice
  wire [211:0] di;wire [127:0] dout;
  for(s=0;s<53;s=s+1)begin:source
   for(j=0;j<4;j=j+1)begin:bitpos
    if(4*k+j<26)assign di[4*s+j]=i_data[26*s+4*k+j];
    else assign di[4*s+j]=1'b0;
   end
  end
  s81_a2f_field4 u_leaf(ck[k],rst_n[k],di,i_sel,i_drain_v,i_drain_slot,vv[32*k+:32],dout,ff[4*k+:4]);
  for(b=0;b<32;b=b+1)begin:bank
   for(j=0;j<4;j=j+1)begin:bitpos
    if(4*k+j<26)assign o_data[26*b+4*k+j]=dout[4*b+j];
   end
  end
 end endgenerate
 // These depend only on shared selectors/drain state and therefore agree across allseven leaves.
 assign o_v=vv[31:0];assign fault=ff[3:0];
endmodule
`default_nettype wire
