`default_nettype none
// HBM-P4-SPLIT (2026-10-23): CORE-SPLIT twins of the pinned ot_hbm_idx_score_leaf (ot_hbm_idx_score_cluster.sv) and
// ot_hbm_idx_score_quarter_static (ot_hbm_idx_score_quarter_static.sv), generated verbatim from them with ONE change each:
// the leaf core is ot_hbm_idx_chunk_rt_h (rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv: 4 key columns x 2 half-column hard cores
// ot_hidx_score_hcol, every crossing register to register, cycle-exact vs ot_hbm_idx_chunk_rt; bench
// rtl/test/hbm_idx_static/run_chunk_rt_h_equiv.sh).  Opt-in by module name: the pinned files are unchanged (the plan
// binds ot_hbm_idx_score_quarter_static_h only when it adopts the split).  Cycle cost 0.
module ot_hbm_idx_score_leaf_h #(parameter integer AUXW = 30)(
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
    ot_hbm_idx_chunk_rt_h core(.clk(clk), .clk_pair(clk_pair), .rst_n(rst_n), .hb(hb_p),
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

module ot_hbm_idx_score_quarter_static_h #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_ctl,input wire[1:0]clk_engine,clk_meta,clk_tail,
 input wire[7:0]clk_chunk,input wire[255:0]clk_hslice,input wire rst_n,
 input wire half,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,          // stack bitmap bit 2*beat+half (this quarter's lanes)
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,input wire[4395:0]key_lines,   // stack key lines 4*half .. 4*half+3
 output reg[305:0]score,output wire fault
);
 localparam integer QW = 8 + 512 + 32 + 16, KW4 = 4 * 544, SW = 1 + 1 + 4 + 128 + 4, AUXW = 30, NK = 4, NCH = 4;
 // ---------------- reset relay
 wire rst_c;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rst_c));
 // ---------------- input pin flops (no reset)
 (* keep *) reg h_r;(* keep *) reg[RANK_W-1:0]rk_r;(* keep *) reg[10:0]fo_r;(* keep *) reg[11:0]nk_r;
 (* keep *) reg ke_r;(* keep *) reg[170:0]kb_r;
 (* keep *) reg qv_r;(* keep *) reg[7:0]qh_r;(* keep *) reg[511:0]qc_r;(* keep *) reg[31:0]qs_r;(* keep *) reg[15:0]qw_r;
 (* keep *) reg bv_r;(* keep *) reg[7:0]bi_r;(* keep *) reg[4395:0]kl_r;
 always @(posedge clk_ctl)begin
  h_r<=half;rk_r<=rank;fo_r<=first_ord;nk_r<=nkeys;ke_r<=keep_en;kb_r<=keep_bitmap;
  qv_r<=ql_v;qh_r<=ql_head;qc_r<=ql_codes;qs_r<=ql_sc;qw_r<=ql_w;
  bv_r<=beat_v;bi_r<=beat_index;kl_r<=key_lines;
 end
 // ---------------- W glue (cluster W glue on the registered inputs; this quarter's 4 key lines)
 wire[19:0]g0=20'(8*TP)*20'(fo_r)+20'(8)*20'(rk_r)+20'(16*TP)*20'(bi_r);
 reg wf;
 always @* begin
  wf=0;
  if(bv_r)begin
   if(nk_r>2736||bi_r>170)wf=1;
   for(integer j=0;j<4;j=j+1)if(!kl_r[j*1099]||kl_r[j*1099+1+:10]!==10'((4*int'(h_r)+j)*128+int'(bi_r)))wf=1;
  end
 end
 wire[1:0]ev,efault,wf_d;wire[7:0]kv,fl;wire[127:0]val;wire[159:0]idx;wire[1:0]last;
 genvar e,c,l;
 for(e=0;e<2;e=e+1)begin:ge
  wire[KW4-1:0]keys;wire[3:0]valid_keys,keep_keys;
  for(l=0;l<4;l=l+1)begin:gl
   localparam integer ll=4*e+l;                               // quarter lane 0..7 = stack lane 8*half + ll
   assign keys[l*544+:544]=kl_r[(ll/2)*1099+11+(ll%2)*544+:544];
   assign valid_keys[l]=({4'd0,bi_r}*12'd16+12'(ll)+(h_r?12'd8:12'd0))<nk_r;
   assign keep_keys[l]=!ke_r||kb_r[bi_r];
  end
  // stack-cluster metadata of global engine 2*half + e: first = g0 + half*(8TP) + e*4
  wire[19:0]first=g0+(h_r?20'(8*TP):20'd0)+20'(e*4);
  wire[24:0]meta_d={(({4'd0,bi_r}+12'd1)*12'd16>=nk_r),first,4'd0};
  // ---------------- leaf row (W -> E), aux = {W fault cause, meta input 25, keep 4}
  wire qv_c [0:NCH]; wire [QW-1:0] q_c [0:NCH]; wire kv_c [0:NCH]; wire [3:0] kkv_c [0:NCH]; wire [KW4-1:0] key_c [0:NCH];
  wire [AUXW-1:0] aux_c [0:NCH]; wire [4*SW-1:0] bus_c [0:NCH];
  assign qv_c[0]=qv_r; assign q_c[0]={qh_r,qc_r,qs_r,qw_r}; assign kv_c[0]=bv_r; assign kkv_c[0]=valid_keys;
  assign key_c[0]=keys; assign aux_c[0]={wf,meta_d,keep_keys}; assign bus_c[0]='0;
  for(c=0;c<NCH;c=c+1)begin:gc
   wire [15:0] cp;
   for(l=0;l<16;l=l+1)begin:gp
    assign cp[l]=clk_hslice[e*128 + c*32 + 2*l];
   end
   wire [4*SW-1:0] bo;
   ot_hbm_idx_score_leaf_h #(.AUXW(AUXW)) leaf(.clk(clk_chunk[e*4+c]), .clk_pair(cp), .rst_n(rst_c), .hb(8'(8*c)),
    .w_qv(qv_c[c]), .w_q(q_c[c]), .w_kv(kv_c[c]), .w_kkv(kkv_c[c]), .w_key(key_c[c]), .w_aux(aux_c[c]), .w_bus(bus_c[c]),
    .e_qv(qv_c[c+1]), .e_q(q_c[c+1]), .e_kv(kv_c[c+1]), .e_kkv(kkv_c[c+1]), .e_key(key_c[c+1]), .e_aux(aux_c[c+1]), .e_bus(bo));
   assign bus_c[c+1]=bo;
  end
  // ---------------- E glue of row e (verbatim ot_hbm_idx_score_cluster)
  wire eclk=clk_engine[e];
  wire qv_e=qv_c[NCH], kv_e=kv_c[NCH]; wire [AUXW-1:0] aux_e=aux_c[NCH]; wire [4*SW-1:0] bus_e=bus_c[NCH];
  wire [3:0] keep_d;
  ot_hdc_delay #(.W(4),.D(106)) keep_pipe(.clk(eclk),.rst_n(rst_c),.d(aux_e[3:0]),.q(keep_d));
  wire [3:0] son, sv; wire [3:0] skv [0:3]; wire [127:0] ssum [0:3]; wire [3:0] sfl [0:3];
  for(c=0;c<4;c=c+1)begin:gs
   assign {son[c], sv[c], skv[c], ssum[c], sfl[c]} = bus_e[c*SW +: SW];
  end
  reg [3:0] ready1,ready2; reg online_q; reg fault_q; reg [1:0] settle;
  always @(posedge eclk or negedge rst_c)begin
   if(!rst_c)begin ready1<=0;ready2<=0;online_q<=0;fault_q<=0;settle<=0;end
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
  ot_hbm_idx_tail_native u_t (.clk(clk_tail[e]), .rst_n(rst_c), .i_v(sv[0]), .i_kv(skv[0]),
   .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));
  reg ov; reg [3:0] ok, ofl; reg [63:0] os;
  always @(posedge eclk or negedge rst_c) if(!rst_c) ov<=0; else ov<=tv;
  always @(posedge eclk) begin ok<=tkv; os<=ts; ofl<=tf; end
  assign ev[e]=ov; assign kv[e*4+:4]=ok; assign val[e*64+:64]=os;
  wire[24:0]meta;
  hidx_meta_w25_d123_r0 md(.clk(clk_meta[e]),.rst_n(rst_c),.d(aux_e[28:4]),.q(meta));
  for(l=0;l<4;l=l+1)begin:go
   assign idx[(e*4+l)*20+:20]=meta[23:4]+20'(l);
  end
  assign last[e]=meta[24];
  assign fl[e*4+:4]=ofl|meta[3:0];
  assign wf_d[e]=aux_e[29];
 end
 // ---------------- output pin flops (registered score; data unreset, ev reset)
 always @(posedge clk_ctl or negedge rst_c)
  if(!rst_c)score[0]<=1'b0; else score[0]<=ev[0];
 always @(posedge clk_ctl)score[305:1]<={idx,val,kv,fl,last[0]};
 // Diagnostic-only checker consumes the registered score metadata. Data lanes and
 // their valid/ordinal cycles are unchanged; the existing sticky fault gains
 // valid-key arithmetic errors which formerly remained only in score.fl.
 ot_hbm_idx_score_fault_static score_fault_check(.clk(clk_ctl),.rst_n(rst_c),
  .score_status(score[17:0]),.protocol_fault({wf_d[0],(ev[1]!=ev[0]),efault}),.fault(fault));
endmodule
`default_nettype wire
