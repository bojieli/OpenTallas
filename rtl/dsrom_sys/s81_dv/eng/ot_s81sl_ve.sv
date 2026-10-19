`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-MIX (2026-10-17): ve = the Engram-mix sub-leaf of one BEAT of a DV vector slice (planned x5 per slice, own clock
// root).  It replaces the hub-era dsfd_engram_mix4_c / the p4j void units mix4_w / mix4_e (dsfd_engram_mix4_half, never
// built): every Engram operand is beat-resident in DV (h in vn's h store; K = 4 x 5120 and V = 5120 FP32 = the
// engram.wkv field rows, captured into vp's leaf store; W = q_weight * k_weight, a per-element FP32 constant row in the
// leaf store), so the mix runs where the data is, and only 12 scalars per beat (3 sums x 4 copies) leave the leaf.
//
// Golden (tools/hdc_golden_v41.py engram_layer, chunk8 su class), copy j, D = 5120:
//   hh = csum(h*h), kk = csum(k*k), dd = csum((h*w)*k)       -> this leaf: the beat's aligned 64-element subtree sums
//   rstd = rsqrt(hh/D + eps) * rsqrt(kk/D + eps); dot = (dd*rstd)*scale; gate = sigmoid(signed sqrt(max(|dot|,1e-6)))
//                                                             -> slice finish (xfin exchange + ot_s81_engram_norm/_gate)
//   out = bf16(h + gate*v)                                    -> this leaf (add phase), written back into vn's h store
// A beat (64 elements) is 8 golden chunks = an aligned subtree of the padded pairwise tree, so the beat partial here is
// bit-identical to the flat engine's node, exactly as vn's norm beat partial.
//
// Arithmetic leaves are the gated hub-era Engram leaves, UNCHANGED (rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv):
//   ot_s81_engram_mul4   (4 lanes: h*h, k*k, h*w, (h*w)*k)      x1
//   ot_s81_engram_chunk8 (golden chunk of 8, sequential from +0) x3 (hh, kk, dd)
//   ot_s81_engram_add8   (8 lanes: bf16(h + gate*v))             x1
// plus the beat tree here (3 golden pairwise levels over the 8 chunk sums, one ot_dsrom_qadd per sum, dataflow issue
// with fixed operands per node: exact by construction, as vn's beat tree).
//
// Streams (static schedule, no ready / credit; the feeder -- the beat's vs over vp's extension port -- issues on the
// compiler's fixed timeline):
//   reduce  r_v: 4 elements a cycle {h (BF16 in an FP32 word), k, w}, copy-major, element order (16 cycles a copy,
//           64 a beat); r_c = the copy (checked against the leaf's own count: out of order = sticky fault).
//           -> p_v / p_c / p_hh / p_kk / p_dd: one beat partial triple per copy.
//   add     a_v: 8 elements a cycle {h, v} + the copy's gate; -> o_v / o_c / o_y (BF16 in the upper half of each word).
// S81-VE r2 (10-19, route b571a8c2c NEEDS_RTL TT -338 / FF -25): (1) the beat tree is a static streaming pairwise
// tree -- one adder per golden level (L1 leaf pairs, L2 node pairs, L3 root), each level pairs its in-order input
// stream (hold the even operand, issue on the odd one) -- instead of one shared adder behind a 4-slot x 7-node issue
// priority encoder and a 60-word operand mux (33 levels at TT).  Same association, same per-node issue cycle, so the
// beat-partial latency is unchanged (129 cyc GAP 0); 4-slot val store (1,920 flops/tree) gone.  (2) The arithmetic
// leaves are ve-local copies of the gated hub Engram leaves (rtl/dsrom_sys/engram/mix, unchanged there: closed views
// bind it) whose fixed operand / hold delay lines are ot_hdc_delay_rf (write-once ring + read mux, cycle-exact)
// instead of shift registers: ~14k zero-logic flop->flop hops were the FF hold endpoints that exhausted hold repair.
// Every input lands in a flop; every output leaves a flop.  MUT (bench only): 1 key -> 1.0 inside mul4; 2 beat tree
// level-1 pairs (s0 + s2), (s1 + s3) (golden association broken, same operands).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_ve #(parameter integer LM = 5, LA = 4, MUT = 0) (
    input  wire         clk,
    input  wire         rst_n,
    // reduce stream
    input  wire         r_v,
    input  wire [1:0]   r_c,
    input  wire [127:0] r_h, r_k, r_w,
    // beat partials
    output reg          p_v,
    output reg  [1:0]   p_c,
    output reg  [31:0]  p_hh, p_kk, p_dd,
    // add stream
    input  wire         a_v,
    input  wire [1:0]   a_c,
    input  wire [255:0] a_h, a_val,
    input  wire [31:0]  a_g,
    output reg          o_v,
    output reg  [1:0]   o_c,
    output reg  [255:0] o_y,
    output reg          fault
);
    wire rn;
    ot_s81_engram_reset reset_leaf (clk, rst_n, rn);

    // ---------------------------------------------------------------- input pin flops
    reg         rv_q, av_q;
    reg [1:0]   rc_q, ac_q;
    reg [127:0] rh_q, rk_q, rw_q;
    reg [255:0] ah_q, aval_q;
    reg [31:0]  ag_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin rv_q <= 1'b0; av_q <= 1'b0; end
        else begin rv_q <= r_v; av_q <= a_v; end
    always @(posedge clk) begin
        rc_q <= r_c; rh_q <= r_h; rk_q <= r_k; rw_q <= r_w;
        ac_q <= a_c; ah_q <= a_h; aval_q <= a_val; ag_q <= a_g;
    end

    // input order check: element quad counter (16 a copy), copy must match
    reg [5:0] icnt;
    reg       f_order;
    always @(posedge clk or negedge rn)
        if (!rn) begin icnt <= 6'd0; f_order <= 1'b0; end
        else if (rv_q) begin
            icnt <= icnt + 6'd1;
            if (rc_q != icnt[5:4]) f_order <= 1'b1;
        end

    // ---------------------------------------------------------------- products (h*h, k*k, (h*w)*k), 4 lanes
    wire         mv;
    wire [127:0] mhh, mkk, mdd;
    wire         mf;
    ot_s81sl_ve_mul4 #(.LM(LM), .MUT(MUT == 1 ? 1 : 0)) mul (clk, rst_n, rv_q, 1'b0, rh_q, rk_q, rw_q,
                                                              mv, mhh, mkk, mdd, mf);

    // ---------------------------------------------------------------- pack two quads into one golden chunk of 8
    reg         half;
    reg [127:0] shh, skk, sdd;
    reg         cv;
    reg [255:0] chh, ckk, cdd;
    always @(posedge clk or negedge rn)
        if (!rn) begin half <= 1'b0; cv <= 1'b0; end
        else begin
            cv <= mv && half;
            if (mv) half <= ~half;
        end
    always @(posedge clk) begin
        if (mv && !half) begin shh <= mhh; skk <= mkk; sdd <= mdd; end
        if (mv && half) begin chh <= {mhh, shh}; ckk <= {mkk, skk}; cdd <= {mdd, sdd}; end
    end

    wire [2:0]  sv, sf;
    wire [31:0] shh_s, skk_s, sdd_s;
    ot_s81sl_ve_chunk8 #(.LA(LA)) chunk_hh (clk, rst_n, cv, chh, sv[0], shh_s, sf[0]);
    ot_s81sl_ve_chunk8 #(.LA(LA)) chunk_kk (clk, rst_n, cv, ckk, sv[1], skk_s, sf[1]);
    ot_s81sl_ve_chunk8 #(.LA(LA)) chunk_dd (clk, rst_n, cv, cdd, sv[2], sdd_s, sf[2]);

    // ---------------------------------------------------------------- beat trees (lockstep)
    wire [2:0]  tv, tf;
    wire [1:0]  tc0, tc1, tc2;
    wire [31:0] thh, tkk, tdd;
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_hh (clk, rst_n, sv[0], shh_s, tv[0], tc0, thh, tf[0]);
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_kk (clk, rst_n, sv[1], skk_s, tv[1], tc1, tkk, tf[1]);
    ot_s81sl_ve_tree #(.LA(LA), .MUT(MUT)) tree_dd (clk, rst_n, sv[2], sdd_s, tv[2], tc2, tdd, tf[2]);

    always @(posedge clk or negedge rn)
        if (!rn) p_v <= 1'b0;
        else p_v <= tv[0];
    always @(posedge clk) begin p_c <= tc0; p_hh <= thh; p_kk <= tkk; p_dd <= tdd; end
    wire f_lock = (tv[0] != tv[1]) || (tv[0] != tv[2]) || (sv[0] != sv[1]) || (sv[0] != sv[2]) ||
                  (tv[0] && ((tc0 != tc1) || (tc0 != tc2)));

    // ---------------------------------------------------------------- add phase: bf16(h + gate*v), 8 lanes
    wire         yv;
    wire [255:0] yd;
    wire         yf;
    wire [1:0]   yc;
    ot_s81sl_ve_add8 #(.LM(LM), .LA(LA)) add (clk, rst_n, av_q, 1'b1, ah_q, aval_q, ag_q, ac_q, yv, yd, yf, yc);
    always @(posedge clk or negedge rn)
        if (!rn) o_v <= 1'b0;
        else o_v <= yv;
    always @(posedge clk) begin o_c <= yc; o_y <= yd; end

    always @(posedge clk or negedge rn)
        if (!rn) fault <= 1'b0;
        else if (f_order || mf || (|sf) || (|tf) || f_lock || yf) fault <= 1'b1;
endmodule

// Beat tree: 8 chunk sums of one copy arrive in order (at most one a cycle) -> the golden pairwise node
// ((s0+s1)+(s2+s3))+((s4+s5)+(s6+s7)).  Static streaming form: three pipelined adders, one per level.  Each level sees
// its operands in order (L1: leaves 0..7 of each copy, L2: L1 sums n0..n3, L3: L2 sums n4,n5), holds the even one and
// issues the pair the cycle after the odd one lands -- the cycle the shared-adder form issued the same node (its
// operands had been written the cycle before).  No arbitration, no slot store; copies leave in arrival order.
// MUT 2 (bench only): level-1 pairs (s0 + s2), (s1 + s3).
module ot_s81sl_ve_tree #(parameter integer LA = 4, MUT = 0) (
    input  wire        clk, rst_n, v,
    input  wire [31:0] s,
    output reg         vo,
    output reg  [1:0]  co,
    output reg  [31:0] y,
    output reg         fault
);
    wire rn;
    ot_s81_engram_reset reset_leaf (clk, rst_n, rn);
    // ---- level 1: leaf pairs
    reg  [2:0]  li;                        // leaf index within the copy
    reg  [31:0] h1, m1, a1, b1;
    reg         i1;
    wire hold1  = (MUT == 2) ? (li == 3'd0 || li == 3'd4 || li == 3'd6) : !li[0];
    wire stash1 = (MUT == 2) && (li == 3'd1);
    wire [31:0] pa1 = (MUT == 2 && li == 3'd3) ? m1 : h1;
    always @(posedge clk or negedge rn)
        if (!rn) begin li <= 3'd0; i1 <= 1'b0; end
        else begin
            i1 <= v && !hold1 && !stash1;
            if (v) li <= li + 3'd1;
        end
    always @(posedge clk)
        if (v) begin
            if (hold1) h1 <= s;
            else if (stash1) m1 <= s;
            else begin a1 <= pa1; b1 <= s; end
        end
    wire [31:0] s1;
    wire        f1;
    wire [LA:0] v1;
    ot_dsrom_qadd #(.LAT(LA)) add1 (clk, rn, i1, a1, b1, s1, f1);
    ot_hdc_vline #(.D(LA)) l1_line (clk, rn, i1, v1);
    wire r1 = v1[LA];
    // ---- level 2: pairs of level-1 sums (n0,n1) -> n4, (n2,n3) -> n5
    reg         p2, i2;
    reg  [31:0] h2, a2, b2;
    always @(posedge clk or negedge rn)
        if (!rn) begin p2 <= 1'b0; i2 <= 1'b0; end
        else begin
            i2 <= r1 && p2;
            if (r1) p2 <= ~p2;
        end
    always @(posedge clk)
        if (r1) begin
            if (!p2) h2 <= s1;
            else begin a2 <= h2; b2 <= s1; end
        end
    wire [31:0] s2;
    wire        f2;
    wire [LA:0] v2;
    ot_dsrom_qadd #(.LAT(LA)) add2 (clk, rn, i2, a2, b2, s2, f2);
    ot_hdc_vline #(.D(LA)) l2_line (clk, rn, i2, v2);
    wire r2 = v2[LA];
    // ---- level 3: (n4, n5) -> n6 = the beat partial
    reg         p3, i3;
    reg  [31:0] h3, a3, b3;
    always @(posedge clk or negedge rn)
        if (!rn) begin p3 <= 1'b0; i3 <= 1'b0; end
        else begin
            i3 <= r2 && p3;
            if (r2) p3 <= ~p3;
        end
    always @(posedge clk)
        if (r2) begin
            if (!p3) h3 <= s2;
            else begin a3 <= h3; b3 <= s2; end
        end
    wire [31:0] s3;
    wire        f3;
    wire [LA:0] v3;
    ot_dsrom_qadd #(.LAT(LA)) add3 (clk, rn, i3, a3, b3, s3, f3);
    ot_hdc_vline #(.D(LA)) l3_line (clk, rn, i3, v3);
    wire r3 = v3[LA];
    // ---- output: copy = arrival order
    reg [1:0] oc;
    always @(posedge clk or negedge rn)
        if (!rn) begin vo <= 1'b0; oc <= 2'd0; fault <= 1'b0; end
        else begin
            vo <= r3;
            if (r3) oc <= oc + 2'd1;
            if (f1 || f2 || f3) fault <= 1'b1;
        end
    always @(posedge clk) if (r3) begin y <= s3; co <= oc; end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ve-local arithmetic leaves: the gated hub Engram leaves of rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv (mul4,
// chunk8, add8), identical arithmetic, latency and ports, with every fixed data delay line of depth >= 3 built as
// ot_hdc_delay_rf (cycle-exact: input register, write-once ring, read mux, output register) instead of a shift line.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_ve_dly #(parameter integer W = 32, D = 1) (
    input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    generate if (D >= 3) begin : g_rf
        ot_hdc_delay_rf #(.W(W), .D(D)) u (clk, rst_n, d, q);
    end else begin : g_sh
        ot_hdc_delay #(.W(W), .D(D)) u (clk, rst_n, d, q);
    end endgenerate
endmodule

module ot_s81sl_ve_mul4 #(parameter integer LM=5,MUT=0)(
 input wire clk,arst_n,v,phase,input wire [127:0] h,k,w,
 output wire vo,output wire [127:0] hh,kk,dot,output reg fault);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg [127:0] hp,kp,wp;reg vp_in,phase_in;
 always @(posedge clk or negedge rn)if(!rn)begin vp_in<=0;phase_in<=0;end else begin vp_in<=v;phase_in<=phase;end
 always @(posedge clk)begin hp<=h;kp<=k;wp<=w;end
 reg [127:0] hr,kr,wr;reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=vp_in&&!phase_in;
 always @(posedge clk)begin hr<=hp;kr<=kp;wr<=wp;end
 wire [2*LM:0] vp;ot_hdc_vline #(.D(2*LM)) valid_line(clk,rn,vr,vp);
 wire [127:0] hs,ks,hw,dot_mid;wire [15:0] f;
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  wire [31:0] kd;
  ot_hdc_qmul_lat #(LM) mh(clk,rn,vr,hr[32*l+:32],hr[32*l+:32],hs[32*l+:32],f[4*l]);
  ot_hdc_qmul_lat #(LM) mk(clk,rn,vr,kr[32*l+:32],kr[32*l+:32],ks[32*l+:32],f[4*l+1]);
  ot_hdc_qmul_lat #(LM) mw(clk,rn,vr,hr[32*l+:32],wr[32*l+:32],hw[32*l+:32],f[4*l+2]);
  ot_s81sl_ve_dly #(.W(32),.D(LM)) key_line(clk,rn,kr[32*l+:32],kd);
  wire [31:0] dr;
  ot_hdc_qmul_lat #(LM) md(clk,rn,vp[LM],hw[32*l+:32],(MUT==1)?32'h3f800000:kd,dr,f[4*l+3]);
  reg [31:0] dout;always @(posedge clk)dout<=dr;assign dot_mid[32*l+:32]=dout;
 end endgenerate
 wire [127:0] hmid,kmid;
 ot_s81sl_ve_dly #(.W(128),.D(LM+1)) hline(clk,rn,hs,hmid);
 ot_s81sl_ve_dly #(.W(128),.D(LM+1)) kline(clk,rn,ks,kmid);
 reg [127:0] hh_pin,kk_pin,dot_pin;
 always @(posedge clk)begin hh_pin<=hmid;kk_pin<=kmid;dot_pin<=dot_mid;end
 assign hh=hh_pin;assign kk=kk_pin;assign dot=dot_pin;
 reg valid;always @(posedge clk or negedge rn)if(!rn)valid<=0;else valid<=vp[2*LM];
 reg valid_pin;always @(posedge clk or negedge rn)if(!rn)valid_pin<=0;else valid_pin<=valid;
 assign vo=valid_pin;wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81sl_ve_chunk8 #(parameter integer LA=4)(
 input wire clk,arst_n,v,input wire [255:0] x,
 output wire vo,output wire [31:0] sum,output reg fault);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg [255:0] xr;reg vr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v;
 always @(posedge clk)xr<=x;
 wire [8*LA:0] vp;ot_hdc_vline #(.D(8*LA)) valid_line(clk,rn,vr,vp);
 wire [31:0] acc[0:8];wire [7:0] f;assign acc[0]=0;
 genvar t;
 generate for(t=0;t<8;t=t+1)begin:term
  wire [31:0] xd;
  ot_s81sl_ve_dly #(.W(32),.D(LA*t)) operand_line(clk,rn,xr[32*t+:32],xd);
  ot_dsrom_qadd #(.LAT(LA)) add(clk,rn,vp[LA*t],acc[t],xd,acc[t+1],f[t]);
 end endgenerate
 assign vo=vp[8*LA];assign sum=acc[8];wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
endmodule

module ot_s81sl_ve_add8 #(parameter integer LM=5,LA=4)(
 input wire clk,arst_n,v,phase,input wire [255:0] h,value,input wire [31:0] gate,input wire [1:0] copy,
 output reg vo,output reg [255:0] y,output reg fault,output wire [1:0] copy_out);
 wire rn;ot_s81_engram_reset reset_leaf(clk,arst_n,rn);
 reg vr;reg [255:0] hr,valr;reg [31:0] gr;
 always @(posedge clk or negedge rn)if(!rn)vr<=0;else vr<=v&&phase;
 always @(posedge clk)begin hr<=h;valr<=value;gr<=gate;end
 wire [LM+LA:0] vp;ot_hdc_vline #(.D(LM+LA)) valid_line(clk,rn,vr,vp);
 wire [15:0] f;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:lane
  wire [31:0] prod,hd,ys;
  ot_hdc_qmul_lat #(LM) mul(clk,rn,vr,valr[32*l+:32],gr,prod,f[2*l]);
  ot_s81sl_ve_dly #(.W(32),.D(LM)) hline(clk,rn,hr[32*l+:32],hd);
  ot_dsrom_qadd #(.LAT(LA)) add(clk,rn,vp[LM],hd,prod,ys,f[2*l+1]);
  wire [31:0] rounded=ys+32'h7fff+ys[16];
  always @(posedge clk)y[32*l+:32]<={rounded[31:16],16'd0};
 end endgenerate
 always @(posedge clk or negedge rn)if(!rn)vo<=0;else vo<=vp[LM+LA];
 wire raw_fault=|f;
 always @(posedge clk or negedge rn)if(!rn)fault<=0;else if(raw_fault)fault<=1;
 ot_s81sl_ve_dly #(.W(2),.D(LM+LA+2)) copy_line(clk,rn,copy,copy_out);
endmodule
