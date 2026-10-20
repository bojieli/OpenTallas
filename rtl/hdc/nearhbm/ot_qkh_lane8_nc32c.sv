`timescale 1ns/1ps
// Default-off same-cycle regional control successor, arithmetic still NC and not yet SAFE32.
module ot_qkh_lane8_nc32c #(
    parameter integer ADD_LAT = 7,
    parameter integer LTW = 12
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      c_in,          // {k issue, v issue of a real row, first round, g}
    input  wire [63:0]     row_in,        // row bytes of lanes 8t .. 8t + 7
    input  wire [15:0]     e_in,
    input  wire [LTW-1:0]  lt_in,
    input  wire [1:0]      hid,           // head strap (0..3)
    input  wire [1:0]      bsel,          // beat column strap: t / 4 (lanes 8t .. are bits 128 (t % 4) .. of beat t / 4)
    input  wire            q_valid_in,
    input  wire [5:0]      q_beat_in,
    input  wire [127:0]    q_data_in,     // bits 128 (t % 4) .. + 127 of the q beat
    output reg  [31:0]     kp,            // the level-3 K node of products 8t .. 8t + 7
    output reg             kpv,
    output reg  [63:0]     nb,            // node-slice words 2t, 2t + 1
    output reg             gf             // lane / bank faults, ORed
);
    localparam integer PLAT = 4;
    generate if(ADD_LAT!=7 || LTW!=12)begin:bad_shape ot_qkh_lane8_nc32c_requires7_12 trap();end endgenerate
    // ---- reset relay: the port drives only the relay; control flops reset from its outputs ---------------------------
    // idle1012 textbook class 2: one reset copy per lane (the shared lane copy drove 952 flops) + one for the tile control
    wire [447:0] r32;
    ot_rst_relay_bounded32 #(.REGIONS(224)) rst_a(.clk(clk),.rst_n_in(rst_n),.rst_n(r32[223:0]));
    ot_rst_relay_bounded32 #(.REGIONS(224)) rst_b(.clk(clk),.rst_n_in(rst_n),.rst_n(r32[447:224]));
    wire [8:0] rr=r32[8:0];
    wire rc = rr[8];          // tile control / pins
    // ---- S3: the pin flops ---------------------------------------------------------------------------------------------
    reg  [3:1]      c3;
    reg  [63:0]     row3;
    reg  [15:0]     e3;
    reg  [LTW-1:0]  lt3;
    reg  [127:0]    qd3;
    always @(posedge clk or negedge rc)
        if (!rc) begin c3[3:1] <= 3'd0; lt3 <= {LTW{1'b0}}; end
        else begin c3[3:1] <= c_in[3:1]; lt3 <= lt_in; end
    always @(posedge clk) begin
        row3 <= row_in; e3 <= e_in; qd3 <= q_data_in;
    end
    // q rows of heads hid (q0) and 4 + hid (q1): beat 4 hid + t / 4, resp. 4 (4 + hid) + t / 4 (HD 128: 4 beats a row)
    reg [127:0] q0,q1;
    (* keep="true",dont_touch="true" *) reg [7:0] gg,gk_d,gk_v,qvc;
    (* keep="true",dont_touch="true" *) reg [5:0] qbc[0:7];
    (* keep="true",dont_touch="true" *) reg [1:0] hdc[0:7],bsc[0:7];
    genvar ci,d;
    generate for(ci=0;ci<8;ci=ci+1)begin:qcap
      always @(posedge clk)begin gg[ci]<=c_in[0];qbc[ci]<=q_beat_in;hdc[ci]<=hid;bsc[ci]<=bsel;end
      always @(posedge clk or negedge r32[9])if(!r32[9])begin gk_d[ci]<=0;gk_v[ci]<=0;qvc[ci]<=0;end
       else begin gk_d[ci]<=c_in[3];gk_v[ci]<=c_in[3];qvc[ci]<=q_valid_in;end
      wire w0=qvc[ci] && (qbc[ci]=={2'b00,hdc[ci],bsc[ci]});
      wire w1=qvc[ci] && (qbc[ci]=={2'b01,hdc[ci],bsc[ci]});
      always @(posedge clk)begin if(w0)q0[16*ci+:16]<=qd3[16*ci+:16];if(w1)q1[16*ci+:16]<=qd3[16*ci+:16];end
    end endgenerate
    // ---- the control delay lines (one copy for 8 lanes) ----------------------------------------------------------------
    wire [168*12-1:0] ltc;
    wire [64*3-1:0] ctc;
    wire [15:0] k1c,k2c,k3c;
    ot_qkh_ctl_tree4_leaf #(.W(12),.DEST(168)) lt_tree(.clk(clk),.rr(r32[114:10]),.d(lt3),.q(ltc));
    ot_qkh_ctl_tree4_leaf #(.W(3),.DEST(64)) ct_tree(.clk(clk),.rr(r32[167:115]),.d(c3[3:1]),.q(ctc));
    ot_qkh_valid_delay16 #(.D(ADD_LAT)) kl1(.clk(clk),.rr(r32[223:168]),.d(ctc[63*3+2]),.q(k1c));
    ot_qkh_valid_delay16 #(.D(ADD_LAT)) kl2(.clk(clk),.rr(r32[279:224]),.d(k1c[15]),.q(k2c));
    ot_qkh_valid_delay16 #(.D(ADD_LAT)) kl3(.clk(clk),.rr(r32[335:280]),.d(k2c[15]),.q(k3c));
    wire g3v=c3[2];
    // ---- the lanes -------------------------------------------------------------------------------------------------------
    wire [8*32-1:0] p_y, l_y, fb, obw;
    wire [7:0]      p_vo, p_f, l_vo, l_f, b_f;
    generate for (d = 0; d < 8; d = d + 1) begin : g_d
        wire rl = rr[d];      // this lane's reset copy
        // tree role: 0 2 4 6 level 1 (own pair); 1: level 2 (0, 2); 5: level 2 (4, 6); 3: level 3 (1, 5); 7: none
        localparam integer TL = (d % 2 == 0) ? 1 : ((d == 1 || d == 5) ? 2 : ((d == 3) ? 3 : 0));
        localparam integer LA = (d == 3) ? 1 : d - 1;
        localparam integer LB = (d == 3) ? 5 : d + 1;
        wire [15:0] qv = gg[d] ? q1[d * 16 +: 16] : q0[d * 16 +: 16];
        (* keep_hierarchy *) ot_qwen_nearhbm_prod_ncr u_p (.clk(clk), .rst_n(r32[336+2*d]), .rst_y(r32[337+2*d]), .valid_in(gk_v[d] || g3v),
            .a(gk_d[d] ? qv : e3), .k(row3[8*d +: 8]), .y(p_y[32*d +: 32]), .fault(p_f[d]), .valid_out(p_vo[d]));
        wire [31:0] la,lb;
        wire ktv=(TL==1)?ctc[(8*d+7)*3+2]:((TL==2)?k1c[12+(d==5)]:((TL==3)?k2c[12]:1'b0));
        wire vdv=ctc[(8*d+7)*3+1];
        for(genvar bc=0;bc<4;bc=bc+1)begin:op_chunk
          wire cz=ctc[(8*d+4+bc/2)*3];
          wire vd=ctc[(8*d+6+bc/2)*3+1];
          wire kt=(TL==1)?ctc[(8*d+bc)*3+2]:((TL==2)?k1c[4*(d==5)+bc]:((TL==3)?k2c[bc]:1'b0));
          wire [7:0] va=cz?8'd0:fb[32*d+8*bc+:8];
          wire [7:0] vb=vd?p_y[32*d+8*bc+:8]:8'd0;
          if(TL==1)begin
           assign la[8*bc+:8]=kt?p_y[32*d+8*bc+:8]:va;
           assign lb[8*bc+:8]=kt?p_y[32*(d+1)+8*bc+:8]:vb;
          end else if(TL>=2)begin
           assign la[8*bc+:8]=kt?l_y[32*LA+8*bc+:8]:va;
           assign lb[8*bc+:8]=kt?l_y[32*LB+8*bc+:8]:vb;
          end else begin assign la[8*bc+:8]=va;assign lb[8*bc+:8]=vb;end
        end
        wire [1:0] err;
        (* keep_hierarchy *) ot_hdc_fp32_add_lat_ncr #(.LAT(ADD_LAT)) u_a (.clk(clk), .rst_n(r32[352+2*d]), .rst_y(r32[353+2*d]), .valid_in(ktv || vdv),
            .a(la), .b(lb), .y(l_y[32*d +: 32]), .err(err), .valid_out(l_vo[d]));
        assign l_f[d] = l_vo[d] && (err != 2'd0);
        // NC: lane 3's 1-deep pad register and the kp output register capture the same l_y word on the same edge
        // (ADD_LAT 7); lane 3's feedback is read from kp, so the RTL holds ONE register (the routed one)
        if (d == 3 && ADD_LAT == 7) begin : g_fbkp
`ifdef KVP3_MUT3
            assign fb[32*d +: 32] = l_y[32*d +: 32];   // bench mutant 3 (must FAIL): feedback one edge early
`else
            assign fb[32*d +: 32] = kp;
`endif
        end else begin : g_pad
            ot_hdc_delay #(.W(32), .D(8 - ADD_LAT)) u_pad (.clk(clk), .rst_n(rl), .d(l_y[32*d +: 32]), .q(fb[32*d +: 32]));
        end
        // the local P.V tree (levels 1-3) of this lane, executing the decision word delayed PLAT
        wire lis=ltc[(20*d)*12];
        reg [31:0] lp0,lp1,lp2,obr;
        wire [31:0] ly,lpa,bpa;
        for(genvar bc=0;bc<4;bc=bc+1)begin:pv_mux
          wire [11:0] dc=ltc[(20*d+bc)*12+:12];
          assign lpa[8*bc+:8]=(dc[3:2]==0)?lp0[8*bc+:8]:((dc[3:2]==1)?lp1[8*bc+:8]:lp2[8*bc+:8]);
          assign bpa[8*bc+:8]=dc[1]?ly[8*bc+:8]:fb[32*d+8*bc+:8];
        end
        wire [1:0]  berr;
        wire        bvo;
        (* keep_hierarchy *) ot_hdc_fp32_add_lat_ncr #(.LAT(ADD_LAT)) u_b (.clk(clk), .rst_n(r32[368+2*d]), .rst_y(r32[369+2*d]), .valid_in(lis),
            .a(lpa), .b(bpa), .y(ly), .err(berr), .valid_out(bvo));
        assign b_f[d] = bvo && (berr != 2'd0);
        for(genvar bc=0;bc<4;bc=bc+1)begin:pv_write
          wire [11:0] a0=ltc[(20*d+4+bc)*12+:12],a1=ltc[(20*d+8+bc)*12+:12],a2=ltc[(20*d+12+bc)*12+:12],ao=ltc[(20*d+16+bc)*12+:12];
          always @(posedge clk)begin
           if(a0[4])lp0[8*bc+:8]<=fb[32*d+8*bc+:8];
           if(a0[5] && a0[7:6]==0)lp0[8*bc+:8]<=ly[8*bc+:8];
           if(a1[5] && a1[7:6]==1)lp1[8*bc+:8]<=ly[8*bc+:8];
           if(a2[5] && a2[7:6]==2)lp2[8*bc+:8]<=ly[8*bc+:8];
           if(ao[8])obr[8*bc+:8]<=ly[8*bc+:8];
          end
        end
        assign obw[32*d +: 32] = obr;
    end endgenerate
    // ---- registered outputs ----------------------------------------------------------------------------------------------
    // node slice (LFB 4): word k of this tile = lane 4k + beat
    generate for(ci=0;ci<8;ci=ci+1)begin:nb_chunk
      wire [11:0] dc=ltc[(160+ci)*12+:12];
      always @(posedge clk)if(dc[9])nb[8*ci+:8]<=obw[32*((ci<4?0:4)+dc[11:10])+8*(ci%4)+:8];
    end endgenerate
    wire k3v=k3c[0];
    always @(posedge clk) kp <= l_y[32*3 +: 32];
    always @(posedge clk or negedge rc)
        if (!rc) begin kpv <= 1'b0; gf <= 1'b0; end
        else begin kpv <= k3v; gf <= (|(p_f & p_vo)) || (|l_f) || (|b_f); end
endmodule

module ot_qkh_ctl_tree4_leaf #(parameter integer W=12,DEST=100,MUT=0)(
 input wire clk,input wire [(21+(DEST+1)/2)-1:0] rr,input wire [W-1:0] d,output wire [DEST*W-1:0] q);
 (* keep="true",dont_touch="true" *) reg [W-1:0] s1[0:1];
 (* keep="true",dont_touch="true" *) reg [W-1:0] s2[0:7];
 (* keep="true",dont_touch="true" *) reg [W-1:0] s3[0:31];
 (* keep="true",dont_touch="true" *) reg [W-1:0] s4[0:DEST-1];
 genvar g;
 generate
 if(W<1 || W>16 || DEST<1 || DEST>256)begin:bad ot_qkh_ctl_tree4_bad_shape trap();end
 for(g=0;g<2;g=g+1)begin:a
  always @(posedge clk or negedge rr[0])if(!rr[0])s1[g]<={W{1'b0}};else s1[g]<=d;
 end
 for(g=0;g<8;g=g+1)begin:b
  always @(posedge clk or negedge rr[1+g/2])if(!rr[1+g/2])s2[g]<={W{1'b0}};else s2[g]<=s1[g/4];
 end
 for(g=0;g<32;g=g+1)begin:c
  always @(posedge clk or negedge rr[5+g/2])if(!rr[5+g/2])s3[g]<={W{1'b0}};else s3[g]<=s2[g/4];
 end
 for(g=0;g<DEST;g=g+1)begin:e
  always @(posedge clk or negedge rr[21+g/2])if(!rr[21+g/2])s4[g]<={W{1'b0}};else s4[g]<=s3[g%32];
  assign q[g*W+:W]=(MUT==1)?s3[g%32]:((MUT==2 && g==0)?(s4[g]^{{(W-1){1'b0}},1'b1}):s4[g]);
 end
 endgenerate
endmodule

module ot_qkh_valid_delay16 #(parameter integer D=7)(input wire clk,input wire [D*8-1:0] rr,input wire d,output wire [15:0] q);
 (* keep="true",dont_touch="true" *) reg [15:0] st[0:D-1];
 genvar t,b;
 generate for(t=0;t<D;t=t+1)begin:stage
  for(b=0;b<16;b=b+1)begin:copy
   always @(posedge clk or negedge rr[t*8+b/2])if(!rr[t*8+b/2])st[t][b]<=1'b0;
   else if(t==0)st[t][b]<=d;else st[t][b]<=st[t-1][b];
  end
 end endgenerate
 assign q=st[D-1];
endmodule
