// Exact existing-edge descriptor, strap and FAST_ISSUE partition. No new data stage.
module ot_qwen_nknl_control_capture_v1 #(

    parameter integer W = 16, parameter integer G = 4, parameter integer IL = 8, parameter integer AW = 24,
    parameter integer NW = 16, parameter integer GT = G, parameter integer SMIN = 0, parameter integer KV_PREP = 0,
    parameter integer INT8_WEIGHT = 0, parameter integer INT8_SCALE_WCS_BASE = 0, parameter integer TMUT = 0, parameter integer IREG=1, TIDR=1, CAP_MUT=0
) (
 input wire clk,rst_n,ib_go,
 input wire [3*NW+13*AW+13-1:0] ib, input wire [15:0] tile_id,
 output wire go_i, output wire [3*NW+13*AW+13-1:0] ib_i, output wire [15:0] tile_id_i,
 output wire [1+1+((AW-1)-(0)+1)+1+((NW-1)-(0)+1)+((NW-1)-(0)+1)+((NW-1)-(0)+1)+1+1+1+1+1+1+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((3)-(0)+1)+((AW-1)-(0)+1)+((NW-1)-(0)+1)+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((NW-1)-(0)+1)+((NW-1)-(0)+1)+(($clog2(IL)-1)-(0)+1)+((AW-1)-(0)+1)+((AW-1)-(0)+1)+((NW)-(0)+1)+((NW)-(0)+1)+((AW-1)-(0)+1)+1+1+1+1-1:0] ctl_bus
);
localparam integer IBW=3*NW+13*AW+13;
reg go_q;reg [IBW-1:0] ib_q;
always @(posedge clk or negedge rst_n) if(!rst_n)go_q<=0;else go_q<=ib_go;
always @(posedge clk)ib_q<=ib ^ ((CAP_MUT==2) ? ({{(IBW-1){1'b0}},1'b1} << (IBW-3*NW-1-AW)): {IBW{1'b0}});
assign go_i=(IREG && CAP_MUT!=1)?go_q:ib_go;assign ib_i=IREG?ib_q:ib;
generate if(TIDR!=0)begin:g_tidr
(* keep *)reg[15:0] tile_id_q;always @(posedge clk)tile_id_q<=tile_id;assign tile_id_i=tile_id_q;
end else begin:g_tidn assign tile_id_i=tile_id;end endgenerate
    wire [NW-1:0] b_nout, b_tiles, b_k;
    wire          b_wsrc, b_round, b_mmode, b_oen, b_amax, b_rmax;
    wire [AW-1:0] b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs, b_wcs, b_obase, b_ots, b_ojs, b_mbase;
    wire [2:0]    b_jsh;
    wire [3:0]    b_split;
    assign {b_nout, b_tiles, b_k, b_wsrc, b_wbase, b_ts, b_ks, b_js, b_xbase, b_xks, b_xjs, b_xcs,
            b_jsh, b_split, b_wcs, b_round, b_obase, b_ots, b_ojs, b_mmode, b_oen, b_amax, b_rmax, b_mbase} = ib_i;

wire  wrom_re;
wire  kv_re;
wire [AW-1:0] wrom_addr;
wire  active;
wire [NW-1:0] nout_r;
wire [NW-1:0] tiles_r;
wire [NW-1:0] k_r;
wire  wsrc_r;
wire  round_r;
wire  oen_r;
wire  amax_r;
wire  mmode_r;
wire  rmax_r;
wire [AW-1:0] mbase_r;
wire [AW-1:0] scale_base_r;
wire [3:0] split_r;
wire [AW-1:0] wcs_r;
wire [NW-1:0] ktot_r;
wire [AW-1:0] ts_r;
wire [AW-1:0] ots_r;
wire [AW-1:0] xcs_r;
wire [NW-1:0] t;
wire [NW-1:0] k;
wire [$clog2(IL)-1:0] j;
wire [AW-1:0] cur;
wire [AW-1:0] oa;
wire [NW:0] nb;
wire [NW:0] lb;
wire [AW-1:0] xc;
wire  t_last;
wire  k_last;
wire  split_fault;
wire  pend;
    ot_qwen_w12_issue_banked_v1 #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .GT(GT), .SMIN(SMIN), .KV_PREP(KV_PREP),
        .INT8_WEIGHT(INT8_WEIGHT), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE), .TMUT(TMUT)) u_issue (
        .clk(clk), .rst_n(rst_n), .go(go_i), .i_nout(b_nout), .i_tiles(b_tiles), .i_k(b_k), .i_wsrc(b_wsrc), .i_round(b_round),
        .i_mmode(b_mmode), .i_oen(b_oen), .i_amax(b_amax), .i_rmax(b_rmax), .i_wbase(b_wbase), .i_ts(b_ts), .i_ks(b_ks),
        .i_js(b_js), .i_xbase(b_xbase), .i_xks(b_xks), .i_xjs(b_xjs), .i_xcs(b_xcs), .i_wcs(b_wcs), .i_obase(b_obase),
        .i_ots(b_ots), .i_ojs(b_ojs), .i_mbase(b_mbase), .i_jsh(b_jsh), .i_split(b_split),
        .wrom_re(wrom_re), .kv_re(kv_re), .wrom_addr(wrom_addr),
        .o_active(active),
        .o_nout_r(nout_r),
        .o_tiles_r(tiles_r),
        .o_k_r(k_r),
        .o_wsrc_r(wsrc_r),
        .o_round_r(round_r),
        .o_oen_r(oen_r),
        .o_amax_r(amax_r),
        .o_mmode_r(mmode_r),
        .o_rmax_r(rmax_r),
        .o_mbase_r(mbase_r),
        .o_scale_base_r(scale_base_r),
        .o_split_r(split_r),
        .o_wcs_r(wcs_r),
        .o_ktot_r(ktot_r),
        .o_ts_r(ts_r),
        .o_ots_r(ots_r),
        .o_xcs_r(xcs_r),
        .o_t(t),
        .o_k(k),
        .o_j(j),
        .o_cur(cur),
        .o_oa(oa),
        .o_nb(nb),
        .o_lb(lb),
        .o_xc(xc),
        .o_t_last(t_last),
        .o_k_last(k_last),
        .o_split_fault(split_fault),
        .o_pend(pend));
assign ctl_bus={wrom_re,kv_re,wrom_addr,active,nout_r,tiles_r,k_r,wsrc_r,round_r,oen_r,amax_r,mmode_r,rmax_r,mbase_r,scale_base_r,split_r,wcs_r,ktot_r,ts_r,ots_r,xcs_r,t,k,j,cur,oa,nb,lb,xc,t_last,k_last,split_fault,pend};
endmodule
