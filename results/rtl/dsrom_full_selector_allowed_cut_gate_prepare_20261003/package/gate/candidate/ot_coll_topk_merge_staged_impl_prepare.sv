// SOURCE PREPARATION ONLY. Historical source clock comments below are not qualification.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_coll_topk_merge: the select half of COLL_TOPK_MERGE / ARGMAX_MERGE (W15b).
//
// Every die holds the same gathered candidates (the all-gather of each rank's
// n (score, local id) pairs, rank-major), so every die runs this identical,
// deterministic select and needs no second exchange.
//
//   global id  = rank * stride + local id
//   result     = the k global ids of the largest scores, ties to the LOWER
//                global id (tools/hdc_golden_v41.topk_lowest_index: scores
//                compared as values, so -0 == +0), emitted in ascending
//                global-id order, 16 ids a 512-bit word (the last word padded
//                with zeros).
//   order      = candidates are stored rank-major and each rank's local ids
//                ascending (the contract), so buffer order IS global-id order.
//
// Method: exact radix select, then one filter pass.
//   keys       binary32 -> an order-preserving u32 (-0 canonicalised to +0;
//              a NaN score latches fault).
//   HIST pass  d = 0..32/DIG-1: P candidates a cycle; those whose top d*DIG
//              key bits equal the prefix found so far are counted into
//              2^DIG bins by their next DIG bits.  The bin holding the r-th
//              largest extends the prefix and r becomes the rank inside it.
//              After the last pass the prefix is T, the k-th largest key, and
//              r is how many keys equal to T are taken.
//   FILTER     P candidates a cycle in buffer order: take key > T, or
//              key == T while fewer than r equal keys were taken (ties to the
//              lower id, since buffer order is id order).  Taken ids are
//              compacted (prefix counts, one-hot slot select) into a staging
//              buffer that emits OW = PF/LW full words at a time (aligned).
// Cycles (no stalls): (32/DIG) x (N*n/P + 7) + N*n/PF + 9.
// The candidate buffers are register files here (a synthesis stand-in for
// the die's SRAM); all timing-critical logic is pipelined for 1.2 GHz at SS.
// ---------------------------------------------------------------------------
module ot_coll_topk_merge_staged_impl_prepare #(
    parameter integer MUTANT = 0,
    parameter integer N     = 4,              // ranks
    parameter integer NMAX  = 512,            // candidates per rank (max); n % P == 0
    parameter integer LW    = 16,             // lanes (u32 elements) in one VM word
    parameter integer LDW   = 1,              // words a load beat: 1 (rank ld_rank) or N (word j is rank j)
    parameter integer P     = 64,             // HIST candidates a cycle (multiple of LW)
    parameter integer PF    = P,              // FILTER candidates a cycle (divides P, multiple of LW): the filter's
                                              // compactor is PF x PF, so a wide P keeps a narrow PF
    parameter integer DIG   = 4,              // radix bits per HIST pass (divides 32)
    parameter integer RB    = (N > 1) ? $clog2(N) : 1,
    parameter integer CAP   = N * NMAX,
    parameter integer CB    = $clog2(CAP + 1),
    parameter integer WB    = $clog2(CAP / LW),
    parameter integer OW    = PF / LW         // output words a cycle (max)
) (
    input  wire              clk,
    input  wire              rst_n,
    // gathered candidates: one 16-lane word of scores (ld_id 0) or local ids (ld_id 1) of rank ld_rank
    input  wire              ld_valid,
    input  wire              ld_id,
    input  wire [RB-1:0]     ld_rank,
    input  wire [WB-1:0]     ld_word,         // word index inside the rank (n / LW words); n stable while loading
    input  wire [32*LW*LDW-1:0] ld_data,
    // command
    input  wire              go,
    input  wire [CB-1:0]     n,               // candidates per rank
    input  wire [CB-1:0]     k,               // 1 <= k <= N * n
    input  wire [31:0]       stride,          // >= n (rank r owns [r*stride, (r+1)*stride))
    output reg               busy,
    output reg               done,            // one cycle, after the last output word
    output reg               fault,           // NaN score, or a bad command
    // result: out_nw words (LW ids each, word 0 in the low bits) a cycle, in order, in aligned groups of OW
    // words (only the last group may be short; the last word zero-padded)
    output reg               out_valid,
    output reg  [$clog2(OW+1)-1:0] out_nw,
    output reg  [32*LW*OW-1:0] out_data,
    output reg               out_last,
    output reg  [31:0]       stat_cycles      // go -> done
);
    initial begin
        if(N!=4 || NMAX!=2048 || LW!=16 || LDW!=4 || P!=64 || PF!=64 || DIG!=8 || CB!=14)
            $fatal(1,"BALANCED_FULL_GEOMETRY_REQUIRED");
        if(MUTANT<0 || MUTANT>2) $fatal(1,"UNKNOWN_CORE_MUTANT");
    end
    // Source cycle comment remains historical; runtime calibration is a gate.
    localparam integer NR    = CAP / P;        // P-lane rows
    localparam integer QW    = P / LW;         // words per row
    localparam integer NPASS = 32 / DIG;
    localparam integer NBIN  = 1 << DIG;
    localparam integer RRB   = (NR > 1) ? $clog2(NR) : 1;
    localparam integer PB    = $clog2(P + 1);
    localparam integer SB    = $clog2(2 * PF + 1);
    localparam integer FB    = $clog2(PF + 1);
    localparam integer FQ    = P / PF;         // filter chunks per row

    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;       // -0 == +0 (values compared)
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic isnan(input [31:0] x);
        isnan = (x[30:23] == 8'hFF) && (x[22:0] != 0);
    endfunction

    // ---- candidate buffers (P-lane rows) ------------------------------------------------------------------
    reg [32*P-1:0] kmem [0:NR-1];
    reg [32*P-1:0] imem [0:NR-1];
    reg            nan_seen;
    reg [WB:0]     wpr;                             // words per rank (n / LW)
    integer ln, lj;
    always @(posedge clk) if (ld_valid)
        for (lj = 0; lj < LDW; lj = lj + 1) begin : wr
            reg [WB+RB:0] fw;
            fw = (LDW == 1 ? ld_rank : lj[RB-1:0]) * wpr + ld_word;
            if (ld_id) imem[fw / QW][32*LW*(fw % QW) +: 32*LW] <= ld_data[32*LW*lj +: 32*LW];
            else for (ln = 0; ln < LW; ln = ln + 1)
                kmem[fw / QW][32*(LW*(fw % QW) + ln) +: 32] <= okey(ld_data[32*(LW*lj + ln) +: 32]);
        end

    // ---- control ------------------------------------------------------------------------------------------
    localparam [2:0] S_IDLE = 3'd0, S_HIST = 3'd1, S_PICK = 3'd2, S_FILT = 3'd3, S_DRAIN = 3'd4;
    reg  [2:0]      st;
    reg  [CB-1:0]   k_r, n_r;
    reg  [31:0]     stride_r;
    reg  [31:0]     prefix;
    reg  [$clog2(NPASS+1)-1:0] pass;
    reg  [CB-1:0]   rr;
    reg  [RRB:0]    row, nrow, rpr;                 // row issued, rows in use, rows per rank
    reg  [CB-1:0]   cnt [0:NBIN-1];
    wire [5:0]      sh = 6'd32 - 6'(pass) * 6'(DIG);
    integer b, l, j;

    // ---- HIST: read row -> match + one-hot -> per-bin popcount -> accumulate ------------------------------------
    reg h0_v,h1_v;
    wire h2_v;
    reg [5:0] hist_valid;
    assign h2_v=hist_valid[5];
    always @(posedge clk or negedge rst_n)
      if(!rst_n) hist_valid<=0; else hist_valid<={hist_valid[4:0],h1_v};
    reg [32*P-1:0]   h0_k;
    reg [P-1:0]      h1_hot [0:NBIN-1];
    reg [PB-1:0]     h2_pc [0:NBIN-1];
    always @(posedge clk) begin
        h0_k <= kmem[row[RRB-1:0]];
        for (l = 0; l < P; l = l + 1) begin : hot
            reg [31:0] kk;
            reg [63:0] top;
            reg        m;
            kk = h0_k[32*l +: 32];
            top = {32'd0, kk} >> sh;
            m = (top[31:0] == ({32'd0, prefix} >> sh));
            for (b = 0; b < NBIN; b = b + 1)
                h1_hot[b][l] <= m && (((kk >> (sh - DIG)) & (NBIN - 1)) == b);
        end

    end

    reg [1:0] hist_pc_1[0:NBIN-1][0:31];
    generate for(genvar hb1=0;hb1<NBIN;hb1=hb1+1) begin:g_hist_1
      for(genvar hi1=0;hi1<32;hi1=hi1+1) begin:g_pair
        always @(posedge clk) hist_pc_1[hb1][hi1]<=2'(h1_hot[hb1][2*hi1])+2'(h1_hot[hb1][2*hi1+1]);
      end
    end endgenerate
    reg [2:0] hist_pc_2[0:NBIN-1][0:15];
    generate for(genvar hb2=0;hb2<NBIN;hb2=hb2+1) begin:g_hist_2
      for(genvar hi2=0;hi2<16;hi2=hi2+1) begin:g_pair
        always @(posedge clk) hist_pc_2[hb2][hi2]<=3'(hist_pc_1[hb2][2*hi2])+3'(hist_pc_1[hb2][2*hi2+1]);
      end
    end endgenerate
    reg [3:0] hist_pc_3[0:NBIN-1][0:7];
    generate for(genvar hb3=0;hb3<NBIN;hb3=hb3+1) begin:g_hist_3
      for(genvar hi3=0;hi3<8;hi3=hi3+1) begin:g_pair
        always @(posedge clk) hist_pc_3[hb3][hi3]<=4'(hist_pc_2[hb3][2*hi3])+4'(hist_pc_2[hb3][2*hi3+1]);
      end
    end endgenerate
    reg [4:0] hist_pc_4[0:NBIN-1][0:3];
    generate for(genvar hb4=0;hb4<NBIN;hb4=hb4+1) begin:g_hist_4
      for(genvar hi4=0;hi4<4;hi4=hi4+1) begin:g_pair
        always @(posedge clk) hist_pc_4[hb4][hi4]<=5'(hist_pc_3[hb4][2*hi4])+5'(hist_pc_3[hb4][2*hi4+1]);
      end
    end endgenerate
    reg [5:0] hist_pc_5[0:NBIN-1][0:1];
    generate for(genvar hb5=0;hb5<NBIN;hb5=hb5+1) begin:g_hist_5
      for(genvar hi5=0;hi5<2;hi5=hi5+1) begin:g_pair
        always @(posedge clk) hist_pc_5[hb5][hi5]<=6'(hist_pc_4[hb5][2*hi5])+6'(hist_pc_4[hb5][2*hi5+1]);
      end
    end endgenerate
    generate for(genvar hb6=0;hb6<NBIN;hb6=hb6+1) begin:g_hist_6
      for(genvar hi6=0;hi6<1;hi6=hi6+1) begin:g_pair
        always @(posedge clk) h2_pc[hb6]<=7'(hist_pc_5[hb6][2*hi6])+7'(hist_pc_5[hb6][2*hi6+1]);
      end
    end endgenerate

    // ---- PICK -----------------------------------------------------------------------------------------------
    reg  [CB-1:0]   suf [0:NBIN-1];
    reg [4:0] pk;
    reg pvalid;
    reg  [DIG-1:0]  pbin;
    reg  [CB-1:0]   pgt;

    reg [CB-1:0] suffix_up_0[0:127];
    generate for(genvar su0=0;su0<128;su0=su0+1) begin:g_up_0
      always @(posedge clk) if(st==S_PICK && pk==0) suffix_up_0[su0]<=CB'(cnt[2*su0]+cnt[2*su0+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_1[0:63];
    generate for(genvar su1=0;su1<64;su1=su1+1) begin:g_up_1
      always @(posedge clk) if(st==S_PICK && pk==1) suffix_up_1[su1]<=CB'(suffix_up_0[2*su1]+suffix_up_0[2*su1+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_2[0:31];
    generate for(genvar su2=0;su2<32;su2=su2+1) begin:g_up_2
      always @(posedge clk) if(st==S_PICK && pk==2) suffix_up_2[su2]<=CB'(suffix_up_1[2*su2]+suffix_up_1[2*su2+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_3[0:15];
    generate for(genvar su3=0;su3<16;su3=su3+1) begin:g_up_3
      always @(posedge clk) if(st==S_PICK && pk==3) suffix_up_3[su3]<=CB'(suffix_up_2[2*su3]+suffix_up_2[2*su3+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_4[0:7];
    generate for(genvar su4=0;su4<8;su4=su4+1) begin:g_up_4
      always @(posedge clk) if(st==S_PICK && pk==4) suffix_up_4[su4]<=CB'(suffix_up_3[2*su4]+suffix_up_3[2*su4+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_5[0:3];
    generate for(genvar su5=0;su5<4;su5=su5+1) begin:g_up_5
      always @(posedge clk) if(st==S_PICK && pk==5) suffix_up_5[su5]<=CB'(suffix_up_4[2*su5]+suffix_up_4[2*su5+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_6[0:1];
    generate for(genvar su6=0;su6<2;su6=su6+1) begin:g_up_6
      always @(posedge clk) if(st==S_PICK && pk==6) suffix_up_6[su6]<=CB'(suffix_up_5[2*su6]+suffix_up_5[2*su6+1]);
    end endgenerate
    reg [CB-1:0] suffix_up_7[0:0];
    generate for(genvar su7=0;su7<1;su7=su7+1) begin:g_up_7
      always @(posedge clk) if(st==S_PICK && pk==7) suffix_up_7[su7]<=CB'(suffix_up_6[2*su7]+suffix_up_6[2*su7+1]);
    end endgenerate
    reg [CB-1:0] suffix_down_0[0:1];
    generate for(genvar sd0=0;sd0<1;sd0=sd0+1) begin:g_down_0
      always @(posedge clk) if(st==S_PICK && pk==8) begin
        suffix_down_0[2*sd0]<=CB'(CB'(0)+suffix_up_6[2*sd0+1]);
        suffix_down_0[2*sd0+1]<=CB'(0);
      end
    end endgenerate
    reg [CB-1:0] suffix_down_1[0:3];
    generate for(genvar sd1=0;sd1<2;sd1=sd1+1) begin:g_down_1
      always @(posedge clk) if(st==S_PICK && pk==9) begin
        suffix_down_1[2*sd1]<=CB'(suffix_down_0[sd1]+suffix_up_5[2*sd1+1]);
        suffix_down_1[2*sd1+1]<=suffix_down_0[sd1];
      end
    end endgenerate
    reg [CB-1:0] suffix_down_2[0:7];
    generate for(genvar sd2=0;sd2<4;sd2=sd2+1) begin:g_down_2
      always @(posedge clk) if(st==S_PICK && pk==10) begin
        suffix_down_2[2*sd2]<=CB'(suffix_down_1[sd2]+suffix_up_4[2*sd2+1]);
        suffix_down_2[2*sd2+1]<=suffix_down_1[sd2];
      end
    end endgenerate
    reg [CB-1:0] suffix_down_3[0:15];
    generate for(genvar sd3=0;sd3<8;sd3=sd3+1) begin:g_down_3
      always @(posedge clk) if(st==S_PICK && pk==11) begin
        suffix_down_3[2*sd3]<=CB'(suffix_down_2[sd3]+suffix_up_3[2*sd3+1]);
        suffix_down_3[2*sd3+1]<=suffix_down_2[sd3];
      end
    end endgenerate
    reg [CB-1:0] suffix_down_4[0:31];
    generate for(genvar sd4=0;sd4<16;sd4=sd4+1) begin:g_down_4
      always @(posedge clk) if(st==S_PICK && pk==12) begin
        suffix_down_4[2*sd4]<=CB'(suffix_down_3[sd4]+suffix_up_2[2*sd4+1]);
        suffix_down_4[2*sd4+1]<=suffix_down_3[sd4];
      end
    end endgenerate
    reg [CB-1:0] suffix_down_5[0:63];
    generate for(genvar sd5=0;sd5<32;sd5=sd5+1) begin:g_down_5
      always @(posedge clk) if(st==S_PICK && pk==13) begin
        suffix_down_5[2*sd5]<=CB'(suffix_down_4[sd5]+suffix_up_1[2*sd5+1]);
        suffix_down_5[2*sd5+1]<=suffix_down_4[sd5];
      end
    end endgenerate
    reg [CB-1:0] suffix_down_6[0:127];
    generate for(genvar sd6=0;sd6<64;sd6=sd6+1) begin:g_down_6
      always @(posedge clk) if(st==S_PICK && pk==14) begin
        suffix_down_6[2*sd6]<=CB'(suffix_down_5[sd6]+suffix_up_0[2*sd6+1]);
        suffix_down_6[2*sd6+1]<=suffix_down_5[sd6];
      end
    end endgenerate
    generate for(genvar sd7=0;sd7<128;sd7=sd7+1) begin:g_down_7
      always @(posedge clk) if(st==S_PICK && pk==15) begin
        suf[2*sd7]<=CB'(suffix_down_6[sd7]+cnt[2*sd7+1]);
        suf[2*sd7+1]<=suffix_down_6[sd7];
      end
    end endgenerate
    reg [CB:0] choose_lower_sum[0:NBIN-1];
    reg [NBIN-1:0] choose_pred;
    generate for(genvar cp=0;cp<NBIN;cp=cp+1) begin:g_predicate
      always @(posedge clk) begin
        if(st==S_PICK && pk==16) choose_lower_sum[cp]<={(suf[cp]<rr),CB'(suf[cp]+cnt[cp])};
        if(st==S_PICK && pk==17) choose_pred[cp]<=choose_lower_sum[cp][CB] && (rr<=choose_lower_sum[cp][CB-1:0]);
      end
    end endgenerate
    reg [CB+DIG:0] choose_node_0[0:127];
    generate for(genvar cw0=0;cw0<128;cw0=cw0+1) begin:g_winner_0
      always @(posedge clk) if(st==S_PICK && pk==18) choose_node_0[cw0]<=choose_pred[2*cw0+1]?{choose_pred[2*cw0+1],DIG'(2*cw0+1),suf[2*cw0+1]}:{choose_pred[2*cw0],DIG'(2*cw0),suf[2*cw0]};
    end endgenerate
    reg [CB+DIG:0] choose_node_1[0:63];
    generate for(genvar cw1=0;cw1<64;cw1=cw1+1) begin:g_winner_1
      always @(posedge clk) if(st==S_PICK && pk==19) choose_node_1[cw1]<=choose_node_0[2*cw1+1][CB+DIG]?choose_node_0[2*cw1+1]:choose_node_0[2*cw1];
    end endgenerate
    reg [CB+DIG:0] choose_node_2[0:31];
    generate for(genvar cw2=0;cw2<32;cw2=cw2+1) begin:g_winner_2
      always @(posedge clk) if(st==S_PICK && pk==20) choose_node_2[cw2]<=choose_node_1[2*cw2+1][CB+DIG]?choose_node_1[2*cw2+1]:choose_node_1[2*cw2];
    end endgenerate
    reg [CB+DIG:0] choose_node_3[0:15];
    generate for(genvar cw3=0;cw3<16;cw3=cw3+1) begin:g_winner_3
      always @(posedge clk) if(st==S_PICK && pk==21) choose_node_3[cw3]<=choose_node_2[2*cw3+1][CB+DIG]?choose_node_2[2*cw3+1]:choose_node_2[2*cw3];
    end endgenerate
    reg [CB+DIG:0] choose_node_4[0:7];
    generate for(genvar cw4=0;cw4<8;cw4=cw4+1) begin:g_winner_4
      always @(posedge clk) if(st==S_PICK && pk==22) choose_node_4[cw4]<=choose_node_3[2*cw4+1][CB+DIG]?choose_node_3[2*cw4+1]:choose_node_3[2*cw4];
    end endgenerate
    reg [CB+DIG:0] choose_node_5[0:3];
    generate for(genvar cw5=0;cw5<4;cw5=cw5+1) begin:g_winner_5
      always @(posedge clk) if(st==S_PICK && pk==23) choose_node_5[cw5]<=choose_node_4[2*cw5+1][CB+DIG]?choose_node_4[2*cw5+1]:choose_node_4[2*cw5];
    end endgenerate
    reg [CB+DIG:0] choose_node_6[0:1];
    generate for(genvar cw6=0;cw6<2;cw6=cw6+1) begin:g_winner_6
      always @(posedge clk) if(st==S_PICK && pk==24) choose_node_6[cw6]<=choose_node_5[2*cw6+1][CB+DIG]?choose_node_5[2*cw6+1]:choose_node_5[2*cw6];
    end endgenerate
    wire [CB+DIG:0] choose_root=choose_node_6[1][CB+DIG]?choose_node_6[1]:choose_node_6[0];

    // ---- FILTER: read -> compare -> take -> prefix -> compact -> stage/emit ------------------------------------
    reg              f0_v, f1_v, f2_v, f3_v, f4_v;
    reg  [32*PF-1:0]  f0_k, f0_i, f1_id, f2_id, f3_id;
    reg  [31:0]      f0_base, rbase;
    reg  [RRB+8:0]   frow, frr, nfch, fpr;          // chunk issued; chunk inside the rank; chunks in use; per rank
    reg  [PF-1:0]     f1_gt, f1_eq, f2_take, f3_take;
    reg  [FB-1:0]    f3_tp [0:PF-1];                 // take prefix counts
    reg  [FB-1:0]    f3_n;
    reg  [32*PF-1:0]  f4_c;                          // compacted ids
    reg  [FB-1:0]    f4_n;
    reg  [CB-1:0]    eq_left;
    reg  [64*PF-1:0]  stg;                           // 2PF staging slots
    reg  [SB-1:0]    stn;
    reg  [CB-1:0]    outw_left;
    wire [31:0]      T = prefix;
    wire fpipe=f0_v || f1_v || f2_v || f3_v || f4_v || eq_v_0 || eq_v_1 || eq_v_2 || eq_v_3 || eq_v_4 || eq_v_5 || (|sort_valid);

    reg [1:0] eq_count_0[0:PF-1];
    reg [32*PF-1:0] eq_id_0;
    reg [PF-1:0] eq_gt_0,eq_mask_0;
    reg eq_v_0;
    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_0<=0; else eq_v_0<=f1_v;
    always @(posedge clk) begin
      eq_id_0<=f1_id;
      eq_gt_0<=f1_gt;
      eq_mask_0<=f1_eq;
    end
    generate for(genvar ep0=0;ep0<PF;ep0=ep0+1) begin:g_eq_0
      if(ep0>=1) always @(posedge clk) eq_count_0[ep0]<=2'(f1_eq[ep0])+2'(f1_eq[ep0-1]);
      else always @(posedge clk) eq_count_0[ep0]<=2'(f1_eq[ep0]);
    end endgenerate
    reg [2:0] eq_count_1[0:PF-1];
    reg [32*PF-1:0] eq_id_1;
    reg [PF-1:0] eq_gt_1,eq_mask_1;
    reg eq_v_1;
    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_1<=0; else eq_v_1<=eq_v_0;
    always @(posedge clk) begin
      eq_id_1<=eq_id_0;
      eq_gt_1<=eq_gt_0;
      eq_mask_1<=eq_mask_0;
    end
    generate for(genvar ep1=0;ep1<PF;ep1=ep1+1) begin:g_eq_1
      if(ep1>=2) always @(posedge clk) eq_count_1[ep1]<=3'(eq_count_0[ep1])+3'(eq_count_0[ep1-2]);
      else always @(posedge clk) eq_count_1[ep1]<=3'(eq_count_0[ep1]);
    end endgenerate
    reg [3:0] eq_count_2[0:PF-1];
    reg [32*PF-1:0] eq_id_2;
    reg [PF-1:0] eq_gt_2,eq_mask_2;
    reg eq_v_2;
    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_2<=0; else eq_v_2<=eq_v_1;
    always @(posedge clk) begin
      eq_id_2<=eq_id_1;
      eq_gt_2<=eq_gt_1;
      eq_mask_2<=eq_mask_1;
    end
    generate for(genvar ep2=0;ep2<PF;ep2=ep2+1) begin:g_eq_2
      if(ep2>=4) always @(posedge clk) eq_count_2[ep2]<=4'(eq_count_1[ep2])+4'(eq_count_1[ep2-4]);
      else always @(posedge clk) eq_count_2[ep2]<=4'(eq_count_1[ep2]);
    end endgenerate
    reg [4:0] eq_count_3[0:PF-1];
    reg [32*PF-1:0] eq_id_3;
    reg [PF-1:0] eq_gt_3,eq_mask_3;
    reg eq_v_3;
    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_3<=0; else eq_v_3<=eq_v_2;
    always @(posedge clk) begin
      eq_id_3<=eq_id_2;
      eq_gt_3<=eq_gt_2;
      eq_mask_3<=eq_mask_2;
    end
    generate for(genvar ep3=0;ep3<PF;ep3=ep3+1) begin:g_eq_3
      if(ep3>=8) always @(posedge clk) eq_count_3[ep3]<=5'(eq_count_2[ep3])+5'(eq_count_2[ep3-8]);
      else always @(posedge clk) eq_count_3[ep3]<=5'(eq_count_2[ep3]);
    end endgenerate
    reg [5:0] eq_count_4[0:PF-1];
    reg [32*PF-1:0] eq_id_4;
    reg [PF-1:0] eq_gt_4,eq_mask_4;
    reg eq_v_4;
    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_4<=0; else eq_v_4<=eq_v_3;
    always @(posedge clk) begin
      eq_id_4<=eq_id_3;
      eq_gt_4<=eq_gt_3;
      eq_mask_4<=eq_mask_3;
    end
    generate for(genvar ep4=0;ep4<PF;ep4=ep4+1) begin:g_eq_4
      if(ep4>=16) always @(posedge clk) eq_count_4[ep4]<=6'(eq_count_3[ep4])+6'(eq_count_3[ep4-16]);
      else always @(posedge clk) eq_count_4[ep4]<=6'(eq_count_3[ep4]);
    end endgenerate
    reg [6:0] eq_count_5[0:PF-1];
    reg [32*PF-1:0] eq_id_5;
    reg [PF-1:0] eq_gt_5,eq_mask_5;
    reg eq_v_5;
    always @(posedge clk or negedge rst_n) if(!rst_n) eq_v_5<=0; else eq_v_5<=eq_v_4;
    always @(posedge clk) begin
      eq_id_5<=eq_id_4;
      eq_gt_5<=eq_gt_4;
      eq_mask_5<=eq_mask_4;
    end
    generate for(genvar ep5=0;ep5<PF;ep5=ep5+1) begin:g_eq_5
      if(ep5>=32) always @(posedge clk) eq_count_5[ep5]<=7'(eq_count_4[ep5])+7'(eq_count_4[ep5-32]);
      else always @(posedge clk) eq_count_5[ep5]<=7'(eq_count_4[ep5]);
    end endgenerate
    reg [19:0] sort_valid;
    always @(posedge clk or negedge rst_n)
      if(!rst_n) sort_valid<=0; else sort_valid<={sort_valid[18:0],f3_v};
    reg [38:0] sort_record_1[0:PF-1];
    generate for(genvar si1=0;si1<PF;si1=si1+1) begin:g_sort_1
      wire [38:0] here={f3_tp[si1],f3_id[32*si1+:32]},other={f3_tp[(si1^1)],f3_id[32*(si1^1)+:32]};
      wire ascending=(si1&2)==0;
      wire lower_lane=(si1&1)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_1[si1]<=chosen;
    end endgenerate
    reg [38:0] sort_record_2[0:PF-1];
    generate for(genvar si2=0;si2<PF;si2=si2+1) begin:g_sort_2
      wire [38:0] here=sort_record_1[si2],other=sort_record_1[(si2^2)];
      wire ascending=(si2&4)==0;
      wire lower_lane=(si2&2)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_2[si2]<=chosen;
    end endgenerate
    reg [38:0] sort_record_3[0:PF-1];
    generate for(genvar si3=0;si3<PF;si3=si3+1) begin:g_sort_3
      wire [38:0] here=sort_record_2[si3],other=sort_record_2[(si3^1)];
      wire ascending=(si3&4)==0;
      wire lower_lane=(si3&1)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_3[si3]<=chosen;
    end endgenerate
    reg [38:0] sort_record_4[0:PF-1];
    generate for(genvar si4=0;si4<PF;si4=si4+1) begin:g_sort_4
      wire [38:0] here=sort_record_3[si4],other=sort_record_3[(si4^4)];
      wire ascending=(si4&8)==0;
      wire lower_lane=(si4&4)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_4[si4]<=chosen;
    end endgenerate
    reg [38:0] sort_record_5[0:PF-1];
    generate for(genvar si5=0;si5<PF;si5=si5+1) begin:g_sort_5
      wire [38:0] here=sort_record_4[si5],other=sort_record_4[(si5^2)];
      wire ascending=(si5&8)==0;
      wire lower_lane=(si5&2)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_5[si5]<=chosen;
    end endgenerate
    reg [38:0] sort_record_6[0:PF-1];
    generate for(genvar si6=0;si6<PF;si6=si6+1) begin:g_sort_6
      wire [38:0] here=sort_record_5[si6],other=sort_record_5[(si6^1)];
      wire ascending=(si6&8)==0;
      wire lower_lane=(si6&1)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_6[si6]<=chosen;
    end endgenerate
    reg [38:0] sort_record_7[0:PF-1];
    generate for(genvar si7=0;si7<PF;si7=si7+1) begin:g_sort_7
      wire [38:0] here=sort_record_6[si7],other=sort_record_6[(si7^8)];
      wire ascending=(si7&16)==0;
      wire lower_lane=(si7&8)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_7[si7]<=chosen;
    end endgenerate
    reg [38:0] sort_record_8[0:PF-1];
    generate for(genvar si8=0;si8<PF;si8=si8+1) begin:g_sort_8
      wire [38:0] here=sort_record_7[si8],other=sort_record_7[(si8^4)];
      wire ascending=(si8&16)==0;
      wire lower_lane=(si8&4)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_8[si8]<=chosen;
    end endgenerate
    reg [38:0] sort_record_9[0:PF-1];
    generate for(genvar si9=0;si9<PF;si9=si9+1) begin:g_sort_9
      wire [38:0] here=sort_record_8[si9],other=sort_record_8[(si9^2)];
      wire ascending=(si9&16)==0;
      wire lower_lane=(si9&2)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_9[si9]<=chosen;
    end endgenerate
    reg [38:0] sort_record_10[0:PF-1];
    generate for(genvar si10=0;si10<PF;si10=si10+1) begin:g_sort_10
      wire [38:0] here=sort_record_9[si10],other=sort_record_9[(si10^1)];
      wire ascending=(si10&16)==0;
      wire lower_lane=(si10&1)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_10[si10]<=chosen;
    end endgenerate
    reg [38:0] sort_record_11[0:PF-1];
    generate for(genvar si11=0;si11<PF;si11=si11+1) begin:g_sort_11
      wire [38:0] here=sort_record_10[si11],other=sort_record_10[(si11^16)];
      wire ascending=(si11&32)==0;
      wire lower_lane=(si11&16)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_11[si11]<=chosen;
    end endgenerate
    reg [38:0] sort_record_12[0:PF-1];
    generate for(genvar si12=0;si12<PF;si12=si12+1) begin:g_sort_12
      wire [38:0] here=sort_record_11[si12],other=sort_record_11[(si12^8)];
      wire ascending=(si12&32)==0;
      wire lower_lane=(si12&8)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_12[si12]<=chosen;
    end endgenerate
    reg [38:0] sort_record_13[0:PF-1];
    generate for(genvar si13=0;si13<PF;si13=si13+1) begin:g_sort_13
      wire [38:0] here=sort_record_12[si13],other=sort_record_12[(si13^4)];
      wire ascending=(si13&32)==0;
      wire lower_lane=(si13&4)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_13[si13]<=chosen;
    end endgenerate
    reg [38:0] sort_record_14[0:PF-1];
    generate for(genvar si14=0;si14<PF;si14=si14+1) begin:g_sort_14
      wire [38:0] here=sort_record_13[si14],other=sort_record_13[(si14^2)];
      wire ascending=(si14&32)==0;
      wire lower_lane=(si14&2)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_14[si14]<=chosen;
    end endgenerate
    reg [38:0] sort_record_15[0:PF-1];
    generate for(genvar si15=0;si15<PF;si15=si15+1) begin:g_sort_15
      wire [38:0] here=sort_record_14[si15],other=sort_record_14[(si15^1)];
      wire ascending=(si15&32)==0;
      wire lower_lane=(si15&1)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_15[si15]<=chosen;
    end endgenerate
    reg [38:0] sort_record_16[0:PF-1];
    generate for(genvar si16=0;si16<PF;si16=si16+1) begin:g_sort_16
      wire [38:0] here=sort_record_15[si16],other=sort_record_15[(si16^32)];
      wire ascending=(si16&64)==0;
      wire lower_lane=(si16&32)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_16[si16]<=chosen;
    end endgenerate
    reg [38:0] sort_record_17[0:PF-1];
    generate for(genvar si17=0;si17<PF;si17=si17+1) begin:g_sort_17
      wire [38:0] here=sort_record_16[si17],other=sort_record_16[(si17^16)];
      wire ascending=(si17&64)==0;
      wire lower_lane=(si17&16)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_17[si17]<=chosen;
    end endgenerate
    reg [38:0] sort_record_18[0:PF-1];
    generate for(genvar si18=0;si18<PF;si18=si18+1) begin:g_sort_18
      wire [38:0] here=sort_record_17[si18],other=sort_record_17[(si18^8)];
      wire ascending=(si18&64)==0;
      wire lower_lane=(si18&8)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_18[si18]<=chosen;
    end endgenerate
    reg [38:0] sort_record_19[0:PF-1];
    generate for(genvar si19=0;si19<PF;si19=si19+1) begin:g_sort_19
      wire [38:0] here=sort_record_18[si19],other=sort_record_18[(si19^4)];
      wire ascending=(si19&64)==0;
      wire lower_lane=(si19&4)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_19[si19]<=chosen;
    end endgenerate
    reg [38:0] sort_record_20[0:PF-1];
    generate for(genvar si20=0;si20<PF;si20=si20+1) begin:g_sort_20
      wire [38:0] here=sort_record_19[si20],other=sort_record_19[(si20^2)];
      wire ascending=(si20&64)==0;
      wire lower_lane=(si20&2)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) sort_record_20[si20]<=chosen;
    end endgenerate
    generate for(genvar si21=0;si21<PF;si21=si21+1) begin:g_sort_21
      wire [38:0] here=sort_record_20[si21],other=sort_record_20[(si21^1)];
      wire ascending=(si21&64)==0;
      wire lower_lane=(si21&1)==0;
      wire choose_min=(ascending==lower_lane);
      wire [38:0] chosen=(choose_min ? (here[38:32]<other[38:32]) : (here[38:32]>other[38:32]))?here:other;
      always @(posedge clk) f4_c[32*si21+:32]<=chosen[38]?32'd0:chosen[31:0];
    end endgenerate
    reg [1:0] take_count_1[0:31];
    generate for(genvar tc1=0;tc1<32;tc1=tc1+1) begin:g_take_count_1
      always @(posedge clk) take_count_1[tc1]<=2'(f3_take[2*tc1])+2'(f3_take[2*tc1+1]);
    end endgenerate
    reg [2:0] take_count_2[0:15];
    generate for(genvar tc2=0;tc2<16;tc2=tc2+1) begin:g_take_count_2
      always @(posedge clk) take_count_2[tc2]<=3'(take_count_1[2*tc2])+3'(take_count_1[2*tc2+1]);
    end endgenerate
    reg [3:0] take_count_3[0:7];
    generate for(genvar tc3=0;tc3<8;tc3=tc3+1) begin:g_take_count_3
      always @(posedge clk) take_count_3[tc3]<=4'(take_count_2[2*tc3])+4'(take_count_2[2*tc3+1]);
    end endgenerate
    reg [4:0] take_count_4[0:3];
    generate for(genvar tc4=0;tc4<4;tc4=tc4+1) begin:g_take_count_4
      always @(posedge clk) take_count_4[tc4]<=5'(take_count_3[2*tc4])+5'(take_count_3[2*tc4+1]);
    end endgenerate
    reg [5:0] take_count_5[0:1];
    generate for(genvar tc5=0;tc5<2;tc5=tc5+1) begin:g_take_count_5
      always @(posedge clk) take_count_5[tc5]<=6'(take_count_4[2*tc5])+6'(take_count_4[2*tc5+1]);
    end endgenerate
    reg [6:0] take_total_6;
    always @(posedge clk) take_total_6<=7'(take_count_5[0])+7'(take_count_5[1]);
    reg [6:0] take_total_7;
    always @(posedge clk) take_total_7<=take_total_6;
    reg [6:0] take_total_8;
    always @(posedge clk) take_total_8<=take_total_7;
    reg [6:0] take_total_9;
    always @(posedge clk) take_total_9<=take_total_8;
    reg [6:0] take_total_10;
    always @(posedge clk) take_total_10<=take_total_9;
    reg [6:0] take_total_11;
    always @(posedge clk) take_total_11<=take_total_10;
    reg [6:0] take_total_12;
    always @(posedge clk) take_total_12<=take_total_11;
    reg [6:0] take_total_13;
    always @(posedge clk) take_total_13<=take_total_12;
    reg [6:0] take_total_14;
    always @(posedge clk) take_total_14<=take_total_13;
    reg [6:0] take_total_15;
    always @(posedge clk) take_total_15<=take_total_14;
    reg [6:0] take_total_16;
    always @(posedge clk) take_total_16<=take_total_15;
    reg [6:0] take_total_17;
    always @(posedge clk) take_total_17<=take_total_16;
    reg [6:0] take_total_18;
    always @(posedge clk) take_total_18<=take_total_17;
    reg [6:0] take_total_19;
    always @(posedge clk) take_total_19<=take_total_18;
    reg [6:0] take_total_20;
    always @(posedge clk) take_total_20<=take_total_19;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; busy <= 1'b0; done <= 1'b0; fault <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0;
            out_nw <= 0; pass <= 0; row <= 0; pk <= 0; stn <= 0; stat_cycles <= 0; nan_seen <= 1'b0;
            wpr <= NMAX / LW; h0_v <= 1'b0; h1_v <= 1'b0; pvalid <= 0;
            {f0_v, f1_v, f2_v, f3_v, f4_v} <= 5'b0;
            for (b = 0; b < NBIN; b = b + 1) cnt[b] <= 0;
        end else begin
            if (!busy) wpr <= (WB+1)'(n / LW);
            if (ld_valid && !ld_id)
                for (ln = 0; ln < LW * LDW; ln = ln + 1) if (isnan(ld_data[32*ln +: 32])) nan_seen <= 1'b1;
            done <= 1'b0; out_valid <= 1'b0; out_last <= 1'b0; out_nw <= 0;
            if (busy) stat_cycles <= stat_cycles + 1;
            h0_v <= (st == S_HIST) && (row < nrow);
            h1_v <= h0_v;
            // Final six-level histogram token is h2_v.
            case (st)
                S_IDLE: if (go) begin
                    if (nan_seen || k == 0 || n == 0 || ((n * N) % P) != 0 || (n % PF) != 0 || n > NMAX || k > n * N) fault <= 1'b1;
                    else begin
                        busy <= 1'b1; stat_cycles <= 0; st <= S_HIST;
                        k_r <= k; n_r <= n; stride_r <= stride; rr <= k;
                        prefix <= 0; pass <= 0; row <= 0;
                        nrow <= (n * N) / P; rpr <= n / P; nfch <= (n * N) / PF; fpr <= n / PF;
                        for (b = 0; b < NBIN; b = b + 1) cnt[b] <= 0;
                    end
                end
                S_HIST: begin
                    if (row < nrow) row <= row + 1'b1;
                    if (h2_v) for (b = 0; b < NBIN; b = b + 1) cnt[b] <= cnt[b] + h2_pc[b];
                    if (row == nrow && !h0_v && !h1_v && !h2_v) begin st <= S_PICK; pk <= 0; end
                end
                S_PICK: begin
                    pk <= pk + 1'b1;
                    if(pk==25) begin
                        pvalid<=choose_root[CB+DIG];
                        if(choose_root[CB+DIG]) begin
                            pbin<=choose_root[CB+DIG-1:CB];pgt<=choose_root[CB-1:0];
                        end
                    end
                    if (pk == 26) begin
                        prefix <= prefix | ({{(32-DIG){1'b0}}, (pbin ^ DIG'(MUTANT==1))} << (sh - DIG));
                        rr <= rr - pgt;
                        for (b = 0; b < NBIN; b = b + 1) cnt[b] <= 0;
                        row <= 0;
                        if (pass == NPASS - 1) begin
                            st <= S_FILT; frow <= 0; frr <= 0; rbase <= 0; stn <= 0;
                            eq_left <= rr - pgt; outw_left <= (k_r + LW - 1) / LW;
                        end else begin
                            pass <= pass + 1'b1; st <= S_HIST;
                        end
                    end
                end
                S_FILT, S_DRAIN: begin
                    // f0: read a row of keys and ids
                    f0_v <= (st == S_FILT) && (frow < nfch);
                    if ((st == S_FILT) && (frow < nfch)) begin
                        f0_k <= kmem[frow / FQ][32*PF*(frow % FQ) +: 32*PF];
                        f0_i <= imem[frow / FQ][32*PF*(frow % FQ) +: 32*PF];
                        f0_base <= rbase;
                        frow <= frow + 1'b1;
                        if (frr == fpr - 1) begin frr <= 0; rbase <= rbase + stride_r; end
                        else frr <= frr + 1'b1;
                    end
                    if (st == S_FILT && frow == nfch) st <= S_DRAIN;
                    // f1: compare with T, global ids
                    f1_v <= f0_v;
                    for (l = 0; l < PF; l = l + 1) begin
                        f1_gt[l] <= f0_k[32*l +: 32] > T;
                        f1_eq[l] <= f0_k[32*l +: 32] == T;
                        f1_id[32*l +: 32] <= f0_base + f0_i[32*l +: 32];
                    end
                    // Fullsource row-order quota feedback after six prefix edges.
                    f2_v<=eq_v_5; f2_id<=eq_id_5;
                    for(l=0;l<PF;l=l+1) begin
                        if(l==0) f2_take[l]<=eq_v_5 && (eq_gt_5[l] || (eq_mask_5[l] && (MUTANT==2 ? CB'(0)<=eq_left : CB'(0)<eq_left)));
                        else f2_take[l]<=eq_v_5 && (eq_gt_5[l] || (eq_mask_5[l] && (MUTANT==2 ? CB'(eq_count_5[l-1])<=eq_left : CB'(eq_count_5[l-1])<eq_left)));
                    end
                    if(eq_v_5) eq_left<=CB'(eq_count_5[PF-1])<eq_left ? eq_left-CB'(eq_count_5[PF-1]) : CB'(0);
                    // Reuse f3 key storage for stable {invalid,original_lane} sorting.
                    f3_v<=f2_v;f3_id<=f2_id;f3_take<=f2_take;
                    for(l=0;l<PF;l=l+1) f3_tp[l]<={!f2_take[l],6'(l)};
                    f3_n<=0; // retained gross-model allowance, not a state credit.
                    f4_v<=sort_valid[19];f4_n<=sort_valid[19]?take_total_20:7'(0);
                    // f5: append at stn; emit OW full words once PF ids are staged (aligned groups), and at the end the
                    // rest, OW words a cycle, the last word zero-padded
                    begin : emit
                        reg [64*PF-1:0] s;
                        reg [SB-1:0] m;
                        reg [$clog2(OW+1)-1:0] w;
                        s = stg; m = stn;
                        if (f4_v && f4_n != 0) begin
                            s = s | ({{(32*PF){1'b0}}, f4_c & ((f4_n == PF) ? {(32*PF){1'b1}} :
                                     (({{(32*PF-1){1'b0}}, 1'b1} << (32 * f4_n)) - 1'b1))} << (32 * m));
                            m = m + f4_n;
                        end
                        w = 0;
                        if (m >= PF) w = OW;
                        else if (st == S_DRAIN && !fpipe && m != 0) w = ($clog2(OW+1))'((m + LW - 1) / LW);
                        if (w != 0) begin
                            out_valid <= 1'b1; out_nw <= w;
                            out_data <= s[32*LW*OW-1:0] & ((m >= SB'(32'(w) * LW)) ?
                                        ((w == OW) ? {(32*LW*OW){1'b1}} :
                                         (({{(32*LW*OW-1){1'b0}}, 1'b1} << (32 * LW * w)) - 1'b1)) :
                                        (({{(32*LW*OW-1){1'b0}}, 1'b1} << (32 * m)) - 1'b1));
                            out_last <= (outw_left == CB'(w));
                            outw_left <= outw_left - CB'(w);
                            s = s >> (32 * LW * w);
                            m = (m >= SB'(32'(w) * LW)) ? m - SB'(32'(w) * LW) : {SB{1'b0}};
                        end
                        stg <= s; stn <= m;
                    end
                    if (st == S_DRAIN && !fpipe && stn == 0 && !out_valid) begin
                        st <= S_IDLE; busy <= 1'b0; done <= 1'b1; nan_seen <= 1'b0;
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
