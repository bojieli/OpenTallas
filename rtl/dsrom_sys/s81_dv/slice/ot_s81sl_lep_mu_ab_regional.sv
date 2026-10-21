`timescale 1ns/1ps
`default_nettype none
// S81-LEPAB regional successor. Three explicit same-frequency roots; every
// C<->A/B bus is a fixed D4/K2 landing, not an asynchronous FIFO. New master:
// never bind a legacy lep_mu_ab view onto this module. See committed MODEL.json.
module ot_s81sl_lep_mu_ab_regional #(
    parameter integer DT = 512, parameter integer DR = 12, parameter integer CRED = 12, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 1, parameter integer IN_PIPE = 1, parameter integer NATIVE32 = 1
) (
    input  wire            clk,
    input  wire            clk_a,
    input  wire            clk_b,
    input  wire            rst_n,
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

    wire [2:0] reset_c;
    ot_rst_relay_tree3 #(.REGIONS(3)) u_rc(.clk(clk),.rst_n_in(rst_n),.rst_n(reset_c));
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
      ot_s81sl_lepab_cross #(.W(1138)) u_to_pair(.cs(clk),.cd(pair_clk[p]),.rst_n(rst_n),.i({tx_mc,tx_ro}),.o(cmd));
      wire [1103:0] out_ri,out_wd;
      wire [31:0] out_rt;
      wire out_wv,out_fault;
      wire [1:0] pair_rxv;
      wire [2:0] rf;
      ot_rst_relay_tree3 #(.REGIONS(3)) u_relay_reset(.clk(pair_clk[p]),.rst_n_in(rst_n),.rst_n(rf));
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
        .clk(pair_clk[p]),.rst_n(rst_n),.ro(cmd[1103:0]),.mu_c(cmd[1137:1104]),
        .ri(out_ri),.mu_rt(out_rt),.ml_wv(out_wv),.ml_wd(out_wd),
        .ml_rv(1'b0),.ml_rd(1104'd0),.ml_f(1'b0),.sl_f(1'b0),
        .lo0_v(local_lv[2*p]),.lo0_r(local_lr[2*p]),.lo0_d(local_ld[1106*p+:553]),
        .lo1_v(local_lv[2*p+1]),.lo1_r(local_lr[2*p+1]),.lo1_d(local_ld[1106*p+553+:553]),
        .li0_v(local_iv[2*p]),.li0_r(local_ir[2*p]),.li0_d(local_id[1106*p+:553]),
        .li1_v(local_iv[2*p+1]),.li1_r(local_ir[2*p+1]),.li1_d(local_id[1106*p+553+:553]),
        .rxv(pair_rxv),.l0_f(lane_fault[6*p+:3]),.l1_f(lane_fault[6*p+3+:3]),.fault(out_fault));
      if(p==0) begin:g_a assign rxv=pair_rxv;end
      else begin:g_b assign rxvb=pair_rxv;end
      ot_s81sl_lepab_cross #(.W(2242)) u_from_pair(.cs(pair_clk[p]),.cd(clk),.rst_n(rst_n),
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
    wire replay_tag=ml_rd[0] && (ml_rd[3:1]==1 || ml_rd[3:1]==2) && ml_rd[1045];
    assign replay_stripped={ml_rd[1103:1078],(replay_tag?33'd0:ml_rd[1077:1045]),ml_rd[1044:0]};
    wire [31:0] replay_rt=replay_tag?{1'b1,ml_rd[1047+:10],ml_rd[1057+:21]}:32'd0;
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

// Two physical forwarded edges; only the high valid bit is reset. Credit W1
// uses that same high bit. Data reset is deliberately omitted.
module ot_s81sl_lepab_relay2 #(parameter integer W=554)(
 input wire clk,rn,input wire [W-1:0] i,output wire [W-1:0] o);
 (* keep *) reg [W-1:0] first,last;
 always @(posedge clk or negedge rn) if(!rn) begin first[W-1]<=0;last[W-1]<=0;end
 else begin first[W-1]<=i[W-1];last[W-1]<=first[W-1];end
 generate if(W>1) begin:g_data
   always @(posedge clk) begin first[W-2:0]<=i[W-2:0];last[W-2:0]<=first[W-2:0];end
 end endgenerate
 assign o=last;
endmodule

// Reset-equal n32 writer + bounded reader per12 bits. The reset forest gives
// each local chunk a private leaf: the source reset never drives a W-bit bank.
module ot_s81sl_lepab_cross #(parameter integer W=1138,CB=12,N=(W+CB-1)/CB)(
 input wire cs,cd,rst_n,input wire [W-1:0] i,output wire [W-1:0] o);
 wire [N-1:0] rs,rd;
 ot_pl_land_reset_forest #(.DEPTH(7),.LEAVES(N)) u_rs(.ck(cs),.d(rst_n),.q(rs));
 ot_pl_land_reset_forest #(.DEPTH(7),.LEAVES(N)) u_rd(.ck(cd),.d(rst_n),.q(rd));
 for(genvar c=0;c<N;c=c+1) begin:g_chunk
   localparam integer CW=(W-c*CB<CB)?W-c*CB:CB;
   wire [4*CW-1:0] bank;
   wire [11:0] epoch;
   wire [3:0] valid;
   (* keep_hierarchy="yes" *) ot_pl_land_n32_local_w #(.W(CW),.D(4),.GB(12)) u_w(
     .ck(cs),.rsi(rs[c]),.i(i[c*CB+:CW]),.bank(bank),.epo(epoch),.vld(valid));
   (* keep_hierarchy="yes" *) ot_pl_land_local_r #(.W(CW),.D(4),.K(2)) u_r(
     .ck(cd),.rsi(rd[c]),.bank(bank),.epo(epoch),.vld(valid),.o(o[c*CB+:CW]));
 end
endmodule

(* keep_hierarchy="yes" *)
module ot_s81sl_lepab_select(input wire [4:0] i,input wire active,output wire [4:0] o);
 assign o={i[4] && !i[3],i[3],i[2] && !i[0] && !i[1],i[1] && !i[0],i[0]} & {5{active}};
endmodule

module ot_s81sl_lepab_merge(input wire clk,rn,input wire [4:0] sel,
 input wire [2239:0] a,b,m,output wire [2239:0] o,output wire [4:0] valid);
 localparam integer N=140,NG=(N+7)/8;
 wire [NG*5-1:0] decoded;
 wire [N+NG-1:0] rr;
 ot_rst_relay_tree3 #(.REGIONS(N+NG)) u_rr(.clk(clk),.rst_n_in(rn),.rst_n(rr));
 for(genvar g=0;g<NG;g=g+1) begin:g_decode
   (* keep=1 *) ot_s81sl_lepab_select u_dec(.i(sel),.active(rr[N+g]),.o(decoded[5*g+:5]));
 end
 for(genvar c=0;c<N;c=c+1) begin:g_chunk
   localparam integer LO=16*c;
   (* keep *) reg [4:0] s;
   reg [15:0] da,db,dm,qo;
   always @(posedge clk or negedge rr[c]) if(!rr[c]) s<=0;else s<=decoded[5*(c/8)+:5];
   always @(posedge clk) begin
     da<=a[LO+:16];db<=b[LO+:16];dm<=m[LO+:16];
     if(LO<1136) qo<=({16{s[0]}}&da)|({16{s[1]}}&db)|({16{s[2]}}&dm);
     else qo<=({16{s[3]}}&da)|({16{s[4]}}&db);
   end
   assign o[LO+:16]=qo;
 end
 reg [4:0] v1,v2;
 always @(posedge clk or negedge rr[0]) if(!rr[0]) begin v1<=0;v2<=0;end
 else begin v1<={sel[4] && !sel[3],sel[3],sel[2] && !sel[0] && !sel[1],sel[1] && !sel[0],sel[0]};v2<=v1;end
 assign valid=v2;
endmodule
`default_nettype wire
