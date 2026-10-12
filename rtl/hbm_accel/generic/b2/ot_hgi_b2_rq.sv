`timescale 1ns/1ps
`default_nettype none
// HBM B2 cluster record stations (el1011-hbm-b2-cp): the per-cluster end of ot_hgi_b2_disp's command bus.  Glue in the
// tile: ONE station per unit (ot_hgi_b2_rqu, one hardened block replicated 5 x 4; its unit / cluster are strap pins,
// not parameters), sitting at the unit's record port; the cluster fans the command bus out to its 5 stations.
//   * cb (pin flops): beats with qmask[qid] and unit == uid are written straight into the tail slot (beat k -> bits
//     [k*BW +: BW]); the last beat commits it.  The dispatcher's credits (D a unit and cluster) guarantee the room;
//   * D slots; the slot the unit executes stays stable until its done / fault (the legacy record buses hold the record
//     while the unit runs, as cp_die's registers did);
//   * issue: one valid pulse (a flop) when a record is committed, the unit idle (one record in a unit, as the legacy
//     credit) and its ret[0] ready; done / fault free the slot and return {fault, done} (registered) = the credit.
// MUT (bench): 2 the issue takes the YOUNGEST committed slot instead of the oldest (record ordering mutant).
module ot_hgi_b2_rqu #(
    parameter integer D   = 4,
    parameter integer BW  = 1024,
    parameter integer PW  = 2198,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [2:0]    uid,          // strap: unit index (0 SM, 1 SU, 2 SFU, 3 ATT, 4 DMA)
    input  wire [1:0]    qid,          // strap: cluster
    input  wire [BW+8:0] cb,
    output reg  [1:0]    rb,           // {fault, done}
    output wire [1098:0] rec_a,        // rec[1098:0] = {record [1098:1], valid pulse} (E face)
    output wire [PW-1100:0] rec_b,     // rec[PW-1:1099] (N face)
    input  wire [2:0]    ret           // {fault, done, ready}
);
    localparam integer DB = (D > 1) ? $clog2(D) : 1;
    localparam integer DN = DB + 1;
    localparam [DB-1:0] DM1 = D - 1;
    localparam integer SLW = 128, NSL = (PW + SLW - 1) / SLW, SPB = BW / SLW;   // 18 storage slices, 8 a beat
    // v2 (gate): pin flops on every input (control reset, payload not); stage W decodes the beat and registers the data
    // and one write-enable copy per storage slice; stage S writes the slot.  Each slice reads with its own copy of the
    // executing-slot pointer (no pointer net over ~600 loads).
    reg c_v; reg [7:0] c_h; reg [BW-1:0] c_d; reg [2:0] u_q; reg [1:0] q_q; reg [2:0] ret_q;
    always @(posedge clk) c_d <= cb[9 +: BW];
    wire me = c_v && c_h[4 + q_q] && c_h[3:1] == u_q;  // c_h = cb[8:1] {qmask, unit, last}
    wire last = c_h[0];
    reg [1:0] cbt;
    reg [BW-1:0] wd;
    reg cm_q;
    reg [DB-1:0] hp, tp;
    reg [DN-1:0] n;
    reg run, iv;
    reg [DB-1:0] es;
    function automatic [DB-1:0] inc(input [DB-1:0] p); inc = (p == DM1) ? {DB{1'b0}} : p + 1'b1; endfunction
    function automatic [DB-1:0] dec(input [DB-1:0] p); dec = (p == {DB{1'b0}}) ? DM1 : p - 1'b1; endfunction
    wire fin = run && (ret_q[1] || ret_q[2]);
    wire iss = !fin && !run && n != 0 && ret_q[0];
    wire [DB-1:0] es_n = (MUT == 2) ? dec(cm_q ? inc(tp) : tp) : hp;
    always @(posedge clk) if (me) wd <= c_d;
    reg [SLW-1:0] qd [0:NSL-1][0:D-1];
    wire [NSL*SLW-1:0] hdx;
    genvar gs;
    generate for (gs = 0; gs < NSL; gs = gs + 1) begin : sl
        localparam integer BEAT = gs / SPB, OFS = (gs % SPB) * SLW;
        (* keep *) reg [D-1:0] wen;                  // this slice's slot write enables (stage W -> S)
        (* keep *) reg [DB-1:0] esc;                 // this slice's copy of the executing slot
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin wen <= {D{1'b0}}; esc <= {DB{1'b0}}; end
            else begin
                wen <= (me && cbt == BEAT) ? ({{(D-1){1'b0}}, 1'b1} << tp) : {D{1'b0}};
                if (iss) esc <= es_n;
            end
        integer k;
        always @(posedge clk) for (k = 0; k < D; k = k + 1) if (wen[k]) qd[gs][k] <= wd[OFS +: SLW];
        assign hdx[gs * SLW +: SLW] = qd[gs][esc];
    end endgenerate
    wire [PW-1:0] rec = {hdx[PW-1:1], iv};
    assign rec_a = rec[1098:0]; assign rec_b = rec[PW-1:1099];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c_v <= 1'b0; c_h <= 8'd0; u_q <= 3'd0; q_q <= 2'd0; ret_q <= 3'd0;
            cbt <= 2'd0; rb <= 2'd0; run <= 1'b0; iv <= 1'b0; cm_q <= 1'b0;
            hp <= {DB{1'b0}}; tp <= {DB{1'b0}}; es <= {DB{1'b0}}; n <= {DN{1'b0}};
        end else begin
            c_v <= cb[0]; c_h <= cb[8:1]; u_q <= uid; q_q <= qid; ret_q <= ret;
            if (me) begin cbt <= last ? 2'd0 : cbt + 2'd1; if (last) tp <= inc(tp); end
            cm_q <= me && last;                       // the slot is complete after stage S's write
            iv <= 1'b0; rb <= 2'd0;
            if (fin) begin hp <= inc(hp); run <= 1'b0; rb <= {ret_q[2], ret_q[1]}; end
            else if (iss) begin run <= 1'b1; iv <= 1'b1; es <= es_n; end
            n <= n + {{DB{1'b0}}, cm_q} - {{DB{1'b0}}, fin};
        end
    end
endmodule

// one cluster's five stations (bench / cluster-top convenience; the hardened block is ot_hgi_b2_rqu)
module ot_hgi_b2_rq #(
    parameter integer Q   = 0,
    parameter integer D   = 4,
    parameter integer BW  = 1024,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [BW+8:0] cb,
    output wire [9:0]    rb,           // {fault 5, done 5}
    output wire [938:0]  sm_rec,
    input  wire [2:0]    sm_ret,
    output wire [2197:0] su_rec,
    input  wire [2:0]    su_ret,
    output wire [1173:0] sfu_rec,
    input  wire [2:0]    sfu_ret,
    output wire [1471:0] att_rec,
    input  wire [2:0]    att_ret,
    output wire [703:0]  dma_rec,
    input  wire [2:0]    dma_ret
);
    wire [2197:0] r [0:4]; wire [1:0] b [0:4];
    wire [2:0] rt [0:4];
    assign rt[0] = sm_ret; assign rt[1] = su_ret; assign rt[2] = sfu_ret; assign rt[3] = att_ret; assign rt[4] = dma_ret;
    genvar g;
    localparam [1:0] QB = Q;
    generate for (g = 0; g < 5; g = g + 1) begin : u
        localparam [2:0] UG = g;
        ot_hgi_b2_rqu #(.D(D), .BW(BW), .MUT(MUT)) st (.clk(clk), .rst_n(rst_n), .uid(UG), .qid(QB), .cb(cb),
            .rb(b[g]), .rec_a(r[g][1098:0]), .rec_b(r[g][2197:1099]), .ret(rt[g]));
    end endgenerate
    assign rb = {b[4][1], b[3][1], b[2][1], b[1][1], b[0][1], b[4][0], b[3][0], b[2][0], b[1][0], b[0][0]};
    assign sm_rec = r[0][938:0]; assign su_rec = r[1]; assign sfu_rec = r[2][1173:0]; assign att_rec = r[3][1471:0];
    assign dma_rec = r[4][703:0];
endmodule
`default_nettype wire
