`timescale 1ns/1ps
// Native clock-owned functional prototype. Slots/clock delivery/parentclosure unqualified.
`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11 (owner textbook audit: the 8-head chunk was 146.7k flops on one clock root, 52k async-reset;
// CTS hold repair stalled at -70 ps with ~48k endpoints in margin): ONE HEAD x ONE KEY of the indexer chunk as a hardened
// slice.  Every slice is identical (one view for all 32 positions of a chunk): the chunk is NKT columns of 8 slices and
// everything travels SYSTOLICALLY down a column on registered seams -- no broadcast across the chunk.
//   * q load: the beat enters at the pin flop, the slice compares its head with its strap hid (a registered pin), writes
//     its own query registers (2 edges, as ot_hdc_v41x_idx_chunk_l) and passes the beat on FPL + 2 edges a hop (as keys).
//   * key: pin flop -> NB block dots + NB-1 sequential block adds -> BF16 -> head-weight product = the head term
//     (LAT_T after the pin flop, exactly the chunk_l arithmetic), and the key passes on FPL + 2 edges a hop, so the next
//     slice's term meets this slice's running sum with no per-position delay.
//   * running sum: pin flop cs_in; first = 1 seeds (term -> FP32, -0 -> +0, delayed FPL like an add), else cs + term
//     (ot_hdc_v41x_faddl); registered out.  Fault ORs along, as chunk_l.
// Pin-to-pin: key_out = key_in + FPL + 2; q_out = q_in + FPL + 2; cs_out = key_in + LAT_T + FPL + 2.
module ot_hbm_idx_hslice_ready_native #(
    parameter integer NB  = 4,
    parameter integer FPL = 7,
    parameter integer FML = 5,
    parameter integer QL  = 5
) (
    input  wire              clk,
    input  wire              rst_n, output reg online,
    input  wire [7:0]        hid,        // absolute head of this slice (strap, registered)
    input  wire              first,      // strap: head 0 of the chunk (seeds the sum)
    // q load in / out
    input  wire              ql_v,
    input  wire [7:0]        ql_head,
    input  wire [NB*128-1:0] ql_codes,
    input  wire [NB*8-1:0]   ql_sc,
    input  wire [15:0]       ql_w,
    output reg               qo_v,
    output reg  [7:0]        qo_head,
    output reg  [NB*128-1:0] qo_codes,
    output reg  [NB*8-1:0]   qo_sc,
    output reg  [15:0]       qo_w,
    // key in / out
    input  wire [NB*136-1:0] k_key,
    output wire [NB*136-1:0] ko_key,
    // running sum in / out
    input  wire [31:0]       cs_in,
    input  wire              cf_in,
    output reg  [31:0]       cs_out,
    output reg               cf_out
);
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    // reset standard: the port drives only the relay
    wire [0:0] srr; wire rs = srr[0];
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(srr));
`ifdef OT_HBM_IDX_READY_MUT_LAX
    always @* online=rst_n;
`else
    // ready2 (B5 10-14): online is cleared by the relay output rs, not by the port, so the rst_n port drives only the
    // relay (3 flops at the N face).  Assert stays asynchronous (rs is cleared asynchronously by the port), release was
    // already gated by rs && rn_p: cycle-identical.  The port -> online clear crossed the tile to the S face (native
    // audit capture 215.5 ps on rst_n, > 190).
    always @(posedge clk or negedge rs)
      if (!rs) online<=1'b0; else online<=rs && rn_p;
`endif
    // ---- pin flops
    reg rn_p; reg [7:0] hid_p; reg first_p;
    reg qv_p; reg [7:0] qh_p; reg [NB*128-1:0] qc_p; reg [NB*8-1:0] qs_p; reg [15:0] qw_p;
    reg [KW-1:0] key_p; reg [31:0] csi_p; reg cfi_p;
    always @(posedge clk) begin
        rn_p <= rs; hid_p <= hid; first_p <= first;
        qv_p <= ql_v && rn_p; qh_p <= ql_head; qc_p <= ql_codes; qs_p <= ql_sc; qw_p <= ql_w;
        key_p <= k_key; csi_p <= cs_in; cfi_p <= cf_in;
    end
    // ---- q load: own head written one edge after the compare; beat passed on registered
    reg q_we; reg [NB*128-1:0] q2c; reg [NB*8-1:0] q2s; reg [15:0] q2w;
    reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
    always @(posedge clk) begin
        q_we <= qv_p && rn_p && (qh_p == hid_p);
        q2c <= qc_p; q2s <= qs_p; q2w <= qw_p;
        if (q_we) begin qc <= q2c; qs <= q2s; qw <= q2w; end
    end
    // the q beat passes on FPL + 2 pin to pin, the same as a key, so q loads and keys keep their input order at every
    // slice (a key sees exactly the query it would have seen in chunk_l)
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    wire [QW-1:0] qb_d; wire qv_d;
    ot_hdc_delay #(.W(QW), .D(FPL)) u_qp (.clk(clk), .rst_n(1'b1), .d({qh_p, qc_p, qs_p, qw_p}), .q(qb_d));
    ot_hdc_delay #(.W(1), .D(FPL), .RESET(1)) u_qv (.clk(clk), .rst_n(rs), .d(qv_p && rn_p), .q(qv_d));
    always @(posedge clk) begin
        qo_v <= qv_d && rn_p; {qo_head, qo_codes, qo_sc, qo_w} <= qb_d;
    end
    // ---- key pass-through: FPL + 2 pin to pin (pin flop + FPL + output flop)
    wire [KW-1:0] key_d;
    ot_hdc_delay #(.W(KW), .D(FPL)) u_kp (.clk(clk), .rst_n(1'b1), .d(key_p), .q(key_d));
    reg [KW-1:0] key_o;
    always @(posedge clk) key_o <= key_d;
    assign ko_key = key_o;
    // ---- the head term (chunk_l g_head arithmetic, unchanged)
    wire [NB*128-1:0] kc; wire [NB*8-1:0] ks;
    genvar bb;
    generate for (bb = 0; bb < NB; bb = bb + 1) begin : g_skew
        localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
        wire [135:0] kb_d;
        ot_hdc_delay #(.W(136), .D(DS)) u_sk (.clk(clk), .rst_n(1'b1),
            .d({key_p[NB*128 + 8*bb +: 8], key_p[128*bb +: 128]}), .q(kb_d));
        assign kc[128*bb +: 128] = kb_d[127:0];
        assign ks[8*bb +: 8] = kb_d[135:128];
    end endgenerate
    wire [NB*32-1:0] acc; wire [NB-1:0] afault;
    generate for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
        wire [31:0] bv; wire bo;
        ot_hdc_v41x_q4dot_l #(.QL(QL)) u_d (.clk(clk), .a(qc[bb*128 +: 128]), .b(kc[128*bb +: 128]),
                               .ua(qs[bb*8 +: 8]), .ub(ks[8*bb +: 8]), .y(bv), .ovf(bo));
        if (bb == 0) begin : g_first
            assign acc[31:0] = bv; assign afault[0] = bo;
        end else begin : g_add
            wire [1:0] err; wire vo_unused; wire pf, bo_d;
            ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(afault[bb-1]), .q(pf));
            ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rs), .valid_in(1'b1),
                .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
            ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(clk), .rst_n(1'b1), .d(bo), .q(bo_d));
            assign afault[bb] = pf || bo_d || (err != 2'd0);
        end
    end endgenerate
    wire [15:0] sc16; wire sco;
    ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
    reg [15:0] rsc; reg rscf;
    always @(posedge clk) begin rsc <= sc16; rscf <= afault[NB-1] || sco; end
    wire [15:0] tm; wire tmo, rscf_d;
    ot_hdc_v41x_bmul_l #(.ML(FML)) u_m (.clk(clk), .a(rsc), .w(qw), .y(tm), .ovf(tmo));
    ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(clk), .rst_n(1'b1), .d(rscf), .q(rscf_d));
    wire tf = rscf_d || tmo;
    // ---- running sum: the term is formed LAT_T after key_p, when cs_in (pin flopped) arrives
    wire [1:0] err; wire vo_unused;
    wire [31:0] sum;
    ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rs), .valid_in(1'b1),
        .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
    wire [32:0] seed_d;
    ot_hdc_delay #(.W(33), .D(FPL)) u_sd (.clk(clk), .rst_n(1'b1),
        .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
    wire pf;
    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
    always @(posedge clk) begin
        cs_out <= first_p ? seed_d[31:0] : sum;
        cf_out <= first_p ? seed_d[32] : (pf || (err != 2'd0));
    end
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_idx_chunk_owned_native (
    input wire clk, input wire [31:0] clk_hslice,
    input  wire                  rst_n,
    input  wire [7:0]            hb,
    input  wire                  ql_v,
    input  wire [7:0]            ql_head,
    input  wire [NB*128-1:0]     ql_codes,
    input  wire [NB*8-1:0]       ql_sc,
    input  wire [15:0]           ql_w,
    input  wire                  k_v,
    input  wire [NKT-1:0]        k_kv,
    input  wire [NKT*NB*136-1:0] k_key,
    output reg                   c_v,
    output reg  [NKT-1:0]        c_kv,
    output reg  [NKT*32-1:0]     c_sum,
    output reg  [NKT-1:0]        c_fault
, output reg online
);
 localparam integer NB=4,NKT=4,FPL=7,FML=5,QL=5;

    wire [31:0] hrdy; reg [31:0] rdy1,rdy2;
    always @(posedge clk or negedge rst_n)
      if(!rst_n)begin rdy1<=0;rdy2<=0;online<=0;end
      else begin rdy1<=hrdy;rdy2<=rdy1;online<=(&rdy2);end
    localparam integer HC = 8;
    localparam integer KW = NB * 136;
    localparam integer LAT_SC = QL + FPL * (NB - 1);
    localparam integer LAT_T  = LAT_SC + 1 + FML;
    localparam integer XLAT   = FPL + 16;
    localparam integer LATE   = LAT_T + FPL * (HC - 1) + XLAT;   // input register -> output register
    wire [NKT:0] rr;
    ot_rst_relay #(.REGIONS(NKT + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[NKT];
    // input registers
    reg rql_v; reg [7:0] rql_head; reg [NB*128-1:0] rql_codes; reg [NB*8-1:0] rql_sc; reg [15:0] rql_w;
    reg rv; reg [NKT-1:0] rkv; reg [NKT*KW-1:0] rkey; reg [7:0] hb_p; reg [7:0] hid [0:HC-1];
    integer i;
    always @(posedge clk) begin
        rql_v <= ql_v && rn; rql_head <= ql_head; rql_codes <= ql_codes; rql_sc <= ql_sc; rql_w <= ql_w;
        rv <= k_v && rn; rkv <= k_kv; rkey <= k_key; hb_p <= hb;
        for (i = 0; i < HC; i = i + 1) hid[i] <= hb_p + 8'(i);
    end
    wire [NKT:0] vl;
    ot_hdc_delay #(.W(NKT + 1), .D(LATE), .RESET(1)) u_vl (.clk(clk), .rst_n(rn), .d({rkv, rv}), .q(vl));
    genvar g, h;
    generate for (g = 0; g < NKT; g = g + 1) begin : g_col
        wire qv [0:HC]; wire [7:0] qh [0:HC]; wire [NB*128-1:0] qc [0:HC]; wire [NB*8-1:0] qs [0:HC]; wire [15:0] qw [0:HC];
        wire [KW-1:0] ky [0:HC]; wire [31:0] cs [0:HC]; wire cf [0:HC];
        assign qv[0] = rql_v; assign qh[0] = rql_head; assign qc[0] = rql_codes; assign qs[0] = rql_sc; assign qw[0] = rql_w;
        assign ky[0] = rkey[g*KW +: KW]; assign cs[0] = 32'd0; assign cf[0] = 1'b0;
        for (h = 0; h < HC; h = h + 1) begin : g_s
`ifdef OT_IDX_HSLICE_HARD
            ot_hbm_idx_hslice_ready_native u_s (.clk(clk_hslice[8*g+h]),
`else
            ot_hbm_idx_hslice_ready_native #(.NB(NB), .FPL(FPL), .FML(FML), .QL(QL)) u_s (.clk(clk_hslice[8*g+h]),
`endif .rst_n(rr[g]), .online(hrdy[8*g+h]), .hid(hid[h]), .first(h == 0),
                .ql_v(qv[h]), .ql_head(qh[h]), .ql_codes(qc[h]), .ql_sc(qs[h]), .ql_w(qw[h]),
                .qo_v(qv[h+1]), .qo_head(qh[h+1]), .qo_codes(qc[h+1]), .qo_sc(qs[h+1]), .qo_w(qw[h+1]),
                .k_key(ky[h]), .ko_key(ky[h+1]), .cs_in(cs[h]), .cf_in(cf[h]), .cs_out(cs[h+1]), .cf_out(cf[h+1]));
        end
        always @(posedge clk) begin c_sum[32*g +: 32] <= cs[HC]; c_fault[g] <= cf[HC]; end
    end endgenerate
    always @(posedge clk) begin c_v <= vl[0] && rn; c_kv <= vl[NKT:1]; end
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_idx_tail_native (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  i_v,
    input  wire [NKT-1:0]        i_kv,
    input  wire [NKT-1:0]        i_keep,
    input  wire [NKT*NCH*32-1:0] i_sum,     // key g, chunk c at [(g*NCH+c)*32 +: 32]
    input  wire [NKT*NCH-1:0]    i_fault,
    output reg                   o_v,
    output reg  [NKT-1:0]        o_kv,
    output reg  [NKT*16-1:0]     o_score,
    output reg  [NKT-1:0]        o_fault

);
 localparam integer NCH=4,NKT=4,FPL=7;

    localparam integer LV = (NCH <= 1) ? 0 : $clog2(NCH);
    reg                  rv;
    reg [NKT-1:0]        rkv, rkeep;
    reg [NKT*NCH*32-1:0] rsum;
    reg [NKT*NCH-1:0]    rf;
    always @(posedge clk) begin
        rv <= i_v && rst_n;
        rkv <= i_kv;
        rkeep <= i_keep;
        rsum <= i_sum;
        rf <= i_fault;
    end
    wire [2*NKT:0] vl;
    ot_hdc_delay #(.W(2 * NKT + 1), .D(FPL * LV), .RESET(1)) u_vl (.clk(clk), .rst_n(rst_n),
        .d({rkeep, rkv, rv}), .q(vl));
    genvar g, l, i;
    generate
        for (g = 0; g < NKT; g = g + 1) begin : g_key
            // level l holds NCH >> l partial sums
            // level l, partial i at index l * NCH + i
            wire [(LV+1)*NCH*32-1:0] t;
            wire [(LV+1)*NCH-1:0]    tf;
            for (i = 0; i < NCH; i = i + 1) begin : g_in
                assign t[32*i +: 32] = rsum[(g * NCH + i) * 32 +: 32];
                assign tf[i] = rf[g * NCH + i];
            end
            for (l = 0; l < LV; l = l + 1) begin : g_lv
                for (i = 0; i < (NCH >> (l + 1)); i = i + 1) begin : g_add
                    wire [1:0] err;
                    wire       vo_unused;
                    ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(1'b1),
                        .a(t[32*(l*NCH+2*i) +: 32]), .b(t[32*(l*NCH+2*i+1) +: 32]),
                        .y(t[32*((l+1)*NCH+i) +: 32]), .err(err), .valid_out(vo_unused));
                    wire pf;
                    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(rst_n),
                        .d(tf[l*NCH+2*i] || tf[l*NCH+2*i+1]), .q(pf));
                    assign tf[(l+1)*NCH+i] = pf || (err != 2'd0);
                end
            end
            wire [15:0] s16;
            wire        so;
            ot_hdc_v41x_bf16 u_b (.x(t[32*LV*NCH +: 32]), .y(s16), .ovf(so));
            always @(posedge clk) begin
                o_fault[g] <= tf[LV*NCH] || so;
                o_score[16*g +: 16] <= (tf[LV*NCH] || so) ? 16'd0 : (vl[1 + NKT + g] ? s16 : 16'hFF80);
            end
        end
    endgenerate
    always @(posedge clk) begin
        o_v <= vl[0] && rst_n;
        o_kv <= vl[NKT:1];
    end
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_idx_engine_state_native (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 ql_v,




    input  wire                 k_valid,
    output wire                 k_ready,
    input  wire [NK-1:0]        k_kv,
    input  wire [NK-1:0]        k_keep,

    output reg                  o_valid,
    input  wire                 o_ready,
    output reg  [NK-1:0]        o_kv,
    output reg  [NK*16-1:0]     o_score,
    output reg  [NK-1:0]        o_fault,
    // activation counters (since reset; for the benches): keys scored (score
    // slots delivered), head terms fused (ReLU x weight terms summed inside the
    // engine: IH per scored key), keys whose score faulted
    output reg  [47:0]          cnt_keys_scored,
    output reg  [47:0]          cnt_headsums_fused,
    output reg  [47:0]          cnt_faults
, input wire [3:0] chunks_online, output reg online, input wire tv, input wire [3:0] tkv,tf, input wire [63:0] ts,
 output wire take, output wire [3:0] keep_d
);
 localparam integer NK=4,IH=32,NB=4,FD=128,FPL=7,FML=5,QL=5;

    localparam integer NCH = IH / 8;
    localparam integer LVT = (NCH <= 1) ? 0 : $clog2(NCH);
    localparam integer XLAT = FPL + 16;
    localparam integer LAT_C = 1 + QL + FPL * (NB - 1) + 1 + FML + FPL * 7 + 1 + XLAT;   // chunk in-reg .. out-reg
    localparam integer LAT_T = 1 + FPL * LVT + 1;
    localparam integer LAT = LAT_C + LAT_T;                              // k beat -> tail output
    localparam integer FDE = (FD >= LAT + 2) ? FD : (1 << $clog2(LAT + 2));   // effective FIFO depth
    localparam integer CW = $clog2(FDE + 1);

    assign take = k_valid && k_ready;


    ot_hdc_delay #(.W(NK), .D(LAT_C)) u_keep (.clk(clk), .rst_n(rst_n), .d(k_keep), .q(keep_d));
    // output FIFO behind a registered output; a beat bypasses the FIFO when it
    // is empty and the output register is free.  Credit: beats in flight plus
    // beats in the FIFO plus the output register stay within FD.
    localparam integer EW = NK * 18;
    localparam integer PW = (FDE <= 2) ? 1 : $clog2(FDE);
    reg [EW-1:0] fm [0:FDE-1];
    reg [CW-1:0] fcnt, infl;
    reg [PW-1:0] wp, rp;
    wire deq = o_valid && o_ready;
    integer ck;
    reg [$clog2(NK+1)-1:0] nk_out, nf_out;
    always @* begin
        nk_out = 0; nf_out = 0;
        for (ck = 0; ck < NK; ck = ck + 1) begin
            nk_out = nk_out + o_kv[ck];
            nf_out = nf_out + (o_kv[ck] & o_fault[ck]);
        end
    end
    always @(posedge clk)
        if (!rst_n) begin
            cnt_keys_scored <= 0; cnt_headsums_fused <= 0; cnt_faults <= 0;
        end else if (deq) begin
            cnt_keys_scored <= cnt_keys_scored + nk_out;
            cnt_headsums_fused <= cnt_headsums_fused + nk_out * IH;
            cnt_faults <= cnt_faults + nf_out;
        end
    reg [3:0] rdy1,rdy2;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin rdy1<=0;rdy2<=0;online<=0;end
      else begin rdy1<=chunks_online;rdy2<=rdy1;online<=(&rdy2);end
    wire out_free = !o_valid || o_ready;
    wire from_fifo = (fcnt != 0) && out_free;
    wire bypass = tv && (fcnt == 0) && out_free;
    wire push = tv && !bypass;
    // a q-load beat reaches the query registers 3 edges after it is presented
    // (tile input register, enable register, write); keys wait for it
    reg [1:0] qsettle;
    always @(posedge clk)
        if (!rst_n) qsettle <= 2'd0;
        else if (ql_v) qsettle <= 2'd3;
        else if (qsettle != 0) qsettle <= qsettle - 2'd1;
    assign k_ready = rst_n && online && !ql_v && (qsettle == 0) && ((infl + fcnt + (o_valid ? 1 : 0)) < FDE);
    always @(posedge clk) begin
        if (!rst_n) begin
            fcnt <= 0; infl <= 0; wp <= 0; rp <= 0; o_valid <= 1'b0;
        end else begin
            infl <= infl + (take ? 1 : 0) - (tv ? 1 : 0);
            if (push) begin
                fm[wp] <= {tf, tkv, ts};
                wp <= (wp == FDE - 1) ? 0 : wp + 1;
            end
            fcnt <= fcnt + (push ? 1 : 0) - (from_fifo ? 1 : 0);
            if (from_fifo) begin
                {o_fault, o_kv, o_score} <= fm[rp];
                rp <= (rp == FDE - 1) ? 0 : rp + 1;
                o_valid <= 1'b1;
            end else if (bypass) begin
                {o_fault, o_kv, o_score} <= {tf, tkv, ts};
                o_valid <= 1'b1;
            end else if (deq) o_valid <= 1'b0;
        end
    end
endmodule
module ot_hbm_idx_engine_owned_native #(parameter integer MUT=0)(
    input wire clk, input wire clk_tail, input wire [3:0] clk_chunk, input wire [127:0] clk_hslice,
    input  wire                 rst_n,
    input  wire                 ql_v,
    input  wire [7:0]           ql_head,
    input  wire [NB*128-1:0]    ql_codes,
    input  wire [NB*8-1:0]      ql_sc,
    input  wire [15:0]          ql_w,
    input  wire                 k_valid,
    output wire                 k_ready,
    input  wire [NK-1:0]        k_kv,
    input  wire [NK-1:0]        k_keep,
    input  wire [NK*NB*136-1:0] k_key,
    output wire                  o_valid,
    input  wire                 o_ready,
    output wire  [NK-1:0]        o_kv,
    output wire  [NK*16-1:0]     o_score,
    output wire  [NK-1:0]        o_fault,
    // activation counters (since reset; for the benches): keys scored (score
    // slots delivered), head terms fused (ReLU x weight terms summed inside the
    // engine: IH per scored key), keys whose score faulted
    output wire  [47:0]          cnt_keys_scored,
    output wire  [47:0]          cnt_headsums_fused,
    output wire  [47:0]          cnt_faults
, output wire online
);
 localparam integer NK=4,IH=32,NB=4,NCH=4,FPL=7,FML=5,QL=5;
 wire take;wire[3:0]keep_d,chunks_online;
    // chunks
    wire [NCH-1:0]        cv;
    wire [NK-1:0]         ckv [0:NCH-1];
    wire [NK*32-1:0]      csum [0:NCH-1];
    wire [NK-1:0]         cfl [0:NCH-1];
    genvar c, g;
    generate
        for (c = 0; c < NCH; c = c + 1) begin : g_ch
            ot_hbm_idx_chunk_owned_native u_c (
                .clk(clk_chunk[c]), .clk_hslice(clk_hslice[32*c+:32]), .rst_n(rst_n), .hb(8'(8 * ((MUT == 1) ? (c ^ 1) : ((MUT == 2 && c == 0) ? 1 : c)))), .ql_v(ql_v), .ql_head(ql_head), .ql_codes(ql_codes), .ql_sc(ql_sc),
                .ql_w(ql_w), .k_v(take), .k_kv(k_kv), .k_key(k_key),
                .online(chunks_online[c]), .c_v(cv[c]), .c_kv(ckv[c]), .c_sum(csum[c]), .c_fault(cfl[c]));
        end
    endgenerate
    wire [NK*NCH*32-1:0] tsum;
    wire [NK*NCH-1:0] tfl;
    for(genvar gi=0;gi<NK;gi=gi+1)begin:g_transpose
      for(genvar ci=0;ci<NCH;ci=ci+1)begin:g_chunk
        assign tsum[(gi*NCH+ci)*32+:32]=csum[ci][32*gi+:32];
        assign tfl[gi*NCH+ci]=cfl[ci][gi];
      end
    end
    wire              tv;
    wire [NK-1:0]     tkv, tf;
    wire [NK*16-1:0]  ts;
    ot_hbm_idx_tail_native u_t (.clk(clk_tail), .rst_n(rst_n), .i_v(cv[0]), .i_kv(ckv[0]),
        .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));

    ot_hbm_idx_engine_state_native u_state(
        .clk(clk),
        .rst_n(rst_n),
        .ql_v(ql_v),
        .k_valid(k_valid),
        .k_ready(k_ready),
        .k_kv(k_kv),
        .k_keep(k_keep),
        .o_valid(o_valid),
        .o_ready(o_ready),
        .o_kv(o_kv),
        .o_score(o_score),
        .o_fault(o_fault),
        .cnt_keys_scored(cnt_keys_scored),
        .cnt_headsums_fused(cnt_headsums_fused),
        .cnt_faults(cnt_faults),
        .chunks_online(chunks_online),
        .online(online),
        .tv(tv),
        .tkv(tkv),
        .ts(ts),
        .take(take),
        .keep_d(keep_d),
        .tf(tf)
    );
endmodule
(* keep_hierarchy="yes" *) module ot_hbm_idx_slice_owned_native #(parameter integer MUT=0)(
    input wire clk, rst_n, input wire clk_engine,clk_tail, input wire[3:0]clk_chunk,input wire[127:0]clk_hslice,
    input wire ql_v,
    output wire ql_ready,
    input wire [7:0] ql_head,
    input wire [NB*128-1:0] ql_codes,
    input wire [NB*8-1:0] ql_sc,
    input wire [15:0] ql_w,
    input wire i_valid,
    output wire i_ready,
    input wire i_last,
    input wire [IW-1:0] i_first_index,
    input wire [NK-1:0] i_kv,
    input wire [NK-1:0] i_ref,
    input wire [NK-1:0] i_keep,
    input wire [NK*NB*136-1:0] i_key,
    output wire o_valid,
    input wire o_ready,
    output wire o_last,
    output wire [NK-1:0] o_kv,
    output wire [NK*16-1:0] o_score,
    output wire [NK*IW-1:0] o_index,
    output wire [NK-1:0] o_fault

);
 localparam integer NK=4,NB=4,IH=32,IW=20,MD=64,FPL=7,FML=5,QL=5,ARRAY_PHASE_GATE=1;
    wire engine_online; reg rdy1,rdy2;
    always @(posedge clk or negedge rst_n)if(!rst_n)begin rdy1<=0;rdy2<=0;end else begin rdy1<=engine_online;rdy2<=rdy1;end

    // the engine's key-to-score latency; a queue shallower than it + 4 would
    // throttle the stream, so MD is deepened to the next power of two (no change
    // at FPL = FML = QL = 3: latency 47 at NB = 4, IH = 32)
    localparam integer LVE=(IH/8<=1)?0:$clog2(IH/8);
    localparam integer LATE=23+(1+QL+FPL*(NB-1)+1+FML+FPL*7+1)+(1+FPL*LVE+1);
    localparam integer MDE=(MD>=LATE+4)?MD:(1<<$clog2(LATE+4));
    localparam integer PW=$clog2(MDE), CW=$clog2(MDE+1);
    reg [IW+NK:0] meta [0:MDE-1]; // {last, first_index, refused mask}
    reg [PW-1:0] wr,rd;
    reg [CW-1:0] count;
    wire ev,er;
    wire [NK-1:0] ekv,ef;
    wire [NK*16-1:0] es;
    wire take=i_valid && i_ready;
    wire pop=o_valid && o_ready;
    // Query SRAM is single-buffered. A new query may overwrite it only after
    // all earlier score beats leave both the engine and metadata queue.
    assign ql_ready=rdy2 && (count==0) && !ev && (ARRAY_PHASE_GATE || !i_valid);
    assign i_ready=er && count<MDE;
    assign o_valid=ev && count!=0;
    assign o_last=meta[rd][IW+NK];
    assign o_kv=ekv;
    assign o_fault=ef | meta[rd][NK-1:0];
    wire [IW-1:0] first_index=meta[rd][IW+NK-1:NK];
    genvar g;
    generate for(g=0;g<NK;g=g+1) begin:g_idx
        localparam [IW-1:0] OFFSET=g;
        assign o_index[g*IW +: IW]=first_index+OFFSET;
        assign o_score[g*16 +: 16]=meta[rd][g] ? 16'd0 : es[g*16 +: 16];
    end endgenerate
    ot_hbm_idx_engine_owned_native #(.MUT(MUT)) engine (
        .clk(clk_engine),.clk_tail(clk_tail),.clk_chunk(clk_chunk),.clk_hslice(clk_hslice),.online(engine_online),.rst_n(rst_n),.ql_v(ql_v && ql_ready),.ql_head(ql_head),
        .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
        .k_valid(take),.k_ready(er),.k_kv(i_kv),.k_keep(i_keep),.k_key(i_key),
        .o_valid(ev),.o_ready(pop),.o_kv(ekv),.o_score(es),.o_fault(ef),
        .cnt_keys_scored(),.cnt_headsums_fused(),.cnt_faults());
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin wr<=0;rd<=0;count<=0;end
        else begin
            if(take) begin
                meta[wr]<={i_last,i_first_index,i_ref};
                wr<=wr+1'b1;
            end
            if(pop) rd<=rd+1'b1;
            case({take,pop})
                2'b10:count<=count+1'b1;
                2'b01:count<=count-1'b1;
                default:count<=count;
            endcase
        end
    end
`ifndef SYNTHESIS
    always @(posedge clk) if(rst_n && ql_v && !ql_ready)
        $fatal(1,"index score query overwrite while prior scores are in flight");
`endif
endmodule
module ot_hbm_idx_array_owned_native #(parameter integer NS=4,MUT=0)(
    input wire clk, input wire[NS-1:0]clk_engine,clk_meta,clk_tail,input wire[NS*4-1:0]clk_chunk,input wire[NS*128-1:0]clk_hslice,
    input  wire                     rst_n,
    // q load, broadcast: one head per cycle
    input  wire                     ql_v,
    output wire                     ql_ready,
    input  wire [7:0]               ql_head,
    input  wire [NB*128-1:0]        ql_codes,
    input  wire [NB*8-1:0]          ql_sc,
    input  wire [15:0]              ql_w,
    // key beat: NS*NK slots
    input  wire                     i_valid,
    output wire                     i_ready,
    input  wire [NS-1:0]            i_last,
    input  wire [NS*NK-1:0]         i_kv,
    input  wire [NS*NK-1:0]         i_ref,
    input  wire [NS*NK-1:0]         i_keep,
    input  wire [NS*NK*IW-1:0]      i_index,
    input  wire [NS*NK*NB*136-1:0]  i_key,
    // score beat to the selector port: NS*NK slots in beat order
    output wire                     o_valid,
    input  wire                     o_ready,
    output wire [NS-1:0]            o_last,
    output wire [NS*NK-1:0]         o_kv,
    output wire [NS*NK-1:0]         o_fault,
    output wire [NS*NK*16-1:0]      o_score,
    output wire [NS*NK*IW-1:0]      o_index,
    output wire                     protocol_fault

);
 localparam integer NK=4,NB=4,IH=32,IW=20,MD=64,FPL=7,FML=5,QL=5,SAFE_QUERY_GATE=1;

    localparam integer KW = NB * 136;
    wire [NS-1:0] sr, sv, qr;
    wire take = i_valid && i_ready;
    wire consume = o_valid && o_ready;
    assign i_ready = &sr;
    assign ql_ready = (&qr) && (!SAFE_QUERY_GATE || !i_valid);
    wire slice_ql_v = ql_v && (!SAFE_QUERY_GATE || !i_valid);
    assign o_valid = &sv;
    assign protocol_fault = (|sv && !(&sv)) || ((&sv) && o_last != {NS{o_last[0]}});

    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_slice
        ot_hbm_idx_slice_owned_native #(.MUT(MUT)) u (
            .clk(clk_meta[s]), .clk_engine(clk_engine[s]),.clk_tail(clk_tail[s]),.clk_chunk(clk_chunk[4*s+:4]),.clk_hslice(clk_hslice[128*s+:128]), .rst_n(rst_n),
            .ql_v(slice_ql_v), .ql_ready(qr[s]), .ql_head(ql_head),
            .ql_codes(ql_codes), .ql_sc(ql_sc), .ql_w(ql_w),
            .i_valid(take), .i_ready(sr[s]), .i_last(i_last[s]),
            .i_first_index(i_index[s*NK*IW +: IW]),
            .i_kv(i_kv[s*NK +: NK]), .i_ref(i_ref[s*NK +: NK]), .i_keep(i_keep[s*NK +: NK]),
            .i_key(i_key[s*NK*KW +: NK*KW]),
            .o_valid(sv[s]), .o_ready(consume), .o_last(o_last[s]),
            .o_kv(o_kv[s*NK +: NK]), .o_fault(o_fault[s*NK +: NK]),
            .o_score(o_score[s*NK*16 +: NK*16]),
            .o_index(o_index[s*NK*IW +: NK*IW]));
    end endgenerate

`ifndef SYNTHESIS
    // consecutive indices inside each slice group (valid slots only)
    integer cs, cg;
    always @(posedge clk) if (rst_n && take)
        for (cs = 0; cs < NS; cs = cs + 1)
            for (cg = 1; cg < NK; cg = cg + 1)
                if (i_kv[cs*NK + cg] &&
                    i_index[(cs*NK + cg)*IW +: IW] != i_index[cs*NK*IW +: IW] + cg)
                    $fatal(1, "idx array: slice %0d slot %0d index not consecutive", cs, cg);
    always @(posedge clk) if (rst_n && protocol_fault)
        $fatal(1, "idx array: slices out of step");
`endif
endmodule
