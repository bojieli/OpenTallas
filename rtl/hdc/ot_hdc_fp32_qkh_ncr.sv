`timescale 1ns/1ps
// Default-off split-reset NC kernels. rst_y and rst_n must have identical phase/contract.
// 32 output-data reset pins separated from <=25 control reset pins; arithmetic and ages unchanged.
module ot_hdc_fp32_add_lat_ncr #(
    parameter integer LAT = 7,      // only LAT 7 (cuts A, B, C, D + HSPLIT) exists in this variant
    // YCOPY = 1..2 (KV-PARAMS4 K-tree root): y2[32 c +: 32] are kept extra output registers (same D, same edge, own reset
    // leaf rst_y2[c]) so a wide consumer cone can be split over several drivers; YCOPY = 0: y2 = {y, y}, rst_y2 unused
    parameter integer YCOPY = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input wire rst_y,
    input wire [1:0] rst_y2,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output wire [63:0] y2,
    output reg  [1:0]  err,
    output reg         valid_out
);
    generate if (LAT != 7) begin : g_bad_lat
        ot_hdc_fp32_add_lat_ncr_needs_LAT_7 u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;

    wire cmp_c;
    wire [30:0] cmp_s;
    ot_hdc_ksadd_k #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 cut (u_ca): the valid bit is the one reset flop, the rest plain data flops
    reg         x_v;
    reg         x_byp, x_nf, x_sub, x_as, x_bs;
    (* keep="true", dont_touch="true" *) reg [6:0] x_swap;
    (* keep="true",dont_touch="true" *) reg [27:0] x_dab_oh,x_dba_oh;
    (* keep="true",dont_touch="true" *) reg x_dab_big,x_dba_big;
    reg [31:0] x_code_a,x_code_b;
    // R8: two kept copies per 8-bit bypass bank (one per 4-bit half) -> each copy feeds 4 bits x 4 ring slots (R7 census: 33 loads)
    (* keep="true",dont_touch="true" *) reg [7:0] x_az_dist,x_bz_dist,x_nf_dist;
    reg  [7:0]  x_aexp, x_bexp;
    reg  [23:0] x_aman, x_bman;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) x_v <= 1'b0;
        else x_v <= valid_in;
    always @(posedge clk) begin
        x_swap <= {7{!cmp_c}}; x_byp <= bypass; x_nf <= nonfinite; x_code_a<=a;x_code_b<=b;
        x_az_dist<={8{a_zero}};x_bz_dist<={8{b_zero}};x_nf_dist<={8{nonfinite}};
        x_sub <= a[31] ^ b[31]; x_as <= a[31]; x_bs <= b[31];
        x_aexp <= a_exp; x_bexp <= b_exp; x_aman <= a_man; x_bman <= b_man; x_dab_big<=(dab>=28);x_dba_big<=(dba>=28);
    end
    // ---- A2 ----------------------------------------------------------------------------------------
    genvar j;
    generate for(j=0;j<28;j=j+1)begin:jam_capture
      always @(posedge clk)begin x_dab_oh[j]<=(dab==j);x_dba_oh[j]<=(dba==j);end
    end endgenerate
    function automatic [27:0] jam28oh;
      input [23:0] man;input [27:0] oh;input big;
      reg [27:0] val,acc;integer i;
      begin
        val={1'b0,man,3'b000};acc={27'd0,big && (|val)};
        for(i=0;i<28;i=i+1)acc=acc|({28{oh[i]}} & ((val>>i)|{27'd0,|(val & ((28'd1<<i)-1))}));
        jam28oh=acc;
      end
    endfunction
    wire [27:0] small_a=jam28oh(x_aman,x_dba_oh,x_dba_big);
    wire [27:0] small_b=jam28oh(x_bman,x_dab_oh,x_dab_big);

    reg        s1_v, s1_byp, s1_sub, s1_sign, s1_nf;
    wire [31:0] bypass_stage2;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [26:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    wire [27:0] small_s;
    genvar k;
    generate for(k=0;k<4;k=k+1)begin:small_select
      assign small_s[7*k+:7]=x_swap[k]?small_a[7*k+:7]:small_b[7*k+:7];
    end endgenerate
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_nf <= x_nf;




        s1_sub <= x_sub;
        s1_sign <= x_swap[4] ? x_bs : x_as;
        s1_exp <= x_swap[4] ? x_bexp : x_aexp;
        s1_big[11:0] <= x_swap[5] ? x_bman[11:0] : x_aman[11:0];
        s1_big[23:12] <= x_swap[6] ? x_bman[23:12] : x_aman[23:12];
`ifdef KVP3_MUT4
        s1_small <= {1'b0, small_s[25:0]};             // bench mutant 4 (must FAIL): a live bit dropped
`else
        s1_small <= small_s[26:0];
`endif
    end

    // One logical 4-entry x32-bit circular bypass store (128bits), physically four8-bit banks.
    // All banks write the A2 code each edge; reading the old current slot is a four-edge delay.
    // The final u_code capture therefore has exactly the old age, without a five-FF hold chain.
    reg [31:0] bypass_mem[0:3];
    (* keep="true",dont_touch="true" *) reg [3:0] bypass_wp[0:3];
    wire [31:0] bypass_read;
    generate for(j=0;j<4;j=j+1)begin:bypass_bank
      for(genvar h=0;h<2;h=h+1)begin:half
        assign bypass_stage2[8*j+4*h+:4]=x_nf_dist[2*j+h]?4'd0:(x_az_dist[2*j+h]?(x_bz_dist[2*j+h]?4'd0:x_code_b[8*j+4*h+:4]):x_code_a[8*j+4*h+:4]);
      end
      always @(posedge clk or negedge rst_n)
        if(!rst_n)bypass_wp[j]<=4'b0001;
        else bypass_wp[j]<={bypass_wp[j][2:0],bypass_wp[j][3]};
      for(genvar slot=0;slot<4;slot=slot+1)begin:entry
        always @(posedge clk)if(bypass_wp[j][slot])bypass_mem[slot][8*j+:8]<=bypass_stage2[8*j+:8];
      end
      reg [7:0] rd;integer ri;
      always @*begin
        rd=0;
        for(ri=0;ri<4;ri=ri+1)rd=rd|(bypass_mem[ri][8*j+:8]&{8{bypass_wp[j][ri]}});
      end
      assign bypass_read[8*j+:8]=rd;
    end endgenerate

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] small28 = {1'b0, s1_small};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(small28), .cin(1'b0), .s(sum_w), .cout(sum_c));
    ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28), .b(~small28), .cin(1'b1), .s(dif_w), .cout(dif_c));
    // B1 -> B2 cut (u_cb)
    reg         t_v;
    reg         t_byp, t_sub, t_sign, t_nf;
    (* keep="true",dont_touch="true" *) reg [26:0] sentinel;
    reg  [27:0] sum;
    (* keep="true",dont_touch="true" *) reg [2:0] sum_copies;
    reg  [26:1] t_dif;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) t_v <= 1'b0;
        else t_v <= s1_v;
    always @(posedge clk) begin
        t_byp <= s1_byp; t_sub <= s1_sub; t_sign <= s1_sign; t_nf <= s1_nf; sentinel<=((s1_exp>=1)&&(s1_exp<=27))?(27'd1 << (5'd27-s1_exp[4:0])):27'd0;
        sum <= sum_w; sum_copies<={3{sum_w[27]}}; t_dif <= dif_w[26:1];
    end
    // ---- B2 ----------------------------------------------------------------------------------------
`ifdef KVP3_MUT1
    wire [26:0] dif = {1'b0, t_dif[25:1], sum[0]}; // mutant1: drop live high normalization bit; old LSB-only mutant passed300k
`else
    wire [26:0] dif = {t_dif, sum[0]};                 // dif_w[0] == sum_w[0] == s1_small[0]
`endif
    wire carry = sum[27];
    wire [26:0] shifted_add={sum[27:2],sum[1]|sum[0]};
    wire [26:0] add_val;
    generate for(k=0;k<3;k=k+1)begin:add_select
      assign add_val[9*k+:9]=sum_copies[k]?shifted_add[9*k+:9]:sum[9*k+:9];
    end endgenerate
    wire [5:0]  lz_w;
    ot_hdc_lzc32 u_lzc (.x({dif | sentinel, 5'b11111}), .n(lz_w));
    // HSPLIT: {t_exp, dif} for the pass-through from a kept second copy of the B1 -> B2 register (same edge, same value)
    wire [35:0] hq;
    ot_hdc_add_hcopy36 u_hc (.clk(clk), .d({s1_exp, dif_w}), .q(hq));
    wire [7:0]  p_exp = hq[35:28];
    wire [27:0] p_dif = hq[27:0];
    // B2a -> B2b cut (u_cd)
    reg         w_v;
    reg         w_byp, w_sub, w_sign, w_nf, w_carry;
    reg  [7:0]  w_exp;
    reg  [26:0] w_add;
    reg  [27:0] w_dif;
    reg  [4:0]  lz;
    (* keep="true",dont_touch="true" *) reg [26:0] lz_oh;
    (* keep="true",dont_touch="true" *) reg [3:0] w_sub_dist;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) w_v <= 1'b0;
        else w_v <= t_v;
    always @(posedge clk) begin
        w_byp <= t_byp; w_sub <= t_sub; w_sign <= t_sign; w_nf <= t_nf; w_exp <= p_exp;
        w_add <= add_val; w_dif <= p_dif; lz <= lz_w[4:0]; w_carry <= carry; w_sub_dist<={4{t_sub}};

    end
    generate for(j=0;j<27;j=j+1)begin:normal_capture
      always @(posedge clk)lz_oh[j]<=(lz_w[4:0]==j);
    end endgenerate
    reg [26:0] sub_val;
    integer si;
    always @*begin
      sub_val=0;
      for(si=0;si<27;si=si+1)sub_val=sub_val|((w_dif[26:0]<<si)&{27{lz_oh[si]}});
    end
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    ot_hdc_ksadd_k #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero, s2_nf;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_nf <= w_nf; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val[6:0]<=w_sub_dist[0]?sub_val[6:0]:w_add[6:0];
        s2_val[13:7]<=w_sub_dist[1]?sub_val[13:7]:w_add[13:7];
        s2_val[20:14]<=w_sub_dist[2]?sub_val[20:14]:w_add[20:14];
        s2_val[26:21]<=w_sub_dist[3]?sub_val[26:21]:w_add[26:21];
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    // C1 -> C2 cut (u_cc)
    reg         u_v;
    reg         u_byp, u_zero, u_sign, u_nf, rnd_c;
    reg  [31:0] u_code;
    reg  [7:0]  u_exp;
    reg  [23:0] rnd;
    (* keep="true",dont_touch="true" *) reg [1:0] rnd_c_dist;
    (* keep="true",dont_touch="true" *) reg [3:0] u_byp_dist;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) u_v <= 1'b0;
        else u_v <= s2_v;
    always @(posedge clk) begin
        u_byp <= s2_byp; u_zero <= s2_zero; u_sign <= s2_sign; u_nf <= s2_nf; u_code <= bypass_read; u_exp <= s2_exp;
        rnd <= rnd_w; rnd_c <= rnd_cw; rnd_c_dist<={2{rnd_cw}};u_byp_dist<={4{s2_byp}};
    end
    // ---- C2 ----------------------------------------------------------------------------------------
    wire [23:0] shifted_rnd={1'b1,rnd[23:1]};
    wire [23:0] man={rnd_c_dist[1]?shifted_rnd[23:12]:rnd[23:12],rnd_c_dist[0]?shifted_rnd[11:0]:rnd[11:0]};
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate for(k=0;k<4;k=k+1)begin:out_region
      always @(posedge clk or negedge rst_y)begin
        if(!rst_y)y[8*k+:8]<=8'd0;
        else if(u_byp_dist[k])y[8*k+:8]<=u_code[8*k+:8];
        else if(u_zero || over)y[8*k+:8]<=8'd0;
        else y[8*k+:8]<=(code[30:0]==31'd0)?8'd0:code[8*k+:8];
      end
    end endgenerate
    genvar yci;
    generate for(yci=0;yci<2;yci=yci+1)begin:g_yc
      if(yci<YCOPY)begin:g_ycopy
        (* keep="true",dont_touch="true" *) reg [31:0] yc;
        for(k=0;k<4;k=k+1)begin:out_copy
          always @(posedge clk or negedge rst_y2[yci])begin
            if(!rst_y2[yci])yc[8*k+:8]<=8'd0;
            else if(u_byp_dist[k])yc[8*k+:8]<=u_code[8*k+:8];
            else if(u_zero || over)yc[8*k+:8]<=8'd0;
            else yc[8*k+:8]<=(code[30:0]==31'd0)?8'd0:code[8*k+:8];
          end
        end
        assign y2[32*yci+:32]=yc;
      end else begin:g_noycopy
        assign y2[32*yci+:32]=y;
      end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin err<=E_NONE;valid_out<=1'b0;end
        else begin
            valid_out<=u_v;
`ifdef KVP3_MUT2
            if(u_byp)err<=E_NONE;
`else
            if(u_byp)err<={1'b0,u_nf};
`endif
            else if(u_zero)err<=E_NONE;
            else if(over)err<=E_OVERFLOW;
            else err<=E_NONE;
        end
    end
endmodule

module ot_qwen_nearhbm_prod_ncr (
    input  wire        clk,
    input  wire        rst_n,
    input wire rst_y,
    input  wire        valid_in,
    input  wire [15:0] a,            // BF16
    input  wire [7:0]  k,            // FP8 E4M3 (bias 7)
    output reg  [31:0] y,
    output reg         fault,
    output reg         valid_out
);
    wire        a_sub = (a[14:7] == 8'd0);
    wire [7:0]  sa = {!a_sub, a[6:0]};
    wire [9:0]  ea = a_sub ? 10'd1 : {2'd0, a[14:7]};
    wire        k_sub = (k[6:3] == 4'd0);
    wire [3:0]  sk = {!k_sub, k[2:0]};
    wire [9:0]  ek = k_sub ? 10'd1 : {6'd0, k[6:3]};
    wire        bad1 = (a[14:7] == 8'hFF) || (k[6:0] == 7'h7F);
    wire [9:0]  e1 = ea + ek + 10'd5;
    reg         v1, s1_sign, s1_bad;
    reg [11:0]  s1_p;
    reg [8:0]   s1_e9;
    wire [9:0]  s1_e = {1'b0, s1_e9};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v1 <= 1'b0; else v1 <= valid_in;
    end
    always @(posedge clk) begin
        s1_sign <= a[15] ^ k[7];
        s1_bad <= bad1;
        s1_p <= sa * sk;
`ifdef KVP3_MUT5
        s1_e9 <= {1'b0, e1[7:0]};                      // bench mutant 5 (must FAIL): a live exponent bit dropped
`else
        s1_e9 <= e1[8:0];
`endif
    end
    reg [3:0] lz;
    integer i;
    always @* begin
        lz = 4'd0;
        for (i = 0; i < 12; i = i + 1) if (s1_p[i]) lz = i[3:0];
    end
    wire [10:0] be = {1'b0, s1_e} + {7'd0, lz} - 11'd22;
    reg         v2, s2_bad, s2_zero, s2_sign, s2_ovf, s2_normal;
    reg [11:0]  s2_p;
    reg [7:0]   s2_be;
    (* keep="true",dont_touch="true" *) reg [22:0] s2_sh_oh;
    wire [4:0] sh_w=(!be[10] && (be != 11'd0)) ? (5'd23 - {1'b0, lz}) : s1_e[4:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v2 <= 1'b0; else v2 <= v1;
    end
    always @(posedge clk) begin
        s2_bad <= s1_bad;
        s2_sign <= s1_sign;
        s2_zero <= (s1_p == 12'd0);
        s2_p <= s1_p;
        s2_normal <= !be[10] && (be != 11'd0);
        s2_ovf <= !be[10] && (be >= 11'd255);
        s2_be <= be[7:0];

    end
    genvar pj;
    generate for(pj=0;pj<23;pj=pj+1)begin:shift_capture
      always @(posedge clk)s2_sh_oh[pj]<=(sh_w==pj);
    end endgenerate
    reg [22:0] sh;integer sj;
    always @*begin
      sh=0;
      for(sj=0;sj<23;sj=sj+1)sh=sh|(({11'd0,s2_p}<<sj)&{23{s2_sh_oh[sj]}});
    end
    reg         v3, s3_bad, s3_zero, s3_ovf;
    reg [31:0]  s3_y;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v3 <= 1'b0; else v3 <= v2;
    end
    always @(posedge clk) begin
        s3_bad <= s2_bad;
        s3_zero <= s2_zero;
        s3_ovf <= s2_ovf;
        s3_y <= {s2_sign, s2_normal ? s2_be : 8'd0, sh[22:0]};
    end
    always @(posedge clk or negedge rst_y) begin
        if(!rst_y)y<=32'd0;
        else if(s3_bad || s3_ovf)y<=32'd0;
        else y<=s3_zero?32'd0:s3_y;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin valid_out<=1'b0;fault<=1'b0;end
        else begin valid_out<=v3;fault<=(s3_bad || s3_ovf)?v3:1'b0;end
    end
endmodule
