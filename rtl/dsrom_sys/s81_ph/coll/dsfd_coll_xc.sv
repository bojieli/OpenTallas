`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_coll_xc (s81-die-rtl-bind 2026-10-14, die item F2): the collective slab's DIE-CLIENT ADAPTER tile.  It sits
// between the slab's VM-facing pins and the closed VM-side core tile (dsfd_coll_cb / cbj), on the VM interface of
// the core (f_vm / ts / t_vm, contract results/rtl/s81_ph_20261006/collective/contract.json), and gives the three
// die clients the die contract wires to the collective their own ports -- without touching any closed core / lane tile:
//
//  (1) HC y bus (su_hc contract v2: "HC y 8,192 from the collective (valid / ready)").  Every all-reduce result word the
//      core sends to the VM (t_vm engine beat, type 1, not a gather beat, word mask [9:6]) is ALSO packed, in order, 16
//      words a beat (NG 256 x FP32 = one HC y beat), onto t_hc_y / t_hc_yv; f_hc_yr is the HC's ready (its y skid).
//      The VM still receives every word (unchanged t_vm traffic).  Packing: a 16-word assembly row + a YR-deep row FIFO.
//      A message whose last word does not end a 16-word row is a FAULT (the HC y beat is never partial).
//  (2) WFC kit link (stage hop): the kit's link out (f_wfc = {last, data 512, valid}, grant t_wfcg back; receiver =
//      ot_dsrom_mtp_lrx) is injected into the core as pass-through flits (f_vm type 2) on the stage-hop-out channel; the
//      pass-through flits the core receives on the stage-hop-in channel go to the kit's link in (t_wfc, grant f_wfcg
//      from the kit; sender = ot_dsrom_mtp_ltx) instead of the VM.
//  (3) Host channel (layer-die ingest dsfd_host_c): pass-through flits received on the host channel go to the host
//      (t_host = {t_cr, h_cls 2, h_d 512, h_v} from flit data [514:0]); the host's return word f_host = {st 11, h_crn 5,
//      t_v, t_d 64} is sent back on the host channel as flits {st 11, crn 5, cv, cd 64} (credits accumulated, one
//      completion word a flit, status level), whenever credits / completions are pending or the status changed.
// Channel assignment (the VM program's, contract "pass-through channels 0..4"): the core's config word (f_vm type 3,
// data[1:0] rank, [2] engine enable) carries the adapter's fields, latched here when the word passes:
//   data[3] y enable, data[4] hop enable, data[7:5] hop-in channel, data[10:8] hop-out channel, data[11] host enable,
//   data[14:12] host channel.  Disabled functions leave the VM traffic exactly as without this tile.
// Credits / flow control.  Injected flits use the core's pass-through queue credits (q1..q5: QD 8 each, returned in
//   every t_vm header [40:17]); the VM program never sends on a channel this tile owns (a VM flit on an owned channel
//   is a FAULT).  A diverted beat still reaches the VM as a STATUS beat (type 3, data 0) so its header credits / fault
//   are never lost.  The core may only emit a t_vm beat while ts[0] = 1; this tile ANDs the VM's ts[0] with its own
//   room (y rows, hop-in FIFO) for M in-flight beats (ts -> t_vm round trip through the core <= M).  Overflow of any
//   queue is a sticky FAULT (never a silent drop), ORed into t_vm[41] (the slab fault the VM collects; one status beat of its own when the core is idle).
// Cycles: f_vm +1 (this tile's pin register), t_vm +1, ts +1 (priced 0: the VM credit loops have QD slack).
// MUT (negative controls, bench only): 1 y words out of order (word 1 / 2 of every beat swapped), 2 hop-in flits
// dropped when the kit grant is low (no FIFO), 3 host credits not returned (crn forced 0).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_coll_xc #(
    parameter integer NG = 256,                 // HC groups: one y beat = NG x 32 b
    parameter integer YR = 4,                   // y row FIFO depth (rows of NG/16 words)
    parameter integer M = 8,                    // ts -> t_vm in-flight beats (room margin)
    parameter integer HD = 16,                  // hop-in FIFO depth (flits)
    parameter integer KD = 8,                   // hop-out receive FIFO (kit -> coll grant protocol)
    parameter integer CD = 16,                  // host completion FIFO depth
    parameter integer QD = 8,                   // core pass-through queue credits per channel
    parameter integer MUT = 0
) (
    input  wire [0:0]       ck,
    input  wire [0:0]       rst,
    // VM side (die pins of the slab)
    input  wire [591:0]     f_vm,
    input  wire [2:0]       ts,
    output reg  [2099:0]    t_vm,
    // core side (dsfd_coll_cb / cbj S face)
    output reg  [591:0]     c_fvm,
    output reg  [2:0]       c_ts,
    input  wire [2099:0]    c_tvm,
    // HC y bus
    output wire [NG*32-1:0] t_hc_y,
    output wire [0:0]       t_hc_yv,
    input  wire [0:0]       f_hc_yr,
    // WFC kit link: in = to the kit (data {last, data 512}, valid at [0]), out = from the kit
    output wire [513:0]     t_wfc,
    input  wire [0:0]       f_wfcg,
    input  wire [513:0]     f_wfc,
    output wire [0:0]       t_wfcg,
    // host channel
    output reg  [515:0]     t_host,
    input  wire [80:0]      f_host
);
    localparam integer YW = NG / 16;            // 512-b words per y beat (16 at NG 256)
    localparam integer YB = $clog2(YW + 1);
    wire clk = ck[0];
    reg [1:0] rs_q;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    // ---------------- pin registers
    reg [591:0] fv_q; reg [2:0] ts_q; reg [2099:0] tv_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin fv_q <= 0; ts_q <= 0; tv_q <= 0; end
        else begin fv_q <= f_vm; ts_q <= ts; tv_q <= c_tvm; end
    // ---------------- configuration (snooped from the config word on its way to the core)
    reg y_en, hop_en, host_en; reg [2:0] hop_in, hop_out, host_ch;
    wire fv_v = fv_q[0]; wire [1:0] fv_type = fv_q[2:1]; wire [2:0] fv_link = fv_q[5:3]; wire [551:0] fv_d = fv_q[591:40];
    always @(posedge clk or negedge rn)
        if (!rn) begin y_en <= 0; hop_en <= 0; host_en <= 0; hop_in <= 0; hop_out <= 0; host_ch <= 0; end
        else if (fv_v && fv_type == 2'd3) begin
            y_en <= fv_d[3]; hop_en <= fv_d[4]; hop_in <= fv_d[7:5]; hop_out <= fv_d[10:8];
            host_en <= fv_d[11]; host_ch <= fv_d[14:12];
        end
    wire own_vm = fv_v && fv_type == 2'd2 && ((hop_en && fv_link == hop_out) || (host_en && fv_link == host_ch));
    // ---------------- core output beat decode
    wire        b_v    = tv_q[0];
    wire [1:0]  b_type = tv_q[2:1];
    wire [2:0]  b_link = tv_q[5:3];
    wire [3:0]  b_mask = tv_q[9:6];
    wire [3:0]  b_last = tv_q[13:10];
    wire        b_plst = tv_q[14];
    wire        b_gat  = tv_q[15];
    wire [551:0] b_flit = tv_q[52 +: 552];
    wire        is_red = b_v && b_type == 2'd1 && !b_gat;
    wire        is_hop = b_v && b_type == 2'd2 && hop_en && b_link == hop_in;
    wire        is_hst = b_v && b_type == 2'd2 && host_en && b_link == host_ch;
    // pass-through queue credits returned by the core (q1..q5 = channels 0..4)
    wire [3:0] cr_hop = tv_q[17 + 4 * (1 + hop_out) +: 4];
    wire [3:0] cr_hst = tv_q[17 + 4 * (1 + host_ch) +: 4];
    reg f_y, f_hop, f_own, f_kin, f_cmp;
    // ================= (1) y packer
    reg [YW*512-1:0] asm_d; reg [YB-1:0] asm_n;
    reg [YW*512-1:0] yq [0:YR-1]; reg [$clog2(YR)-1:0] yw, yr; reg [$clog2(YR+1)-1:0] yn;
    wire y_pop;
    integer k, w;
    reg [YW*512-1:0] asm_nx, row_d; reg [YB:0] n_nx; reg row_push, row_bad;
    always @(*) begin
        asm_nx = asm_d; n_nx = {1'b0, asm_n}; row_push = 1'b0; row_bad = 1'b0; row_d = asm_d;
        if (is_red && y_en)
            for (k = 0; k < 4; k = k + 1)
                if (b_mask[k]) begin
                    for (w = 0; w < YW; w = w + 1)
                        if (w == n_nx[YB-1:0]) begin
                            asm_nx[w*512 +: 512] = tv_q[52 + ((MUT == 1) ? ((k == 1) ? 2 : (k == 2) ? 1 : k) : k) * 512 +: 512];
                        end
                    if (b_last[k] && n_nx != YW - 1) row_bad = 1'b1;          // a message ends inside a y beat
                    n_nx = n_nx + 1'b1;
                    if (n_nx == YW) begin row_push = 1'b1; row_d = asm_nx; n_nx = 0; end   // the completed row
                end
    end
    // the beat carries at most 4 words: at most one row completes in a beat when YW >= 4
    // output stage: the y beat leaves from flops (oy_v / oy_d); f_hc_yr is the HC skid's ready (same-cycle handshake)
    reg oy_v; reg [YW*512-1:0] oy_d;
    wire y_load = (yn != 0) && (!oy_v || y_pop);
    always @(posedge clk or negedge rn)
        if (!rn) begin asm_n <= 0; yw <= 0; yr <= 0; yn <= 0; f_y <= 1'b0; oy_v <= 1'b0; end
        else begin
            asm_n <= n_nx[YB-1:0];
            if (row_push) yw <= (yw == YR - 1) ? 0 : yw + 1'b1;
            if (y_load) yr <= (yr == YR - 1) ? 0 : yr + 1'b1;
            yn <= yn + row_push - y_load;
            if ((row_push && yn == YR && !y_load) || row_bad) f_y <= 1'b1;
            if (y_load) oy_v <= 1'b1; else if (y_pop) oy_v <= 1'b0;
        end
    always @(posedge clk) begin
        asm_d <= asm_nx;
        if (row_push) yq[yw] <= row_d;
        if (y_load) oy_d <= yq[yr];
    end
    assign t_hc_yv[0] = oy_v;
    assign y_pop = oy_v && f_hc_yr[0];
    assign t_hc_y = oy_d;
    // room for M more beats of 4 words: free words in rows + the open row >= 4 M
    wire [31:0] y_free = (YR - yn) * YW - asm_n;
    wire y_room = !y_en || (y_free >= 4 * M + 4);
    // ================= (2) WFC kit link
    // hop-in: diverted flits -> FIFO -> grant-protocol sender to the kit
    reg [512:0] hq [0:HD-1]; reg [$clog2(HD)-1:0] hw, hr; reg [$clog2(HD+1)-1:0] hn;
    wire k_cv = (hn != 0); wire k_cr; wire k_take = k_cv && k_cr;
    wire h_push = is_hop && !((MUT == 2) && !f_wfcg[0]);
    always @(posedge clk or negedge rn)
        if (!rn) begin hw <= 0; hr <= 0; hn <= 0; f_kin <= 1'b0; end
        else begin
            if (h_push) hw <= (hw == HD - 1) ? 0 : hw + 1'b1;
            if (k_take) hr <= (hr == HD - 1) ? 0 : hr + 1'b1;
            hn <= hn + h_push - k_take;
            if (h_push && hn == HD && !k_take) f_kin <= 1'b1;
        end
    always @(posedge clk) if (h_push) hq[hw] <= {b_plst, b_flit[511:0]};
    wire [512:0] k_ld; wire k_lv;
    ot_dsrom_mtp_ltx #(.W(513)) u_ktx (.clk(clk), .rst_n(rn), .c_valid(k_cv), .c_ready(k_cr), .c_data(hq[hr]),
        .l_valid(k_lv), .l_ready(f_wfcg[0]), .l_data(k_ld));
    assign t_wfc = {k_ld, k_lv};
    wire hop_room = !hop_en || ((HD - hn) >= M + 1);
    // hop-out: the kit's flits (grant protocol receiver) -> injection
    wire ko_v; wire ko_r; wire [512:0] ko_d;
    ot_dsrom_mtp_lrx #(.W(513), .D(KD)) u_krx (.clk(clk), .rst_n(rn), .l_valid(f_wfc[0]), .l_ready(t_wfcg[0]),
        .l_data(f_wfc[513:1]), .c_valid(ko_v), .c_ready(ko_r), .c_data(ko_d));
    // ================= (3) host channel
    always @(posedge clk or negedge rn)
        if (!rn) t_host <= 0;
        else t_host <= is_hst ? {b_flit[514:0], 1'b1} : 516'd0;
    reg [80:0] fh_q; always @(posedge clk or negedge rn) if (!rn) fh_q <= 0; else fh_q <= f_host;
    wire [10:0] h_st = fh_q[80:70]; wire [4:0] h_crn = (MUT == 3) ? 5'd0 : fh_q[69:65]; wire h_tv = fh_q[64];
    wire [63:0] h_td = fh_q[63:0];
    reg [11:0] crn_acc; reg [10:0] st_sent;
    reg [63:0] cq [0:CD-1]; reg [$clog2(CD)-1:0] cw, cr; reg [$clog2(CD+1)-1:0] cn;
    wire hs_take;                                // a host-return flit is injected this cycle
    wire [4:0] crn_send = (crn_acc > 31) ? 5'd31 : crn_acc[4:0];
    wire hs_need = host_en && (crn_acc != 0 || cn != 0 || h_st != st_sent);
    wire c_pop = hs_take && cn != 0;
    always @(posedge clk or negedge rn)
        if (!rn) begin crn_acc <= 0; st_sent <= 0; cw <= 0; cr <= 0; cn <= 0; f_cmp <= 1'b0; end
        else begin
            crn_acc <= crn_acc + h_crn - (hs_take ? crn_send : 5'd0);
            if (hs_take) st_sent <= h_st;
            if (h_tv) cw <= (cw == CD - 1) ? 0 : cw + 1'b1;
            if (c_pop) cr <= (cr == CD - 1) ? 0 : cr + 1'b1;
            cn <= cn + h_tv - c_pop;
            if ((h_tv && cn == CD && !c_pop) || crn_acc > 12'd4000) f_cmp <= 1'b1;   // never at ingest rates
        end
    always @(posedge clk) if (h_tv) cq[cw] <= h_td;
    // return flit data [80:0] = {st 11, crn 5, cv, cd 64} (the host's own t_collective layout)
    wire [551:0] hs_flit = {471'd0, h_st, crn_send, cn != 0, (cn != 0) ? cq[cr] : 64'd0};
    // ================= injection into the core: VM words first, then the kit / host flits under queue credits
    reg [4:0] cred_hop, cred_hst; reg rr;
    wire vm_busy = fv_v;
    wire want_k = hop_en && ko_v && cred_hop != 0;
    wire want_h = hs_need && cred_hst != 0;
    wire pick_k = !vm_busy && want_k && (!want_h || !rr);
    wire pick_h = !vm_busy && want_h && !pick_k;
    assign ko_r = pick_k;
    assign hs_take = pick_h;
    always @(posedge clk or negedge rn)
        if (!rn) begin c_fvm <= 0; cred_hop <= QD; cred_hst <= QD; rr <= 1'b0; f_own <= 1'b0; end
        else begin
            if (pick_k)      c_fvm <= {40'd0, ko_d[511:0], 32'd0, 1'b0, ko_d[512], hop_out, 2'd2, 1'b1};
            else if (pick_h) c_fvm <= {hs_flit, 32'd0, 1'b0, 1'b1, host_ch, 2'd2, 1'b1};
            else             c_fvm <= own_vm ? 592'd0 : fv_q;
            cred_hop <= cred_hop - pick_k + ((hop_en && b_v) ? cr_hop : 4'd0);
            cred_hst <= cred_hst - pick_h + ((host_en && b_v) ? cr_hst : 4'd0);
            if (pick_k || pick_h) rr <= pick_k;
            if (own_vm) f_own <= 1'b1;
        end
    // ================= VM-side outputs
    // the adapter's sticky fault reaches the VM in the next beat's slab fault bit [41]; when the core sends nothing, the
    // adapter sends ONE status beat of its own (type 3, no words, credits 0) for it (ts[0]: the VM has room)
    wire xflt = f_y | f_kin | f_own | f_cmp;
    reg x_sent;
    wire x_beat = xflt && !x_sent && !b_v && ts_q[0];
    always @(posedge clk or negedge rn)
        if (!rn) begin t_vm <= 0; c_ts <= 0; x_sent <= 1'b0; end
        else begin
            // a diverted pass-through beat reaches the VM as a status beat (header credits / fault kept, no data)
            t_vm <= (is_hop || is_hst) ? {2048'd0, tv_q[51:42], tv_q[41] | xflt, tv_q[40:17], 14'd0, 2'd3, 1'b1}
                  : x_beat ? {2048'd0, tv_q[51:50], 8'd0, 1'b1, 24'd0, 14'd0, 2'd3, 1'b1}
                  : {tv_q[2099:42], tv_q[41] | (b_v && xflt), tv_q[40:0]};
            if (x_beat || (b_v && xflt)) x_sent <= 1'b1;
            c_ts <= {ts_q[2:1], ts_q[0] && y_room && hop_room};
        end
endmodule
