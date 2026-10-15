`timescale 1ns/1ps
// Fixed-event landing, not a request matcher. Every compiled put/get consumes
// its assigned cycle even on a fault. Actual missing/late/wrong responses latch
// fault; they never defer a slot or move the normal execution timeline.
// One real aligned-v2 128x256 1R1W SRAM per physical pseudo-channel. Metadata
// names the consumer ordinal, not the physical HBM order. V permutes its ordinal
// so its low/high-64-row alternation has the same bounded ring lifetime as K.
module qkd_static_kv_landing_pc #(
    parameter integer STACK=0, GROUP=0, QUARTER=0, MUT=0
)(
    input wire ck, rst_n,
    input wire arm,
    input wire [15:0] epoch,
    input wire [5:0] layer,
    input wire expected_put,
    input wire [9:0] expected_sector,
    input wire actual_valid,
    input wire [9:0] actual_sector,
    input wire [15:0] actual_epoch,
    input wire [5:0] actual_layer,
    input wire [255:0] actual_data,
    input wire get,
    input wire [13:0] get_t,
    input wire get_v,
    input wire [15:0] get_epoch,
    input wire [5:0] get_layer,
    output reg out_valid,
    output reg [255:0] out_data,
    output reg [13:0] out_t,
    output reg out_v,
    output reg [15:0] out_epoch,
    output reg [5:0] out_layer,
    output reg fault
);
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    (* keep *) reg arm_q, put_q, actual_q, get_q;
    (* keep *) reg [15:0] epoch_q, ae_q, ge_q;
    (* keep *) reg [5:0] layer_q, al_q, gl_q;
    (* keep *) reg [9:0] ps_q, as_q;
    (* keep *) reg [255:0] ad_q;
    (* keep *) reg [13:0] gt_q;
    (* keep *) reg gv_q;
    always @(posedge ck) begin
        epoch_q<=epoch;layer_q<=layer;ae_q<=actual_epoch;al_q<=actual_layer;
        ge_q<=get_epoch;gl_q<=get_layer;ps_q<=expected_sector;as_q<=actual_sector;
        ad_q<=actual_data;gt_q<=get_t;gv_q<=get_v;
    end
    always @(posedge ck or negedge rn)
      if(!rn)begin arm_q<=0;put_q<=0;actual_q<=0;get_q<=0;end
      else begin arm_q<=arm;put_q<=expected_put;actual_q<=actual_valid;get_q<=get;end
    function automatic [7:0] ordinal(input [9:0] sec);
        ordinal=sec[9]?{sec[6:3],sec[7],sec[2:0]}:sec[7:0];
    endfunction
    wire [9:0] get_sector={gv_q,1'b0,gt_q[6],gt_q[12:9],gt_q[5:3]};
    wire [7:0] put_ord=ordinal(ps_q),get_ord=ordinal(get_sector);
    wire [8:0] put_ticket={ps_q[9],put_ord},get_ticket={gv_q,get_ord};
    wire [6:0] wa=put_ord[6:0],ra=get_ord[6:0];
    reg [127:0] valid;
    reg [8:0] ticket[0:127];
    reg [15:0] active_epoch;
    reg [5:0] active_layer;
    reg armed;
    wire [255:0] mem_q;
    ot_sram_1r1w_128x256_m1_r2c2 u_rows(
      .clk(ck),.r_ce_in(get_q),.r_addr_in(ra),.rd_out(mem_q),
      .w_ce_in(put_q),.w_addr_in(wa),.wd_in(ad_q),.w_mask_in({256{1'b1}}),
      .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    reg read_q;
    reg [13:0] rt_q;
    reg rv_q;
    reg [15:0] re_q;
    reg [5:0] rl_q;
    always @(posedge ck) begin
      rt_q<=gt_q;rv_q<=gv_q;re_q<=ge_q;rl_q<=gl_q;
      out_t<=rt_q;out_v<=rv_q;out_epoch<=re_q;out_layer<=rl_q;
      out_data<=(MUT==2)?(mem_q^256'b1):mem_q;
      if(put_q)ticket[wa]<=(MUT==1)?(put_ticket^9'b1):put_ticket;
    end
    always @(posedge ck or negedge rn)
      if(!rn)begin valid<=0;fault<=0;active_epoch<=0;active_layer<=0;armed<=0;read_q<=0;out_valid<=0;end
      else begin
        read_q<=get_q;out_valid<=read_q;
        if(arm_q)begin
          if((|valid)||put_q||get_q)fault<=1;
          active_epoch<=epoch_q;active_layer<=layer_q;armed<=1;valid<=0;
        end
        if(put_q!=actual_q)fault<=1;
        if(put_q)begin
          if(!armed||ps_q[8]||as_q!=ps_q||ae_q!=active_epoch||al_q!=active_layer)fault<=1;
          if(valid[wa]&&!(get_q&&ra==wa))fault<=1;
          valid[wa]<=1;
        end
        if(get_q)begin
          if(!armed||!valid[ra]||ticket[ra]!=get_ticket||ge_q!=active_epoch||gl_q!=active_layer||
             gt_q[13]||gt_q[2:0]!=3'(GROUP)||gt_q[8:7]!=2'(STACK))fault<=1;
          if(!(put_q&&wa==ra))valid[ra]<=0;
        end
      end
endmodule

// One native row group = four separately clocked physical PC landing leaves.
// Every request and response is pin-registered at the group; no ready port.
module qkd_static_kv_landing_grp #(
    parameter integer STACK=0,GROUP=0,MUT=0
)(
    input wire ck,input wire [3:0] ck_pc,input wire rst_n,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [3:0] expected_put,input wire [39:0] expected_sector,
    input wire [3:0] actual_valid,input wire [39:0] actual_sector,
    input wire [63:0] actual_epoch,input wire [23:0] actual_layer,input wire [1023:0] actual_data,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    output reg rsp_valid,output reg [1023:0] rsp_data,output reg [13:0] rsp_t,
    output reg rsp_v,output reg [15:0] rsp_epoch,output reg [5:0] rsp_layer,output reg fault
);
    (* keep *) reg rn;
    always @(posedge ck)rn<=rst_n;
    (* keep *) reg rq;
    (* keep *) reg [13:0] tq;
    (* keep *) reg vq;
    (* keep *) reg [15:0] eq;
    (* keep *) reg [5:0] lq;
    always @(posedge ck)begin tq<=req_t;vq<=req_v;eq<=req_epoch;lq<=req_layer;end
    always @(posedge ck or negedge rn)if(!rn)rq<=0;else rq<=req_valid;
    wire [3:0] ov,pf;
    wire [1023:0] od;
    wire [55:0] ot;
    wire [3:0] vv;
    wire [63:0] oe;
    wire [23:0] ol;
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_pc
      qkd_static_kv_landing_pc #(.STACK(STACK),.GROUP(GROUP),.QUARTER(q),.MUT(MUT))u_pc(
       .ck(ck_pc[q]),.rst_n(rst_n),.arm(arm),.epoch(epoch),.layer(layer),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(rq),.get_t(tq),.get_v(vq),.get_epoch(eq),.get_layer(lq),
       .out_valid(ov[q]),.out_data(od[256*q+:256]),.out_t(ot[14*q+:14]),
       .out_v(vv[q]),.out_epoch(oe[16*q+:16]),.out_layer(ol[6*q+:6]),.fault(pf[q]));
    end endgenerate
    always @(posedge ck)begin rsp_data<=od;rsp_t<=ot[13:0];rsp_v<=vv[0];rsp_epoch<=oe[15:0];rsp_layer<=ol[5:0];end
    always @(posedge ck or negedge rn)
      if(!rn)begin rsp_valid<=0;fault<=0;end
      else begin
        rsp_valid<=ov[0];
        if((|pf)||ov!={4{ov[0]}})fault<=1;
        if(ov[0]&&((ot!={4{ot[13:0]}})||(vv!={4{vv[0]}})||(oe!={4{oe[15:0]}})||(ol!={4{ol[5:0]}})))fault<=1;
      end
endmodule
