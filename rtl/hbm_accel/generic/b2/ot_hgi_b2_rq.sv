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
    output wire [PW-1:0] rec,          // {record [PW-1:1], valid pulse}
    input  wire [2:0]    ret           // {fault, done, ready}
);
    localparam integer DB = (D > 1) ? $clog2(D) : 1;
    localparam integer DN = DB + 1;
    reg [BW+8:0] c; reg [2:0] u_q; reg [1:0] q_q;      // pin flops
    wire cv = c[0] && c[5 + q_q] && c[4:2] == u_q;
    reg [1:0] cbt;
    reg [PW-1:0] qd [0:D-1];
    reg [DB-1:0] hp, tp, es;
    reg [DN-1:0] n;
    reg run, iv;
    function automatic [DB-1:0] inc(input [DB-1:0] p); inc = (p == DB'(D - 1)) ? '0 : p + 1'b1; endfunction
    function automatic [DB-1:0] dec(input [DB-1:0] p); dec = (p == '0) ? DB'(D - 1) : p - 1'b1; endfunction
    wire [PW-1:0] hd = qd[es];
    assign rec = {hd[PW-1:1], iv};
    wire cm  = cv && c[1];
    wire fin = run && (ret[1] || ret[2]);
    always @(posedge clk) if (cv) qd[tp][cbt*BW +: BW] <= c[9 +: BW];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c <= '0; u_q <= 3'd0; q_q <= 2'd0; cbt <= 2'd0; rb <= 2'd0; run <= 1'b0; iv <= 1'b0;
            hp <= '0; tp <= '0; es <= '0; n <= '0;
        end else begin
            c <= cb; u_q <= uid; q_q <= qid;
            if (cv) cbt <= c[1] ? 2'd0 : cbt + 2'd1;
            iv <= 1'b0; rb <= 2'd0;
            if (cm) tp <= inc(tp);
            if (fin) begin hp <= inc(hp); run <= 1'b0; rb <= {ret[2], ret[1]}; end
            else if (!run && n != 0 && ret[0]) begin
                run <= 1'b1; iv <= 1'b1; es <= (MUT == 2) ? dec(cm ? inc(tp) : tp) : hp;
            end
            n <= n + DN'(cm) - DN'(fin);
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
    generate for (g = 0; g < 5; g = g + 1) begin : u
        ot_hgi_b2_rqu #(.D(D), .BW(BW), .MUT(MUT)) st (.clk(clk), .rst_n(rst_n), .uid(3'(g)), .qid(2'(Q)), .cb(cb),
            .rb(b[g]), .rec(r[g]), .ret(rt[g]));
    end endgenerate
    assign rb = {b[4][1], b[3][1], b[2][1], b[1][1], b[0][1], b[4][0], b[3][0], b[2][0], b[1][0], b[0][0]};
    assign sm_rec = r[0][938:0]; assign su_rec = r[1]; assign sfu_rec = r[2][1173:0]; assign att_rec = r[3][1471:0];
    assign dma_rec = r[4][703:0];
endmodule
`default_nettype wire
