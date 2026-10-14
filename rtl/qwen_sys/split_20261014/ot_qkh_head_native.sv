`timescale 1ns/1ps
// KV/system head candidate: preserve the HS reference pipeline and FP32 consumer
// rounding, with no state in the parent. The die delivers a separate phi-R entry
// to every hardened child. Functional equivalence ties all entries to one clock;
// physical qualification also needs assigned slots, native pin audits and STA.
module ot_qkh_head_front_native #(
    parameter integer Q_FP32=1, parameter integer MUT=0
)(input wire clk, rst_n,
  input wire [3:0] c_in, input wire [1023:0] row_in,
  input wire [15:0] e_in, input wire [11:0] lt_in,
  input wire [1:0] hid, input wire q_valid_in,
  input wire [5:0] q_beat_in, input wire [511:0] q_data_in,
  output wire [15:0] f_cr, output wire [1560:0] f_dr,
  output wire pack_fault);
  localparam integer HD=128, LTW=12, NRS=1;
  wire [0:0] rr;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
    (.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  wire rp=rr[0];
    // ---- S2: the tile pins -----------------------------------------------------------------------------------------------
    reg  [3:0]       c2;
    reg  [HD*8-1:0]  row2;
    reg  [15:0]      e2;
    reg  [LTW-1:0]   lt2;
    reg              qv2;
    reg  [5:0]       qb2;
    reg  [511:0]     qd2;
    reg  [1:0]       hid2;
    always @(posedge clk or negedge rp)
        if (!rp) begin c2[3:1] <= 3'd0; lt2 <= {LTW{1'b0}}; qv2 <= 1'b0; end
        else begin c2[3:1] <= c_in[3:1]; lt2 <= lt_in; qv2 <= q_valid_in; end
    always @(posedge clk) begin c2[0] <= c_in[0]; row2 <= row_in; e2 <= e_in; qb2 <= q_beat_in; qd2 <= q_data_in; hid2 <= hid; end
    // Native FP32 transport uses twice the legacy beat count. Round at the
    // canonical attention consumption point, pair consecutive beats, and retain
    // each hardened lane's 128-bit BF16 face. No producer-side Q narrowing.
    wire qv_send;
    wire [5:0] qb_send;
    wire [511:0] qd_send;
    wire q_pack_fault;
    generate if (Q_FP32 != 0) begin : g_qfp32
        wire [255:0] rounded;
        genvar qi;
        for (qi=0; qi<16; qi=qi+1) begin : g_round
            wire [31:0] x=qd2[32*qi +: 32];
            assign rounded[16*qi +:16]=x[31:16]+(x[15] && (|x[14:0] || x[16]));
        end
        reg [255:0] lower;
        reg [4:0] pair_tag;
        reg half_valid, pack_fault;
        always @(posedge clk or negedge rp)
            if (!rp) begin half_valid<=0;pack_fault<=0;end
            else if(qv2) begin
                if(!qb2[0]) begin half_valid<=1;if(half_valid) pack_fault<=1;end
                else begin
                    half_valid<=0;
                    if(!half_valid || pair_tag!=qb2[5:1]) pack_fault<=1;
                end
            end
        always @(posedge clk) if(qv2 && !qb2[0]) begin lower<=rounded;pair_tag<=qb2[5:1];end
        assign qv_send=qv2 && qb2[0] && half_valid && pair_tag==qb2[5:1];
        assign qb_send={1'b0,qb2[5:1]};
        assign qd_send={rounded,lower};
        assign q_pack_fault=pack_fault;
    end else begin : g_qbf16
        assign qv_send=qv2;assign qb_send=qb2;assign qd_send=qd2;assign q_pack_fault=0;
    end endgenerate
    // ---- S2b (q13-rhead r2, structural): the S-face pin flops no longer drive the 16 per-sub-tile relays directly.
    // Route evidence qkh_head_hs_ref-q13a-75e0349aa: qd2[392] (S face, y = 0) -> g_t[15].u_rid/r[0] (row 3 of the 4 x 4
    // floor, y > 560 um) = 765 ps of data path through 7 wire repeaters in ONE cycle (TT -41.92 ps; 11 endpoints, all rows
    // 2 / 3).  NRS shared stages carry every pin bit to the floor centre first, so each hop is pin -> centre (<= ~430 um)
    // and centre -> sub-tile relay (<= ~350 um).  Shared (1,577 flops a stage), not one copy a sub-tile (3,728): the
    // parent stays under 15k sinks on its clock root.  Latency + NRS on every input (HXK / HXN of the control tile).
    wire [3+LTW:0]  cs_o;                     // reset part: {c[3:1], lt, qv}
    wire [HD*8+16+6+512+2:0] ds_o;            // plain part: {c[0], row, e, qb, qd, hid}
    (* keep_hierarchy *) ot_qkh_relay #(.W(4 + LTW), .D(NRS), .RST(1)) u_rsc (.clk(clk), .rst_n(rp), .d({c2[3:1], lt2, qv_send}), .q(cs_o));
    (* keep_hierarchy *) ot_qkh_relay #(.W(1 + HD*8 + 16 + 6 + 512 + 2), .D(NRS)) u_rsd (.clk(clk), .rst_n(rp),
                                                                                    .d({c2[0], row2, e2, qb_send, qd_send, hid2}), .q(ds_o));
    wire [3:0]       c3   = {cs_o[3+LTW:1+LTW], ds_o[HD*8+16+6+512+2]};
    wire [LTW-1:0]   lt3  = cs_o[LTW:1];
    wire             qv3  = cs_o[0];
    wire [HD*8-1:0]  row3 = ds_o[16+6+512+2 +: HD*8];
    wire [15:0]      e3   = ds_o[6+512+2 +: 16];
    wire [5:0]       qb3  = ds_o[512+2 +: 6];
    wire [511:0]     qd3  = ds_o[2 +: 512];
    wire [1:0]       hid3 = ds_o[1:0];
  assign f_cr=cs_o;
  assign f_dr=(MUT==1) ? {ds_o[1560:2],~ds_o[1:0]} : ds_o;
  assign pack_fault=q_pack_fault;
endmodule

module ot_qkh_head_station_native #(
  parameter integer MUT=0
)(input wire clk,rst_n,
  input wire [15:0] cr_i,input wire [216:0] dr_i,
  input wire [31:0] kp_i,input wire kpv_i,gf_i,input wire [63:0] nb_i,
  output wire [15:0] cr_o,output wire [216:0] dr_o,
  output wire [31:0] kp_o,output wire kpv_o,gf_o,
  output wire [63:0] nb_o,output wire lane_rst_n);
  wire [0:0] rr;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
    (.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  assign lane_rst_n=rr[0];
  ot_qkh_relay #(.W(16),.D(2),.RST(1)) u_ric (.clk(clk),.rst_n(rr[0]),.d(cr_i),.q(cr_o));
  ot_qkh_relay #(.W(217),.D(2)) u_rid (.clk(clk),.rst_n(rr[0]),.d(dr_i),.q(dr_o));
  ot_qkh_relay #(.W(32),.D(2)) u_rkd (.clk(clk),.rst_n(rr[0]),.d(kp_i),.q(kp_o));
  ot_qkh_relay #(.W(2),.D(2),.RST(1)) u_rkv (.clk(clk),.rst_n(rr[0]),.d({kpv_i,gf_i}),.q({kpv_o,gf_o}));
  ot_qkh_relay #(.W(64),.D(2)) u_rn (.clk(clk),.rst_n(rr[0]),.d(MUT==2 ? {nb_i[31:0],nb_i[63:32]}:nb_i),.q(nb_o));
endmodule

module ot_qkh_head_score_native #(
  parameter integer MUT=0
)(input wire clk,rst_n,input wire [31:0] sc_i,
  input wire sf_i,gf_i,pack_fault,
  output wire [31:0] sc_o,output wire sf_o,gf_o,
  output wire kt_rst_n);
  wire [0:0] rr;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
    (.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  assign kt_rst_n=rr[0];
  ot_qkh_relay #(.W(32),.D(1)) u_ros (.clk(clk),.rst_n(rr[0]),.d(sc_i),.q(sc_o));
  ot_qkh_relay #(.W(2),.D(1),.RST(1)) u_rof (.clk(clk),.rst_n(rr[0]),
    .d({sf_i,gf_i | (MUT==3 ? 1'b0 : pack_fault)}),.q({sf_o,gf_o}));
endmodule

module ot_qkh_head_native #(
  parameter integer Q_FP32=1,parameter integer MUT=0
)(input wire ck_front,ck_score,ck_kt,
  input wire [15:0] ck_station,ck_lane,
  input wire rst_n,input wire [3:0] c_in,input wire [1023:0] row_in,
  input wire [15:0] e_in,input wire [11:0] lt_in,input wire [1:0] hid,
  input wire q_valid_in,input wire [5:0] q_beat_in,input wire [511:0] q_data_in,
  output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d);
  wire [15:0] f_cr;wire [1560:0] f_dr;wire pack_fault;
  ot_qkh_head_front_native #(.Q_FP32(Q_FP32),.MUT(MUT)) u_front
    (.clk(ck_front),.rst_n(rst_n),.c_in(c_in),.row_in(row_in),.e_in(e_in),.lt_in(lt_in),.hid(hid),
     .q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),.f_cr(f_cr),.f_dr(f_dr),.pack_fault(pack_fault));
  wire [511:0] kp_t,kp_k;wire [15:0] kpv_t,kpv_k,gf_t,gf_k;
  wire [1023:0] nb_t;wire [15:0] lane_rst_n;
  genvar t;
  generate for(t=0;t<16;t=t+1) begin:g_t
    wire [15:0] cr_i=f_cr,cr_o;
    wire [216:0] dr_i={f_dr[1560],f_dr[536+64*t +:64],f_dr[520 +:16],
      f_dr[514 +:6],f_dr[2+128*(t%4) +:128],f_dr[1:0]},dr_o;
    ot_qkh_head_station_native #(.MUT(MUT)) u_station
      (.clk(ck_station[t]),.rst_n(rst_n),.cr_i(cr_i),.dr_i(dr_i),.cr_o(cr_o),.dr_o(dr_o),
       .kp_i(kp_t[32*t +:32]),.kpv_i(kpv_t[t]),.gf_i(gf_t[t]),.nb_i(nb_t[64*t +:64]),
       .kp_o(kp_k[32*t +:32]),.kpv_o(kpv_k[t]),.gf_o(gf_k[t]),.nb_o(nb_d[64*t +:64]),.lane_rst_n(lane_rst_n[t]));
    ot_qkh_lane8 u_l8 (.clk(ck_lane[t]),.rst_n(lane_rst_n[t]),
      .c_in({cr_o[15:13],dr_o[216]}),.row_in(dr_o[215:152]),.e_in(dr_o[151:136]),.lt_in(cr_o[12:1]),
      .hid(dr_o[1:0]),.bsel(2'(t/4)),.q_valid_in(cr_o[0]),.q_beat_in(dr_o[135:130]),.q_data_in(dr_o[129:2]),
      .kp(kp_t[32*t +:32]),.kpv(kpv_t[t]),.nb(nb_t[64*t +:64]),.gf(gf_t[t]));
  end endgenerate
  wire [31:0] sc_k;wire sf_k,gf_kt,kt_rst_n;
  ot_qkh_ktree u_kt (.clk(ck_kt),.rst_n(kt_rst_n),.kp_in(kp_k),.kpv_in(kpv_k[0]),.gf_in(gf_k),
    .sc_d(sc_k),.sc_f(sf_k),.g_f(gf_kt));
  ot_qkh_head_score_native #(.MUT(MUT)) u_score
    (.clk(ck_score),.rst_n(rst_n),.sc_i(sc_k),.sf_i(sf_k),.gf_i(gf_kt),.pack_fault(pack_fault),
     .sc_o(sc_d),.sf_o(sc_f),.gf_o(g_f),.kt_rst_n(kt_rst_n));
endmodule
