`timescale 1ns/1ps
// r4: four front quarters and one fault-merging score leaf; 86 separate entries.
// Existing capture/packing/relay edges and FP32 consumer rounding remain unchanged.
module ot_qkh_head_frontq_native #(
    parameter integer Q_FP32=1, parameter integer MUT=0,
    // KVG3-CORES 10-24 (COORD ruling 2, face_guard not relaxed): PORT_REGS=1 gives every f_t<k> output bit its own launch
    // flop in RTL (per-port copies of the NRS relay stage, same D, same edge) instead of one relay stage whose 41 shared
    // bits ({cr 16, c0, e 16, qb 6, hid 2}) fan out to all four ports (left to the flow's pin_reg_split in partition
    // kits).  0 cycles, identical outputs every edge (miter); +123 flops (4 x 233 vs 809).  PORT_REGS=0 = original.
    parameter integer PORT_REGS=0
)(input wire clk, rst_n,
  input wire [3:0] c_in, input wire [255:0] row_in,
  input wire [15:0] e_in, input wire [11:0] lt_in,
  input wire [1:0] hid, input wire q_valid_in,
  input wire [5:0] q_beat_in, input wire [511:0] q_data_in,
  // kvsys-elements r2 2026-10-14: one 233-bit port a station ({cr 16, dr 217}, the parent's former slice of f_cr/f_dr),
  // so the die-assigned pin plan puts each station's bits on the S-face range that faces it (pin_reg_split gives every
  // output pin its own launch flop: the shared bits are duplicated by the flow, not in RTL).
  output wire [232:0] f_t0,
  output wire [232:0] f_t1,
  output wire [232:0] f_t2,
  output wire [232:0] f_t3,
  output wire pack_fault);
  localparam integer HD=32, LTW=12, NRS=1;
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
    generate if (PORT_REGS == 0) begin : g_rs
      (* keep_hierarchy *) ot_qkh_relay #(.W(4 + LTW), .D(NRS), .RST(1)) u_rsc (.clk(clk), .rst_n(rp), .d({c2[3:1], lt2, qv_send}), .q(cs_o));
      (* keep_hierarchy *) ot_qkh_relay #(.W(1 + HD*8 + 16 + 6 + 512 + 2), .D(NRS)) u_rsd (.clk(clk), .rst_n(rp),
                                                                                    .d({c2[0], row2, e2, qb_send, qd_send, hid2}), .q(ds_o));
    end else begin : g_rs0
      assign cs_o = 'd0; assign ds_o = 'd0;     // unused (the per-port stages below drive the outputs)
    end endgenerate
    wire [3:0]       c3   = {cs_o[3+LTW:1+LTW], ds_o[HD*8+16+6+512+2]};
    wire [LTW-1:0]   lt3  = cs_o[LTW:1];
    wire             qv3  = cs_o[0];
    wire [HD*8-1:0]  row3 = ds_o[16+6+512+2 +: HD*8];
    wire [15:0]      e3   = ds_o[6+512+2 +: 16];
    wire [5:0]       qb3  = ds_o[512+2 +: 6];
    wire [511:0]     qd3  = ds_o[2 +: 512];
    wire [1:0]       hid3 = ds_o[1:0];
  wire [232:0] f_t [0:3];
  genvar ft;
  generate if (PORT_REGS == 0) begin : g_shared
    wire [15:0] f_cr=cs_o;
    wire [792:0] f_dr=(MUT==1) ? {ds_o[792:2],~ds_o[1:0]} : ds_o;
    for(ft=0;ft<4;ft=ft+1) begin:g_ft
      assign f_t[ft]={f_cr,f_dr[792],f_dr[536+64*ft +:64],f_dr[520 +:16],f_dr[514 +:6],f_dr[2+128*(ft%4) +:128],f_dr[1:0]};
    end
  end else begin : g_port
    // the same relay D words, sliced per port before the stage: port ft = {cr, c0, row[64ft+:64], e, qb, qd[128ft+:128], hid}
    for(ft=0;ft<4;ft=ft+1) begin:g_ft
      wire [15:0]  pc;
      wire [216:0] pd;
      (* keep_hierarchy *) ot_qkh_relay #(.W(4 + LTW), .D(NRS), .RST(1)) u_rsc (.clk(clk), .rst_n(rp),
                                                                             .d({c2[3:1], lt2, qv_send}), .q(pc));
      (* keep_hierarchy *) ot_qkh_relay #(.W(217), .D(NRS)) u_rsd (.clk(clk), .rst_n(rp),
`ifdef KVG3_FRONTQ_PRMUT
          // bench mutant (must FAIL): port ft takes the neighbouring port's Q slice
          .d({c2[0], row2[64*ft +:64], e2, qb_send, qd_send[128*((ft+1)%4) +:128], hid2}), .q(pd));
`else
          .d({c2[0], row2[64*ft +:64], e2, qb_send, qd_send[128*ft +:128], hid2}), .q(pd));
`endif
      assign f_t[ft]={pc, pd[216:2], (MUT==1) ? ~pd[1:0] : pd[1:0]};
    end
  end endgenerate
  assign f_t0=f_t[0];
  assign f_t1=f_t[1];
  assign f_t2=f_t[2];
  assign f_t3=f_t[3];
  assign pack_fault=q_pack_fault;
endmodule

// kvsys-elements r2 2026-10-14: the per-lane station is split into its two directions so the die can place each
// where its hops are short (head plan results/arch/qwen_split_1014/head_native_plan_r2.json): stin (front -> lane,
// cr/dr two stages, lane reset) beside the lane's S-face input corner, stout (lane -> ktree kp/kpv/gf and lane -> die
// nb, two stages each) between the lane's E face, the ktree N face and the astk face.  Same stages, same cycles.
module ot_qkh_head_score4_native #(
  parameter integer MUT=0
)(input wire clk,rst_n,input wire [31:0] sc_i,
  input wire sf_i,gf_i,input wire [3:0] pack_fault,
  output wire [31:0] sc_o,output wire sf_o,gf_o,
  output wire kt_rst_n);
  wire [0:0] rr;
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst
    (.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  assign kt_rst_n=rr[0];
  ot_qkh_relay #(.W(32),.D(1)) u_ros (.clk(clk),.rst_n(rr[0]),.d(sc_i),.q(sc_o));
  ot_qkh_relay #(.W(2),.D(1),.RST(1)) u_rof (.clk(clk),.rst_n(rr[0]),
    .d({sf_i,gf_i | (MUT==3 ? 1'b0 : (|pack_fault))}),.q({sf_o,gf_o}));
endmodule

module ot_qkh_head_native_r4 #(
  parameter integer Q_FP32=1,parameter integer MUT=0
)(input wire [3:0] ck_front,input wire ck_score,ck_kt,
  input wire [15:0] ck_stin,ck_stk,ck_nb1,ck_nb2,ck_lane,
  input wire rst_n,input wire [3:0] c_in,input wire [1023:0] row_in,
  input wire [15:0] e_in,input wire [11:0] lt_in,input wire [1:0] hid,
  input wire q_valid_in,input wire [5:0] q_beat_in,input wire [511:0] q_data_in,
  output wire [31:0] sc_d,output wire sc_f,g_f,output wire [1023:0] nb_d);
  wire [232:0] f_t [0:15];wire [3:0] pack_fault;
  genvar g;
  generate for(g=0;g<4;g=g+1) begin:g_front
    // Each row quarter keeps the original full Q packing; local lane j selects Q fragment j.
    ot_qkh_head_frontq_native #(.Q_FP32(Q_FP32),.MUT(MUT)) u_front
      (.clk(ck_front[g]),.rst_n(rst_n),.c_in(c_in),.row_in(row_in[256*g +:256]),.e_in(e_in),.lt_in(lt_in),
       .hid(hid),.q_valid_in(q_valid_in),.q_beat_in(q_beat_in),.q_data_in(q_data_in),
       .f_t0(f_t[4*g]),.f_t1(f_t[4*g+1]),.f_t2(f_t[4*g+2]),.f_t3(f_t[4*g+3]),.pack_fault(pack_fault[g]));
  end endgenerate
  wire [511:0] kp_t,kp_k;wire [15:0] kpv_t,kpv_k,gf_t,gf_k;
  wire [1023:0] nb_t;wire [15:0] lane_rst_n;
  genvar t;
  generate for(t=0;t<16;t=t+1) begin:g_t
    wire [15:0] cr_o;wire [216:0] dr_o;
    ot_qkh_head_stin_native #(.MUT(MUT)) u_stin
      (.clk(ck_stin[t]),.rst_n(rst_n),.cr_i(f_t[t][232:217]),.dr_i(f_t[t][216:0]),.cr_o(cr_o),.dr_o(dr_o),
       .lane_rst_n(lane_rst_n[t]));
    ot_qkh_head_stk_native #(.MUT(MUT)) u_stk
      (.clk(ck_stk[t]),.rst_n(rst_n),.kp_i(kp_t[32*t +:32]),.kpv_i(kpv_t[t]),.gf_i(gf_t[t]),
       .kp_o(kp_k[32*t +:32]),.kpv_o(kpv_k[t]),.gf_o(gf_k[t]));
    wire [63:0] nb_mid;
    ot_qkh_head_nb_native #(.MUT(MUT)) u_nb1
      (.clk(ck_nb1[t]),.nb_i(nb_t[64*t +:64]),.nb_o(nb_mid));
    ot_qkh_head_nb_native u_nb2
      (.clk(ck_nb2[t]),.nb_i(nb_mid),.nb_o(nb_d[64*t +:64]));
    ot_qkh_lane8 u_l8 (.clk(ck_lane[t]),.rst_n(lane_rst_n[t]),
      .c_in({cr_o[15:13],dr_o[216]}),.row_in(dr_o[215:152]),.e_in(dr_o[151:136]),.lt_in(cr_o[12:1]),
      .hid(dr_o[1:0]),.bsel(2'(t/4)),.q_valid_in(cr_o[0]),.q_beat_in(dr_o[135:130]),.q_data_in(dr_o[129:2]),
      .kp(kp_t[32*t +:32]),.kpv(kpv_t[t]),.nb(nb_t[64*t +:64]),.gf(gf_t[t]));
  end endgenerate
  wire [31:0] sc_k;wire sf_k,gf_kt,kt_rst_n;
  ot_qkh_ktree u_kt (.clk(ck_kt),.rst_n(kt_rst_n),.kp_in(kp_k),.kpv_in(kpv_k[0]),.gf_in(gf_k),
    .sc_d(sc_k),.sc_f(sf_k),.g_f(gf_kt));
  ot_qkh_head_score4_native #(.MUT(MUT)) u_score
    (.clk(ck_score),.rst_n(rst_n),.sc_i(sc_k),.sf_i(sf_k),.gf_i(gf_kt),.pack_fault(pack_fault),
     .sc_o(sc_d),.sf_o(sc_f),.gf_o(g_f),.kt_rst_n(kt_rst_n));
endmodule
