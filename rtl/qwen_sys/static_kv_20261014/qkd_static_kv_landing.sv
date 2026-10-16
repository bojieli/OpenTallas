`timescale 1ns/1ps
// Fixed-event landing, not a request matcher. Every compiled put/get consumes
// its assigned cycle even on a fault. Actual missing/late/wrong responses latch
// fault; they never defer a slot or move the normal execution timeline.
// One real aligned-v2 128x256 1R1W SRAM per physical pseudo-channel. Metadata
// names the consumer ordinal, not the physical HBM order. V permutes its ordinal
// so its low/high-64-row alternation has the same bounded ring lifetime as K.
// VMAP (Q-ATTN-RATE 2026-10-16, PV16 V layout = qkd_kv_static_writer VMAP=1): a V row t lives in group {t[5:4],t[0]}
// at PC sector {1,0,t[6],t[12:9],t[3:1]}; its ordinal {t[12:9],t[6],t[3:1]} is then the w16 pair's consumption order.
// K (get_v 0) is unchanged.  0 = the historical t[2:0] group / t[5:3] sector layout.
module qkd_static_kv_landing_pc #(
    parameter integer MUT=0, parameter integer VMAP=0,
    // FAULT_PIPE 1 (KVELEM 2026-10-16, landing_seg ls4): the fault conditions are registered once (fq) before the sticky
    // fault flop: the ticket[ra]/valid[ra] compare cone no longer ends in the fault OR (gate: -105 ps at 770 ps on
    // u_pc.fault/D).  Fault reports one edge later; no slot or data edge moves.  0 = historical single-edge fault.
    parameter integer FAULT_PIPE=0,
    // WRITE_PIPE 1 (KVELEM 2026-10-16, landing_seg ls5): the put side (SRAM write ce/addr/data and the ticket write) is
    // registered once more (put_d/wa_d/tk_d/ad_d) beside the SRAM and the ticket array: ls3 gate TT -43.3 ps on
    // ticket[*]/D (wa decode from the face pin register) and -36.3 ps on u_rows/w_addr_in.  The row is written one edge
    // later; valid[] and every fault check keep the put_q edge.  0 = historical.
    parameter integer WRITE_PIPE=0
)(
    input wire ck, rst_n,
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
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
    (* keep *) reg [1:0] stack_q;
    (* keep *) reg [2:0] group_q;
    always @(posedge ck)begin stack_q<=cfg_stack;group_q<=cfg_group;end
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
    // Row ordinal = the controller's STREAM position of the sector, for K and V alike: rows < T of a group arrive in
    // ascending t, i.e. ascending {t[12:9], t[6], t[5:3] (K) / t[3:1] (V VMAP 1)} = {sec[6:3], sec[7], sec[2:0]}, a
    // gap-free prefix at any T, so with <= 64 rows outstanding (ring bound) no two live rows share a row.
    // (Q-VMWB 10-16: K used sec[7:0] = {t6, t[12:9], t[5:3]}: the t6 = 0 / 1 rows of one t[12:9] are 8 stream
    // positions apart on the same row -> alias at mid T; kv_calendar T 2048 / 4096: slack -4 / -19 core edges.)
    // MUT 3: the old K ordinal (bench negative control).
    function automatic [7:0] ordinal(input [9:0] sec);
        ordinal=(sec[9]||MUT!=3)?{sec[6:3],sec[7],sec[2:0]}:sec[7:0];
    endfunction
    wire gvm=(VMAP!=0)&&gv_q;
    wire [9:0] get_sector={gv_q,1'b0,gt_q[6],gt_q[12:9],gvm?gt_q[3:1]:gt_q[5:3]};
    wire [2:0] get_group=gvm?{gt_q[5:4],gt_q[0]}:gt_q[2:0];
    wire [7:0] put_ord=ordinal(ps_q),get_ord=ordinal(get_sector);
    wire [8:0] put_ticket={ps_q[9],put_ord},get_ticket={gv_q,get_ord};
    wire [6:0] wa=put_ord[6:0],ra=get_ord[6:0];
    reg [127:0] valid;
    reg [8:0] ticket[0:127];
    reg [15:0] active_epoch;
    reg [5:0] active_layer;
    reg armed;
    wire [255:0] mem_q;
    (* keep *) reg put_d;
    (* keep *) reg [6:0] wa_d;
    (* keep *) reg [8:0] tk_d;
    (* keep *) reg [255:0] ad_d;
    always @(posedge ck) begin wa_d<=wa;tk_d<=(MUT==1)?(put_ticket^9'b1):put_ticket;ad_d<=ad_q; end
    always @(posedge ck or negedge rn) if(!rn)put_d<=0; else put_d<=(WRITE_PIPE!=0)&&put_q;
    wire w_ce=(WRITE_PIPE!=0)?put_d:put_q;
    wire [6:0] w_a=(WRITE_PIPE!=0)?wa_d:wa;
    wire [255:0] w_d=(WRITE_PIPE!=0)?ad_d:ad_q;
    wire [8:0] w_tk=(WRITE_PIPE!=0)?tk_d:((MUT==1)?(put_ticket^9'b1):put_ticket);
    ot_sram_1r1w_128x256_m1_r2c2 u_rows(
      .clk(ck),.r_ce_in(get_q),.r_addr_in(ra),.rd_out(mem_q),
      .w_ce_in(w_ce),.w_addr_in(w_a),.wd_in(w_d),.w_mask_in({256{1'b1}}),
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
      if(w_ce)ticket[w_a]<=w_tk;
    end
    // registered fault conditions (FAULT_PIPE 1): the same put/get checks as below, captured one edge before fault
    (* keep *) reg fq;
    wire fq_put=put_q&&((!armed||ps_q[8]||as_q!=ps_q||ae_q!=active_epoch||al_q!=active_layer)||(valid[wa]&&!(get_q&&ra==wa)));
    wire fq_get=get_q&&(!armed||!valid[ra]||ticket[ra]!=get_ticket||ge_q!=active_epoch||gl_q!=active_layer||
                        gt_q[13]||get_group!=group_q||gt_q[8:7]!=stack_q);
    always @(posedge ck or negedge rn) if(!rn)fq<=0; else fq<=(FAULT_PIPE!=0)&&(fq_put||fq_get);
    always @(posedge ck or negedge rn)
      if(!rn)begin valid<=0;fault<=0;active_epoch<=0;active_layer<=0;armed<=0;read_q<=0;out_valid<=0;end
      else begin
        read_q<=get_q;out_valid<=read_q;
        if(FAULT_PIPE!=0 && fq)fault<=1;
        if(arm_q)begin
          if((|valid)||put_q||get_q)fault<=1;
          active_epoch<=epoch_q;active_layer<=layer_q;armed<=1;valid<=0;
        end
        if(put_q!=actual_q)fault<=1;
        if(put_q)begin
          if(FAULT_PIPE==0 && (!armed||ps_q[8]||as_q!=ps_q||ae_q!=active_epoch||al_q!=active_layer))fault<=1;
          if(FAULT_PIPE==0 && valid[wa]&&!(get_q&&ra==wa))fault<=1;
          valid[wa]<=1;
        end
        if(get_q)begin
          if(!armed||!valid[ra]||ticket[ra]!=get_ticket||ge_q!=active_epoch||gl_q!=active_layer||
             gt_q[13]||get_group!=group_q||gt_q[8:7]!=stack_q)begin if(FAULT_PIPE==0)fault<=1;end
          if(!(put_q&&wa==ra))valid[ra]<=0;
        end
      end
endmodule

// Pin-registered row-control leaf. PC request/return faces are explicit so the
// physical parent can insert balanced, compiled relay stages on each quarter.
// VREQ=1 (Q-VMWB 2026-10-16, PV16): a second request face vreq_{valid,t} for the V gets issued by qkd_pv16_vport (the
// pair's own request, demuxed by t[0]); K gets keep req_*.  Both faces are pin-registered, then merged into the get
// register (+1 edge on BOTH K and V: VREQ=1 landing latency 6 / physical 8 edges).  The schedule is static: a K and a
// V get on the same edge is a fault, never arbitrated.  A V get carries the epoch / layer the group was ARMED with
// (arm / epoch / layer, latched here as in the PCs: a group with no K row at small T still serves V).  VREQ=0: unchanged.
module qkd_static_kv_rowctl #(parameter integer VREQ=0)(
    input wire ck,rst_n,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    output wire [3:0] pc_get,output wire [55:0] pc_get_t,output wire [3:0] pc_get_v,
    output wire [63:0] pc_get_epoch,output wire [23:0] pc_get_layer,
    input wire [3:0] pc_valid,input wire [1023:0] pc_data,input wire [55:0] pc_t,
    input wire [3:0] pc_v,input wire [63:0] pc_epoch,input wire [23:0] pc_layer,
    input wire [3:0] pc_fault,
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
    wire collide;
    generate if(VREQ!=0)begin:g_vreq
      (* keep *) reg vrq;
      (* keep *) reg [13:0] vtq;
      always @(posedge ck)vtq<=vreq_t;
      always @(posedge ck or negedge rn)if(!rn)vrq<=0;else vrq<=vreq_valid;
      (* keep *) reg aq;(* keep *) reg [15:0] aeq;(* keep *) reg [5:0] alq;
      reg [15:0] ke;reg [5:0] kl;                  // epoch / layer the group is armed with
      reg mq;reg [13:0] mt;reg mv;reg [15:0] me;reg [5:0] ml;
      always @(posedge ck)begin
        aeq<=epoch;alq<=layer;
        if(aq)begin ke<=aeq;kl<=alq;end
        mt<=vrq?vtq:tq;mv<=vrq|vq;me<=vrq?ke:eq;ml<=vrq?kl:lq;
      end
      always @(posedge ck or negedge rn)if(!rn)aq<=0;else aq<=arm;
      always @(posedge ck or negedge rn)if(!rn)mq<=0;else mq<=rq|vrq;
      assign collide=rq&vrq;
      assign pc_get={4{mq}};assign pc_get_t={4{mt}};assign pc_get_v={4{mv}};
      assign pc_get_epoch={4{me}};assign pc_get_layer={4{ml}};
    end else begin:g_k
      assign collide=1'b0;
      assign pc_get={4{rq}};assign pc_get_t={4{tq}};assign pc_get_v={4{vq}};
      assign pc_get_epoch={4{eq}};assign pc_get_layer={4{lq}};
    end endgenerate
    (* keep *) reg [3:0] iv,ivv,ifault;
    (* keep *) reg [1023:0] idata;
    (* keep *) reg [55:0] it;
    (* keep *) reg [63:0] ie;
    (* keep *) reg [23:0] il;
    always @(posedge ck)begin
      idata<=pc_data;it<=pc_t;ivv<=pc_v;ie<=pc_epoch;il<=pc_layer;
      rsp_data<=idata;rsp_t<=it[13:0];rsp_v<=ivv[0];rsp_epoch<=ie[15:0];rsp_layer<=il[5:0];
    end
    always @(posedge ck or negedge rn)
      if(!rn)begin iv<=0;ifault<=0;rsp_valid<=0;fault<=0;end
      else begin
        iv<=pc_valid;ifault<=pc_fault;rsp_valid<=iv[0];
        if((|ifault)||iv!={4{iv[0]}}||collide)fault<=1;
        if(iv[0]&&((it!={4{it[13:0]}})||(ivv!={4{ivv[0]}})||(ie!={4{ie[15:0]}})||(il!={4{il[5:0]}})))fault<=1;
      end
endmodule

// Wires-only composition; each leaf has its own clock entry and physical home.
// No physical relay latency is claimed here: a routed parent must insert its
// actual balanced request/return relays and compile their fixed calendar.
module qkd_static_kv_landing_grp #(
    parameter integer STACK=0,GROUP=0,MUT=0,VMAP=0,VREQ=0
)(
    input wire ck,input wire [3:0] ck_pc,input wire rst_n,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [3:0] expected_put,input wire [39:0] expected_sector,
    input wire [3:0] actual_valid,input wire [39:0] actual_sector,
    input wire [63:0] actual_epoch,input wire [23:0] actual_layer,input wire [1023:0] actual_data,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    output wire rsp_valid,output wire [1023:0] rsp_data,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault
);
    wire [3:0] get,gv,ov,pf,vv;
    wire [55:0] gt,ot;
    wire [63:0] ge,oe;
    wire [23:0] gl,ol;
    wire [1023:0] od;
    qkd_static_kv_rowctl #(.VREQ(VREQ)) u_rowctl(
      .ck(ck),.rst_n(rst_n),.req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),.vreq_valid(vreq_valid),.vreq_t(vreq_t),.arm(arm),.epoch(epoch),.layer(layer),
      .pc_get(get),.pc_get_t(gt),.pc_get_v(gv),.pc_get_epoch(ge),.pc_get_layer(gl),
      .pc_valid(ov),.pc_data(od),.pc_t(ot),.pc_v(vv),.pc_epoch(oe),.pc_layer(ol),.pc_fault(pf),
      .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault));
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_pc
      qkd_static_kv_landing_pc #(.MUT(MUT),.VMAP(VMAP))u_pc(
       .ck(ck_pc[q]),.rst_n(rst_n),.cfg_stack(2'(STACK)),.cfg_group(3'(GROUP)),.arm(arm),.epoch(epoch),.layer(layer),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(get[q]),.get_t(gt[14*q+:14]),.get_v(gv[q]),.get_epoch(ge[16*q+:16]),.get_layer(gl[6*q+:6]),
       .out_valid(ov[q]),.out_data(od[256*q+:256]),.out_t(ot[14*q+:14]),
       .out_v(vv[q]),.out_epoch(oe[16*q+:16]),.out_layer(ol[6*q+:6]),.fault(pf[q]));
    end endgenerate
endmodule
