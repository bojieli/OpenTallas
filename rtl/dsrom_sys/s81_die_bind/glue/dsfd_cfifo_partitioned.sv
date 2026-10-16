`timescale 1ns/1ps
// Structural successor of the static x2-pair ingress. No added schedule stages.
// Each child has a separate physical clock entry; equal-phase clocks are a die contract.
// This source is NOT a physical view or an adopted die binding.
module dsfd_cfifo_ingress_slice #(parameter integer W=113)(
 input wire f_ck,ck,rst_n,input wire [W:0] i,output wire [W-1:0] o,output wire fault
);
 ot_s81_static_column_ingress #(.W(W)) u(.f_ck(f_ck),.i(i),.ck(ck),.rst_n(rst_n),.o(o),.fault(fault));
endmodule

module dsfd_cfifo_data_slice #(parameter integer W=128)(
 input wire ck,input wire [W-1:0] d,output reg [W-1:0] q
);
 always @(posedge ck) q<=d;
endmodule

module dsfd_cfifo_format_slice #(parameter integer W=128,parameter [W-1:0] QUALIFY=0)(
 input wire ck,v,input wire [W-1:0] d,output reg [W-1:0] q
);
 // Valid is always lane0 oa[0], including lane-valid mismatch/fault cases.
`ifdef OT_CFIFO_SPLIT_MUT_GATE
 always @(posedge ck) q <= d;
`else
 always @(posedge ck) q <= d & ~(QUALIFY & {W{!v}});
`endif
endmodule

module dsfd_cfifo_return_control(
 input wire ck,rst,input wire [65:0] ri,input wire [1:0] st,
 input wire [9:0] lane_fault,input wire av,bv,output wire rs,output wire [69:0] rd
);
 reg [1:0] rsync_q;
 always @(posedge ck or negedge rst)
  if(!rst) rsync_q<=0; else rsync_q<={rsync_q[0],1'b1};
 assign rs=rsync_q[1];
 reg [1:0] sti;always @(posedge ck) sti<=st;
 reg [67:0] rr;reg flt;
 always @(posedge ck or negedge rs)
  if(!rs) begin rr<=0;flt<=0;end
  else begin rr<={sti[1]|flt,sti[0],ri};flt<=flt|(|lane_fault)|(av^bv);end
 assign rd={rr,rr[0],rs};
endmodule

module dsfd_cfifo_partitioned(
 input wire [4:0] xf_lane0,xf_lane1,
 input wire [9:0] cr_ingress,input wire [8:0] cr_format,input wire cr_return,
 input wire rst,input wire [565:0] xd,input wire [537:0] xd2,
 input wire [65:0] ri,input wire [1:0] st,
 output wire [282:0] xa,output wire [265:0] xb,output wire [14:0] cc,
 output wire [535:0] x2,output wire [69:0] rd,output wire rs
);
 wire [564:0] a;wire [536:0] b;wire [9:0] fault;
 genvar k;
 generate for(k=0;k<5;k=k+1)begin:g_a
  dsfd_cfifo_ingress113 u(.f_ck(xf_lane0[k]),.ck(cr_ingress[k]),.rst_n(rs),
   .i({xd[1+113*k+:113],xd[0]}),.o(a[113*k+:113]),.fault(fault[k]));
 end
 for(k=0;k<5;k=k+1)begin:g_b
  localparam integer W=(k<2)?108:107;
  localparam integer LO=(k<2)?108*k:216+107*(k-2);
  if (k<2) begin:g108
   dsfd_cfifo_ingress108 u(.f_ck(xf_lane1[k]),.ck(cr_ingress[k+5]),.rst_n(rs),
    .i({xd2[1+LO+:W],xd2[0]}),.o(b[LO+:W]),.fault(fault[k+5]));
  end else begin:g107
   dsfd_cfifo_ingress107 u(.f_ck(xf_lane1[k]),.ck(cr_ingress[k+5]),.rst_n(rs),
    .i({xd2[1+LO+:W],xd2[0]}),.o(b[LO+:W]),.fault(fault[k+5]));
  end
 end endgenerate
 wire [1100:0] xw={b[536:1],a};
 wire [1099:0] raw={xw[1100:565],xw[564:550],xw[549:284],xw[283:1]};
 wire [1099:0] q;
 localparam [1099:0] QMASK=(1100'b1<<282)|(1100'b1<<549)|(1100'b1<<550)|(1100'b1<<564)|(1100'b1<<568);
 generate for(k=0;k<9;k=k+1)begin:g_f
  localparam integer W=(k<8)?128:76;
  if(k==2)begin:g_qa
   dsfd_cfifo_fmt128_qa u(.ck(cr_format[k]),.v(a[0]),.d(raw[128*k+:W]),.q(q[128*k+:W]));
  end else if(k==4)begin:g_qb
   dsfd_cfifo_fmt128_qb u(.ck(cr_format[k]),.v(a[0]),.d(raw[128*k+:W]),.q(q[128*k+:W]));
  end else if(k==8)begin:g76
   dsfd_cfifo_data76 u(.ck(cr_format[k]),.d(raw[128*k+:W]),.q(q[128*k+:W]));
  end else begin:g128
   dsfd_cfifo_data128 u(.ck(cr_format[k]),.d(raw[128*k+:W]),.q(q[128*k+:W]));
  end
 end endgenerate
 assign {x2,cc,xb,xa}=q;
 dsfd_cfifo_return_control u_ret(.ck(cr_return),.rst(rst),.ri(ri),.st(st),
  .lane_fault(fault),.av(a[0]),.bv(b[0]),.rs(rs),.rd(rd));
endmodule

module dsfd_cfifo_ingress113(input wire f_ck,ck,rst_n,input wire [113:0] i,output wire [112:0] o,output wire fault);
 dsfd_cfifo_ingress_slice #(.W(113)) u(.f_ck(f_ck),.ck(ck),.rst_n(rst_n),.i(i),.o(o),.fault(fault));
endmodule

module dsfd_cfifo_ingress108(input wire f_ck,ck,rst_n,input wire [108:0] i,output wire [107:0] o,output wire fault);
 dsfd_cfifo_ingress_slice #(.W(108)) u(.f_ck(f_ck),.ck(ck),.rst_n(rst_n),.i(i),.o(o),.fault(fault));
endmodule

module dsfd_cfifo_ingress107(input wire f_ck,ck,rst_n,input wire [107:0] i,output wire [106:0] o,output wire fault);
 dsfd_cfifo_ingress_slice #(.W(107)) u(.f_ck(f_ck),.ck(ck),.rst_n(rst_n),.i(i),.o(o),.fault(fault));
endmodule

module dsfd_cfifo_data128(input wire ck,input wire [127:0] d,output wire [127:0] q);
 dsfd_cfifo_data_slice #(.W(128))u(.ck(ck),.d(d),.q(q));
endmodule

module dsfd_cfifo_data76(input wire ck,input wire [75:0] d,output wire [75:0] q);
 dsfd_cfifo_data_slice #(.W(76))u(.ck(ck),.d(d),.q(q));
endmodule

module dsfd_cfifo_fmt128_qa(input wire ck,v,input wire [127:0]d,output wire[127:0]q);
 dsfd_cfifo_format_slice #(.W(128),.QUALIFY(128'h4000000))u(.ck(ck),.v(v),.d(d),.q(q));
endmodule

module dsfd_cfifo_fmt128_qb(input wire ck,v,input wire [127:0]d,output wire[127:0]q);
 dsfd_cfifo_format_slice #(.W(128),.QUALIFY(128'h110006000000000))u(.ck(ck),.v(v),.d(d),.q(q));
endmodule
