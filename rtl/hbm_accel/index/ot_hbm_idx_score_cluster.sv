`timescale 1ns/1ps
`default_nettype none
// IDX-SCORE CLUSTER (H-NETLIST/IDX-SCORE 2026-10-17; H-ELEM approved the registered W->E seam chain, +4 scorer edges,
// ledger IDX.SCORE_CHAIN; H-DIE slot <= 3050 um, 16 head-pair roots per leaf). Same ports and the same arithmetic as
// ot_hbm_idx_score_static; every output 8 edges later (the compiler shifts the selector by 8: hbm_idx_static_calendar.py
// --score-chain 8). Each leaf hop is 2 registers (W pin, E pin: the 450 um reach rule), 4 hops = +8.
//   * 4 x 4 IDENTICAL leaves ot_hbm_idx_score_leaf: row e = engine e (keys of lanes 4e..4e+3), column c = chunk c (heads
//     8c..8c+7, strap hb = 8c). Query, keys and a 30-bit aux word (keep, meta input, W fault cause) enter row e at the W
//     face of leaf (e,0) and are forwarded leaf to leaf through each leaf's W and E pin registers (+2 edges a hop).
//   * sum bus: 4 slots x 138 b {online, v, kv, sum, fault}; leaf c writes slot c from its core and registers the other
//     slots through (W reg, E reg), so every slot reaches the E face of leaf (e,3) at the same age (+8).
//   * W glue (clk_ctl): key line split, valid/keep lanes, meta input, the scorer's W fault checks (combinational into the
//     flop-first leaf (e,0) pins). E glue per row (clk_engine/clk_tail/clk_meta): keep delay, engine settle/online fault,
//     ot_hbm_idx_tail_native, output registers, the d123 meta delay; the scorer fault register (clk_ctl).
// Every leaf pin is registered (flop-first in, register-driven out); seams between leaves are register to register.
module ot_hbm_idx_score_leaf #(parameter integer AUXW = 30)(
    input  wire clk, input wire [15:0] clk_pair, input wire rst_n, input wire [7:0] hb,
    input  wire w_qv, input wire [QW-1:0] w_q, input wire w_kv, input wire [3:0] w_kkv, input wire [KW4-1:0] w_key,
    input  wire [AUXW-1:0] w_aux, input wire [4*SW-1:0] w_bus,
    output wire e_qv, output wire [QW-1:0] e_q, output wire e_kv, output wire [3:0] e_kkv, output wire [KW4-1:0] e_key,
    output wire [AUXW-1:0] e_aux, output reg [4*SW-1:0] e_bus
);
    localparam integer QW = 8 + 512 + 32 + 16, KW4 = 4 * 544, SW = 1 + 1 + 4 + 128 + 4;
    reg f_qv; reg [QW-1:0] f_q; reg f_kv; reg [3:0] f_kkv; reg [KW4-1:0] f_key; reg [AUXW-1:0] f_aux; reg [7:0] hb_p;
    always @(posedge clk) begin
        f_qv <= w_qv; f_q <= w_q; f_kv <= w_kv; f_kkv <= w_kkv; f_key <= w_key; f_aux <= w_aux; hb_p <= hb;
    end
    // E pin registers: a W->E hop is W pin reg -> E pin reg (~half a leaf + the channel each, within the 450 um reach)
    reg g_qv; reg [QW-1:0] g_q; reg g_kv; reg [3:0] g_kkv; reg [KW4-1:0] g_key; reg [AUXW-1:0] g_aux;
    always @(posedge clk) begin g_qv <= f_qv; g_q <= f_q; g_kv <= f_kv; g_kkv <= f_kkv; g_key <= f_key; g_aux <= f_aux; end
    assign e_qv = g_qv; assign e_q = g_q; assign e_kv = g_kv; assign e_kkv = g_kkv; assign e_key = g_key; assign e_aux = g_aux;
    wire c_v_u, on; wire [3:0] c_kv_u, c_f_u; wire [127:0] c_s_u;
    wire n_v; wire [3:0] n_kv, n_f; wire [127:0] n_s;
    ot_hbm_idx_chunk_rt core(.clk(clk), .clk_pair(clk_pair), .rst_n(rst_n), .hb(hb_p),
        .ql_v(f_qv), .ql_head(f_q[QW-1 -: 8]), .ql_codes(f_q[QW-9 -: 512]), .ql_sc(f_q[47:16]), .ql_w(f_q[15:0]),
        .k_v(f_kv), .k_kv(f_kkv), .k_key(f_key),
        .c_v(c_v_u), .c_kv(c_kv_u), .c_sum(c_s_u), .c_fault(c_f_u), .online(on),
        .n_v(n_v), .n_kv(n_kv), .n_sum(n_s), .n_fault(n_f));
    // sum bus: W pin reg (own slot written here from the core) -> E pin reg; every slot ages 2 edges a leaf
    wire [1:0] own = hb_p[4:3];
    reg [4*SW-1:0] b_w;
    integer k;
    always @(posedge clk) begin
        for (k = 0; k < 4; k = k + 1)
            b_w[k*SW +: SW] <= (2'(k) == own) ? {on, n_v, n_kv, n_s, n_f} : w_bus[k*SW +: SW];
        e_bus <= b_w;
    end
endmodule

module ot_hbm_idx_score_cluster #(parameter integer MUT=0,TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_ctl,input wire[3:0]clk_engine,clk_meta,clk_tail,
 input wire[15:0]clk_chunk,input wire[511:0]clk_hslice,input wire rst_n,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[341:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,input wire[8791:0]key_lines,
 output wire[609:0]score,output reg fault
);
 localparam integer QW = 8 + 512 + 32 + 16, KW4 = 4 * 544, SW = 1 + 1 + 4 + 128 + 4, AUXW = 30, NK = 4, NCH = 4;
 // ---------------- W glue: lanes, meta input, W fault cause (all combinational into the flop-first leaf pins)
 wire[19:0]g0=20'(8*TP)*20'(first_ord)+20'(8)*20'(rank)+20'(16*TP)*20'(beat_index);
 wire wfault_cause;
 reg wf;
 integer p;
 always @* begin
  wf=0;
  if(beat_v)begin
   if(nkeys>2736||beat_index>170)wf=1;
   for(p=0;p<8;p=p+1)if(!key_lines[p*1099]||key_lines[p*1099+1+:10]!==10'(p*128+int'(beat_index)))wf=1;
  end
 end
 assign wfault_cause=wf;
 wire[3:0]ev,efault;
 wire[15:0]kv,fl;
 wire[255:0]val;
 wire[319:0]idx;
 wire[3:0]last;
 wire [3:0] wf_d;
 genvar e, c, l;
 for(e=0;e<4;e=e+1)begin:ge
  wire[KW4-1:0]keys;
  wire[3:0]valid_keys,keep_keys;
  for(l=0;l<4;l=l+1)begin:gl
   localparam integer lane=4*e+l;
   assign keys[l*544+:544]=key_lines[(lane/2)*1099+11+(lane%2)*544+:544];
   assign valid_keys[l]=({4'd0,beat_index}*12'd16+12'(lane))<nkeys;
   assign keep_keys[l]=!keep_en||keep_bitmap[int'(beat_index)*2+lane/8];
  end
  wire[19:0]first=g0+20'((e/2)*(8*TP)+(e%2)*4);
  wire[24:0]meta_d={(({4'd0,beat_index}+12'd1)*12'd16>=nkeys),first,4'd0};
  // ---------------- leaf row (W -> E), aux = {W fault cause, meta input 25, keep 4}
  wire qv_c [0:NCH]; wire [QW-1:0] q_c [0:NCH]; wire kv_c [0:NCH]; wire [3:0] kkv_c [0:NCH]; wire [KW4-1:0] key_c [0:NCH];
  wire [AUXW-1:0] aux_c [0:NCH]; wire [4*SW-1:0] bus_c [0:NCH];
  assign qv_c[0]=ql_v; assign q_c[0]={ql_head,ql_codes,ql_sc,ql_w}; assign kv_c[0]=beat_v; assign kkv_c[0]=valid_keys;
  assign key_c[0]=keys; assign aux_c[0]={wfault_cause,meta_d,keep_keys}; assign bus_c[0]='0;
  for(c=0;c<NCH;c=c+1)begin:gc
   localparam integer CK = e*4 + c;
   wire [15:0] cp;
   for(l=0;l<16;l=l+1)begin:gp
    assign cp[l]=clk_hslice[e*128 + c*32 + 2*l];
   end
`ifdef OT_IDX_CL_MUT_SWAP
   localparam [7:0] HB = (e==0 && c<2) ? 8'(8*(c^1)) : 8'(8*c);     // mutant: leaves (0,0) and (0,1) swapped
`else
   localparam [7:0] HB = 8'(8*c);
`endif
   wire qv_i, kv_i; wire [QW-1:0] q_i; wire [3:0] kkv_i; wire [KW4-1:0] key_i; wire [AUXW-1:0] aux_i; wire [4*SW-1:0] bus_i;
`ifdef OT_IDX_CL_MUT_SEAM
   if (e==0 && c==2) begin : g_mseam                                 // mutant: seam leaf(0,1)->leaf(0,2) one edge late
    reg x_qv, x_kv; reg [QW-1:0] x_q; reg [3:0] x_kkv; reg [KW4-1:0] x_key; reg [AUXW-1:0] x_aux; reg [4*SW-1:0] x_bus;
    always @(posedge clk_chunk[CK]) begin
     x_qv<=qv_c[c]; x_q<=q_c[c]; x_kv<=kv_c[c]; x_kkv<=kkv_c[c]; x_key<=key_c[c]; x_aux<=aux_c[c]; x_bus<=bus_c[c];
    end
    assign qv_i=x_qv; assign q_i=x_q; assign kv_i=x_kv; assign kkv_i=x_kkv; assign key_i=x_key; assign aux_i=x_aux; assign bus_i=x_bus;
   end else begin : g_nseam
    assign qv_i=qv_c[c]; assign q_i=q_c[c]; assign kv_i=kv_c[c]; assign kkv_i=kkv_c[c]; assign key_i=key_c[c]; assign aux_i=aux_c[c]; assign bus_i=bus_c[c];
   end
`else
   assign qv_i=qv_c[c]; assign q_i=q_c[c]; assign kv_i=kv_c[c]; assign kkv_i=kkv_c[c]; assign key_i=key_c[c]; assign aux_i=aux_c[c]; assign bus_i=bus_c[c];
`endif
   wire [4*SW-1:0] bo;
   ot_hbm_idx_score_leaf #(.AUXW(AUXW)) leaf(.clk(clk_chunk[CK]), .clk_pair(cp), .rst_n(rst_n), .hb(HB),
    .w_qv(qv_i), .w_q(q_i), .w_kv(kv_i), .w_kkv(kkv_i), .w_key(key_i), .w_aux(aux_i), .w_bus(bus_i),
    .e_qv(qv_c[c+1]), .e_q(q_c[c+1]), .e_kv(kv_c[c+1]), .e_kkv(kkv_c[c+1]), .e_key(key_c[c+1]), .e_aux(aux_c[c+1]), .e_bus(bo));
   assign bus_c[c+1]=bo;
  end
  // ---------------- E glue of row e (ot_hbm_idx_engine_static logic + tail + output regs, all 8 edges later)
  wire eclk=clk_engine[e];
  wire qv_e=qv_c[NCH], kv_e=kv_c[NCH]; wire [AUXW-1:0] aux_e=aux_c[NCH]; wire [4*SW-1:0] bus_e=bus_c[NCH];
  wire [3:0] keep_d;
  ot_hdc_delay #(.W(4),.D(106)) keep_pipe(.clk(eclk),.rst_n(rst_n),.d(aux_e[3:0]),.q(keep_d));
  wire [3:0] son, sv; wire [3:0] skv [0:3]; wire [127:0] ssum [0:3]; wire [3:0] sfl [0:3];
  for(c=0;c<4;c=c+1)begin:gs
   assign {son[c], sv[c], skv[c], ssum[c], sfl[c]} = bus_e[c*SW +: SW];
  end
  reg [3:0] ready1,ready2; reg online_q; reg fault_q; reg [1:0] settle;
  always @(posedge eclk or negedge rst_n)begin
   if(!rst_n)begin ready1<=0;ready2<=0;online_q<=0;fault_q<=0;settle<=0;end
   else begin
    if(qv_e)settle<=3;else if(settle!=0)settle<=settle-1;
    ready1<=son;ready2<=ready1;online_q<=&ready2;
    if(kv_e && (!online_q||qv_e||settle!=0))fault_q<=1;
   end
  end
  assign efault[e]=fault_q;
  wire [NK*NCH*32-1:0] tsum; wire [NK*NCH-1:0] tfl;
  for(l=0;l<NK;l=l+1)begin:g_transpose
   for(c=0;c<NCH;c=c+1)begin:g_chunk
    assign tsum[(l*NCH+c)*32+:32]=ssum[c][32*l+:32];
    assign tfl[l*NCH+c]=sfl[c][l];
   end
  end
  wire tv; wire [NK-1:0] tkv, tf; wire [NK*16-1:0] ts;
  ot_hbm_idx_tail_native u_t (.clk(clk_tail[e]), .rst_n(rst_n), .i_v(sv[0]), .i_kv(skv[0]),
   .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));
  reg ov; reg [3:0] ok, ofl; reg [63:0] os;
  always @(posedge eclk or negedge rst_n) if(!rst_n) ov<=0; else ov<=tv;
  always @(posedge eclk) begin ok<=tkv; os<=ts; ofl<=tf; end
  assign ev[e]=ov; assign kv[e*4+:4]=ok; assign val[e*64+:64]=os;
  wire[24:0]meta;
  hidx_meta_w25_d123_r0 md(.clk(clk_meta[e]),.rst_n(rst_n),.d(aux_e[28:4]),.q(meta));
  for(l=0;l<4;l=l+1)begin:go
   assign idx[(e*4+l)*20+:20]=meta[23:4]+20'(l);
  end
  assign last[e]=meta[24];
  assign fl[e*4+:4]=ofl|meta[3:0];
  assign wf_d[e]=aux_e[29];
 end
 assign score={idx,val,kv,fl,last[0],ev[0]};
 always @(posedge clk_ctl or negedge rst_n)begin
  if(!rst_n)fault<=0;
  else if((|efault)||(ev!={4{ev[0]}})||wf_d[0])fault<=1;
 end
endmodule
`default_nettype wire
