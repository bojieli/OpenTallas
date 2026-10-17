`timescale 1ns/1ps
// CORE-domain full KV-frame staging, after the real dual-clock return ring.
// One or two complete512-sector frames; no variable arrival chooses a read.
// Address is {frame,kind,ordinal8}; no K/V alias or per-row ticket RAM needed.
// Every data bit resides in actual aligned-v2 128x256 1R1W SRAM macros.
module qkd_static_kv_frame_pc #(parameter integer FRAME_SLOTS=1,MUT=0)(
 input wire ck,rst_n,input wire[1:0]cfg_stack,input wire[2:0]cfg_group,
 input wire arm,input wire[15:0]epoch,input wire[5:0]layer,
 input wire expected_put,input wire[9:0]expected_sector,
 input wire[15:0]expected_epoch,input wire[5:0]expected_layer,
 input wire actual_valid,input wire[9:0]actual_sector,input wire[15:0]actual_epoch,
 input wire[5:0]actual_layer,input wire[255:0]actual_data,
 input wire get,input wire[13:0]get_t,input wire get_v,
 input wire[15:0]get_epoch,input wire[5:0]get_layer,
 output reg out_valid,output reg[255:0]out_data,output reg[13:0]out_t,
 output reg out_v,output reg[15:0]out_epoch,output reg[5:0]out_layer,
 output reg fault,output reg[10:0]occupancy,output reg idle
);
 localparam integer DEPTH=512*FRAME_SLOTS,NBANKS=4*FRAME_SLOTS;
 initial if(FRAME_SLOTS!=1&&FRAME_SLOTS!=2)$error("one or two full KV frame slots required");
 (* keep *)reg rn;
 always @(posedge ck)rn<=rst_n;
 (* keep *)reg[1:0]stack_q;(* keep *)reg[2:0]group_q;
 (* keep *)reg aq,pq,vq,gq;
 (* keep *)reg[15:0]ae,pe,ve,ge;
 (* keep *)reg[5:0]al,pl,vl,gl;
 (* keep *)reg[9:0]ps,vs;
 (* keep *)reg[255:0]vd;
 (* keep *)reg[13:0]gt;(* keep *)reg gv;
 always @(posedge ck)begin
  stack_q<=cfg_stack;group_q<=cfg_group;ae<=epoch;al<=layer;
  pe<=expected_epoch;pl<=expected_layer;ve<=actual_epoch;vl<=actual_layer;
  ps<=expected_sector;vs<=actual_sector;vd<=actual_data;
  gt<=get_t;gv<=get_v;ge<=get_epoch;gl<=get_layer;
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin aq<=0;pq<=0;vq<=0;gq<=0;end
  else begin aq<=arm;pq<=expected_put;vq<=actual_valid;gq<=get;end
 function automatic[7:0]ordinal(input[9:0]sec);
  ordinal=sec[9]?{sec[6:3],sec[7],sec[2:0]}:sec[7:0];
 endfunction
 wire[9:0]get_sector={gv,1'b0,gt[6],gt[12:9],gt[5:3]};
 wire af=(FRAME_SLOTS==2)?al[0]:1'b0;
 wire wf=(FRAME_SLOTS==2)?pl[0]:1'b0;
 wire rf=(FRAME_SLOTS==2)?gl[0]:1'b0;
 wire[9:0]wa={wf,ps[9],ordinal(ps)};
 wire[9:0]ra={rf,gv,ordinal(get_sector)};
 reg[DEPTH-1:0]valid;
 reg[FRAME_SLOTS-1:0]armed;
 reg[15:0]owner_epoch[0:FRAME_SLOTS-1];reg[5:0]owner_layer[0:FRAME_SLOTS-1];
 wire[255:0]mem_q[0:NBANKS-1];reg[2:0]read_bank;
 genvar b;
 generate for(b=0;b<NBANKS;b=b+1)begin:g_bank
  ot_sram_1r1w_128x256_m1_r2c2 u_rows(
   .clk(ck),.r_ce_in(gq&&ra[9:7]==b),.r_addr_in(ra[6:0]),.rd_out(mem_q[b]),
   .w_ce_in(pq&&wa[9:7]==b),.w_addr_in(wa[6:0]^((MUT==1)?7'd1:7'd0)),
   .wd_in(vd),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 reg read_q;reg[13:0]rt;reg rv;reg[15:0]re;reg[5:0]rl;
 always @(posedge ck)begin
  if(gq)read_bank<=ra[9:7];
  rt<=gt;rv<=gv;re<=ge;rl<=gl;
  out_t<=rt;out_v<=rv;out_epoch<=re;out_layer<=rl;
  out_data<=mem_q[read_bank]^((MUT==2)?256'd1:256'd0);
 end
 always @(posedge ck or negedge rn)
  if(!rn)idle<=0;else idle<=!(|valid)&&!pq&&!vq&&!gq&&!read_q&&!out_valid;
 wire[511:0]arm_valid=valid>>(af*512);
 integer k;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   valid<=0;armed<=0;read_q<=0;out_valid<=0;fault<=0;occupancy<=0;
   for(k=0;k<FRAME_SLOTS;k=k+1)begin owner_epoch[k]<=0;owner_layer[k]<=0;end
  end else begin
   read_q<=gq;out_valid<=read_q;
   occupancy<=occupancy+{10'd0,pq}-{10'd0,gq};
   if(aq)begin
    if(|arm_valid)fault<=1;
    if(pq||gq)fault<=1;
    owner_epoch[af]<=ae;owner_layer[af]<=al;armed[af]<=1;
   end
   if(pq!=vq)fault<=1;
   if(pq)begin
    if(!armed[wf]||ps[8]||vs!=ps||ve!=pe||vl!=pl||pe!=owner_epoch[wf]||pl!=owner_layer[wf])fault<=1;
    if(valid[wa]&&!(gq&&wa==ra))fault<=1;
    valid[wa]<=1;
   end
   if(gq)begin
    if(!armed[rf]||!valid[ra]||ge!=owner_epoch[rf]||gl!=owner_layer[rf]||gt[13]||gt[2:0]!=group_q||gt[8:7]!=stack_q)fault<=1;
    if(!(pq&&wa==ra))valid[ra]<=0;
   end
  end
 end
endmodule

module qkd_static_kv_frame_physical_grp #(
    parameter integer STACK=0,GROUP=0,MUT=0,HOP_MUT=0,FRAME_SLOTS=1
)(
    input wire ck,input wire [3:0] ck_pc,input wire [3:0] ck_req_rly,ck_rsp_rly,input wire rst_n,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [3:0] expected_put,input wire [39:0] expected_sector,
    input wire [63:0] expected_epoch,input wire [23:0] expected_layer,
    input wire [3:0] actual_valid,input wire [39:0] actual_sector,
    input wire [63:0] actual_epoch,input wire [23:0] actual_layer,input wire [1023:0] actual_data,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    output wire rsp_valid,output wire [1023:0] rsp_data,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault,
    output wire [43:0] occupancy,output wire [3:0] idle
);
    localparam [1:0] STACK_BITS=STACK;localparam [2:0] GROUP_BITS=GROUP;
    wire [3:0] get,gv,ov,pf,vv;
    wire [55:0] gt,ot;
    wire [63:0] ge,oe;
    wire [23:0] gl,ol;
    wire [1023:0] od;

    wire [3:0] get_d,gv_d,ov_d,pf_d,vv_d;
    wire [55:0] gt_d,ot_d;
    wire [63:0] ge_d,oe_d;
    wire [23:0] gl_d,ol_d;
    wire [1023:0] od_d;
    genvar branch;
    generate for(branch=0;branch<4;branch=branch+1)begin:g_hop
      qkd_static_kv_hop38 #(.MUT(HOP_MUT==2 && branch==0))u_req(
        .ck(ck_req_rly[branch]),.rst_n(rst_n),
        .a({gl[6*branch+:6],ge[16*branch+:16],gv[branch],gt[14*branch+:14],get[branch]}),
        .b({gl_d[6*branch+:6],ge_d[16*branch+:16],gv_d[branch],gt_d[14*branch+:14],get_d[branch]}));
      qkd_static_kv_hop295 #(.MUT(HOP_MUT==1 && branch==0))u_rsp(
        .ck(ck_rsp_rly[branch]),.rst_n(rst_n),
        .a({pf[branch],ol[6*branch+:6],oe[16*branch+:16],vv[branch],ot[14*branch+:14],od[256*branch+:256],ov[branch]}),
        .b({pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],od_d[256*branch+:256],ov_d[branch]}));
    end endgenerate
    qkd_static_kv_rowctl u_rowctl(
      .ck(ck),.rst_n(rst_n),.req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .pc_get(get),.pc_get_t(gt),.pc_get_v(gv),.pc_get_epoch(ge),.pc_get_layer(gl),
      .pc_valid(ov_d),.pc_data(od_d),.pc_t(ot_d),.pc_v(vv_d),.pc_epoch(oe_d),.pc_layer(ol_d),.pc_fault(pf_d),
      .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault));
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_pc
      qkd_static_kv_frame_pc #(.MUT(MUT),.FRAME_SLOTS(FRAME_SLOTS))u_pc(
       .ck(ck_pc[q]),.rst_n(rst_n),.cfg_stack(STACK_BITS),.cfg_group(GROUP_BITS),.arm(arm),.epoch(epoch),.layer(layer),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .expected_epoch(expected_epoch[16*q+:16]),.expected_layer(expected_layer[6*q+:6]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(get_d[q]),.get_t(gt_d[14*q+:14]),.get_v(gv_d[q]),.get_epoch(ge_d[16*q+:16]),.get_layer(gl_d[6*q+:6]),
       .out_valid(ov[q]),.out_data(od[256*q+:256]),.out_t(ot[14*q+:14]),
       .out_v(vv[q]),.out_epoch(oe[16*q+:16]),.out_layer(ol[6*q+:6]),.fault(pf[q]),
       .occupancy(occupancy[11*q+:11]),.idle(idle[q]));
    end endgenerate
endmodule
