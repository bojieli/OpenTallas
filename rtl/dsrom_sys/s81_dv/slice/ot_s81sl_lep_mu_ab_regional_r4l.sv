`timescale 1ns/1ps
`default_nettype none
// R2 actual gate requires raw reset entrance landing on every root.
// Successor adds2same-root reset-release stages C/A/B before existing forests;
// traffic register paths and credit/RTT edges are unchanged. Oldr3r is preserved.
module ot_s81sl_lep_mu_ab_regional_r4l #(
    parameter integer DT = 512, parameter integer DR = 12, parameter integer CRED = 12, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 1, parameter integer IN_PIPE = 1, parameter integer NATIVE32 = 1
) (
    input  wire            clk,
    input  wire            clk_a,
    input  wire            clk_b,
    input  wire            rst_n,
    input  wire            rst_n_a,
    input  wire            rst_n_b,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault
);

    // Each external reset reaches one entrance flop. Cascade assertion and
    // same-root two-edge release precede all existing equal-depth forests.
    // Reset startup only: +2 rising edges C/A/B; traffic register ages unchanged.
    wire [2:0] entrance_clk={clk_b,clk_a,clk};
    wire [2:0] entrance_rst={rst_n_b,rst_n_a,rst_n};
    wire [2:0] landed;
    for(genvar rr=0;rr<3;rr=rr+1) begin:g_entrance
      (* keep="true",dont_touch="true",async_reg="true" *) reg first_q,second_q;
      always @(posedge entrance_clk[rr] or negedge entrance_rst[rr])
        if(!entrance_rst[rr]) first_q<=1'b0; else first_q<=1'b1;
      always @(posedge entrance_clk[rr] or negedge first_q)
        if(!first_q) second_q<=1'b0; else second_q<=1'b1;
      assign landed[rr]=second_q;
    end
    wire land_rst_n=landed[0],land_rst_n_a=landed[1],land_rst_n_b=landed[2];
    wire [2:0] reset_c;
    ot_rst_relay_tree3 #(.REGIONS(3)) u_rc(.clk(clk),.rst_n_in(land_rst_n),.rst_n(reset_c));
    localparam integer NW=$clog2(NB+1);
    reg [NW-1:0] remain;
    reg pair_b, dispatch_fault;
    wire bad_copy=mu_c[0] && mu_c[1] && mu_c[12:3]==0;
    `ifdef OT_S81SL_LEP_MUT_WRONGCOPY
    wire selected_b=1'b0; // causal mutant: centre drops the static copy-B route
`else
    wire selected_b=pair_b && remain!=0;
`endif
    always @(posedge clk or negedge reset_c[0]) begin
      if(!reset_c[0]) begin remain<=0;pair_b<=0;dispatch_fault<=0;end
      else begin
        if(mu_c[0]) begin
          remain<=NW'(NB);pair_b<=mu_c[1] && mu_c[12:3]!=0;
          if(bad_copy || (remain!=0 && !(ro[0] && remain==1))) dispatch_fault<=1;
        end else if(ro[0] && remain!=0) remain<=remain-1'b1;
      end
    end
    wire [1:0] pair_clk={clk_b,clk_a};
    wire [1:0] pair_rst={land_rst_n_b,land_rst_n_a};
    wire [4483:0] arrived;
    wire [1:0] pair_fault;
    wire [3:0] local_lv, local_lr, local_iv, local_ir;
    wire [2211:0] local_ld,local_id;
    wire [3:0] external_lr={lo3_r,lo2_r,lo1_r,lo0_r};
    wire [3:0] external_iv={li3_v,li2_v,li1_v,li0_v};
    wire [2211:0] external_id={li3_d,li2_d,li1_d,li0_d};
    wire [3:0] external_lv,external_ir;
    wire [2211:0] external_ld;
    wire [11:0] lane_fault={l3_f,l2_f,l1_f,l0_f};
    for(genvar p=0;p<2;p=p+1) begin:g_pair
      reg [1103:0] tx_ro;
      reg [33:0] tx_mc;
      wire mine=(p==1)?selected_b:!selected_b;
      wire command_mine=(p==1)?(mu_c[1] && mu_c[12:3]!=0):!(mu_c[1] && mu_c[12:3]!=0);
      always @(posedge clk) begin
        tx_ro<={ro[1103:1],ro[0] && mine};
        tx_mc<={mu_c[33:2],1'b0,mu_c[0] && command_mine};
      end
      wire [1137:0] cmd;
      ot_s81sl_lepab_cross_r3r #(.W(1138)) u_to_pair(.cs(clk),.cd(pair_clk[p]),.rst_n_src(land_rst_n),.rst_n_dst(pair_rst[p]),.i({tx_mc,tx_ro}),.o(cmd));
      wire [1103:0] out_ri,out_wd;
      wire [31:0] out_rt;
      wire out_wv,out_fault;
      wire [1:0] pair_rxv;
      wire [2:0] rf;
      ot_rst_relay_tree3 #(.REGIONS(3)) u_relay_reset(.clk(pair_clk[p]),.rst_n_in(pair_rst[p]),.rst_n(rf));
      for(genvar l=0;l<2;l=l+1) begin:g_lane
        localparam integer L=2*p+l;
        ot_s81sl_lepab_relay2 #(.W(554)) u_lo(.clk(pair_clk[p]),.rn(rf[l]),
          .i({local_lv[L],local_ld[553*L+:553]}),.o({external_lv[L],external_ld[553*L+:553]}));
        ot_s81sl_lepab_relay2 #(.W(1)) u_locr(.clk(pair_clk[p]),.rn(rf[l]),.i(external_lr[L]),.o(local_lr[L]));
        ot_s81sl_lepab_relay2 #(.W(554)) u_li(.clk(pair_clk[p]),.rn(rf[l]),
          .i({external_iv[L],external_id[553*L+:553]}),.o({local_iv[L],local_id[553*L+:553]}));
        ot_s81sl_lepab_relay2 #(.W(1)) u_licr(.clk(pair_clk[p]),.rn(rf[l]),.i(local_ir[L]),.o(external_ir[L]));
      end
      ot_s81sl_lep_mu_a #(.DT(DT),.DR(DR),.CRED(CRED),.SRAM(SRAM),.NB(NB),
        .RX_SRAM(RX_SRAM),.IN_PIPE(IN_PIPE),.NATIVE32(NATIVE32)) u_core(
        .clk(pair_clk[p]),.rst_n(pair_rst[p]),.ro(cmd[1103:0]),.mu_c(cmd[1137:1104]),
        .ri(out_ri),.mu_rt(out_rt),.ml_wv(out_wv),.ml_wd(out_wd),
        .ml_rv(1'b0),.ml_rd(1104'd0),.ml_f(1'b0),.sl_f(1'b0),
        .lo0_v(local_lv[2*p]),.lo0_r(local_lr[2*p]),.lo0_d(local_ld[1106*p+:553]),
        .lo1_v(local_lv[2*p+1]),.lo1_r(local_lr[2*p+1]),.lo1_d(local_ld[1106*p+553+:553]),
        .li0_v(local_iv[2*p]),.li0_r(local_ir[2*p]),.li0_d(local_id[1106*p+:553]),
        .li1_v(local_iv[2*p+1]),.li1_r(local_ir[2*p+1]),.li1_d(local_id[1106*p+553+:553]),
        .rxv(pair_rxv),.l0_f(lane_fault[6*p+:3]),.l1_f(lane_fault[6*p+3+:3]),.fault(out_fault));
      if(p==0) begin:g_a assign rxv=pair_rxv;end
      else begin:g_b assign rxvb=pair_rxv;end
      ot_s81sl_lepab_cross_r3r #(.W(2242)) u_from_pair(.cs(pair_clk[p]),.cd(clk),.rst_n_src(pair_rst[p]),.rst_n_dst(land_rst_n),
        .i({out_fault,out_wv,out_wd,out_rt,out_ri}),.o(arrived[2242*p+:2242]));
      assign pair_fault[p]=arrived[2242*p+2241];
    end
    assign {lo3_v,lo2_v,lo1_v,lo0_v}=external_lv;
    assign {lo3_d,lo2_d,lo1_d,lo0_d}=external_ld;
    assign {li3_r,li2_r,li1_r,li0_r}=external_ir;
    wire [1103:0] a_ri=arrived[0+:1104],b_ri=arrived[2242+:1104];
    wire [31:0] a_rt=arrived[1104+:32],b_rt=arrived[2242+1104+:32];
    wire [1103:0] a_wd=arrived[1136+:1104],b_wd=arrived[2242+1136+:1104];
    wire a_wv=arrived[2240],b_wv=arrived[2242+2240];
    wire [4:0] select_in={b_wv,a_wv,ml_rv,b_ri[0],a_ri[0]};
    wire [2239:0] data_a={a_wd,a_rt,a_ri},data_b={b_wd,b_rt,b_ri};
    wire [1103:0] replay_stripped;
    assign replay_stripped[1044:0]=ml_rd[1044:0];
    assign replay_stripped[1103:1078]=ml_rd[1103:1078];
    for(genvar tc=0;tc<3;tc=tc+1) begin:g_replay_strip
      localparam integer W=(33-12*tc<12)?33-12*tc:12;
      (* keep=1 *) ot_s81sl_lepab_replay_slice #(.W(W),.STRIP(1)) u_strip(
        .code({ml_rd[1045],ml_rd[3:0]}),.i(ml_rd[1045+12*tc+:W]),.o(replay_stripped[1045+12*tc+:W]));
    end
    wire [31:0] replay_rt,replay_identity={1'b1,ml_rd[1047+:10],ml_rd[1057+:21]};
    for(genvar tc=0;tc<4;tc=tc+1) begin:g_replay_identity
      (* keep=1 *) ot_s81sl_lepab_replay_slice #(.W(8),.STRIP(0)) u_identity(
        .code({ml_rd[1045],ml_rd[3:0]}),.i(replay_identity[tc*8+:8]),.o(replay_rt[tc*8+:8]));
    end
    wire [2239:0] data_m={1104'd0,replay_rt,replay_stripped};
    wire [2239:0] merged;
    wire [4:0] valid_out;
    ot_s81sl_lepab_merge u_merge(.clk(clk),.rn(reset_c[1]),.sel(select_in),
      .a(data_a),.b(data_b),.m(data_m),.o(merged),.valid(valid_out));
    assign ri={merged[1103:1],|valid_out[2:0]};
    assign mu_rt=merged[1104+:32];
    assign ml_wd=merged[1136+:1104];
    assign ml_wv=|valid_out[4:3];
    reg error;
    always @(posedge clk or negedge reset_c[2]) begin
      if(!reset_c[2]) error<=0;
      else if(dispatch_fault || |pair_fault || sl_f || ml_f ||
        (a_ri[0] && b_ri[0]) || (a_wv && b_wv) ||
        (ml_rv && (a_ri[0] || b_ri[0]))) error<=1;
    end
    assign fault=error;
`ifndef SYNTHESIS
    initial if(DR!=12 || CRED!=12 || RX_SRAM!=1 || NATIVE32!=1 || IN_PIPE!=1)
      $fatal(1,"LEPAB_REGION_REQUIRES_MATCHED_CRED12_NATIVE32");
`endif
endmodule
`default_nettype wire
