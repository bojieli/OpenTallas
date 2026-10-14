`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// tb_hgi_rlanes (hgi-1010/c 2026-10-10, BENCH ONLY): a behavioural model of the four kport HBM read lanes the DMA mover
// uses (ot_hgi_dma_mover r_req_* / r_rsp_*), for unit benches without the real kport + svc.  Lane l (= stack l):
//   a request {addr 37, len 1..8, tag 16} is taken when r_req_v && r_req_rdy (rdy: fewer than NOL requests queued on the
//   lane, randomly withheld when RAND); its sectors are answered in request order, address order within the burst,
//   LAT cycles after acceptance at the earliest, one sector a cycle a lane, held until r_rsp_rdy; rsp_tag = the request's
//   tag, rsp_last on the burst's last sector.  The parent supplies each presented sector's data: la (byte address of the
//   sector on lane l) -> ld (combinational, from the parent's memory).  A WRITE request (r_req_we, one full sector) is
//   applied at acceptance through wv / wa / wd / ws (the parent writes its memory on the next edge) and answered in order
//   with rsp_we = 1 (a one-beat response) LAT cycles later.
// Checks ($fatal): a request whose stack (addr[36:35]) is not the lane, a length outside 1..8, an unaligned address.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hgi_rlanes #(
    parameter integer LAT = 12,
    parameter integer NOL = 16,
    parameter integer RAND = 1,
    parameter integer SEED = 11
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [3:0]        r_req_v,
    output reg  [3:0]        r_req_rdy,
    input  wire [4*37-1:0]   r_req_addr,
    input  wire [4*4-1:0]    r_req_len,
    input  wire [4*16-1:0]   r_req_tag,
    input  wire [3:0]        r_req_we,
    input  wire [4*256-1:0]  r_req_wdata,
    input  wire [4*32-1:0]   r_req_wstrb,
    output reg  [3:0]        r_rsp_v,
    output reg  [3:0]        r_rsp_we,
    input  wire [3:0]        r_rsp_rdy,
    output reg  [4*16-1:0]   r_rsp_tag,
    output reg  [3:0]        r_rsp_last,
    output wire [4*256-1:0]  r_rsp_data,
    output reg  [4*37-1:0]   la,
    input  wire [4*256-1:0]  ld,
    output reg  [3:0]        wv,
    output reg  [4*37-1:0]   wa,
    output reg  [4*256-1:0]  wd,
    output reg  [4*32-1:0]   ws
);
    assign r_rsp_data = ld;
    integer seed = SEED;
    longint tn = 0;
    reg [36:0] qa [0:3][0:63]; reg [3:0] ql [0:3][0:63]; reg qw [0:3][0:63]; reg [15:0] qt [0:3][0:63]; longint qd [0:3][0:63];
    integer qh [0:3], qn [0:3], bt [0:3];
    initial begin for (integer l = 0; l < 4; l = l + 1) begin qh[l] = 0; qn[l] = 0; bt[l] = 0; end
        r_req_rdy = 4'd0; r_rsp_v = 4'd0; r_rsp_we = 4'd0; r_rsp_tag = '0; r_rsp_last = 4'd0; la = '0; wv = 4'd0; end
    always @(posedge clk) begin
        tn <= tn + 1;
        if (!rst_n) begin
            for (integer l = 0; l < 4; l = l + 1) begin qh[l] = 0; qn[l] = 0; bt[l] = 0; end
            r_req_rdy <= 4'd0; r_rsp_v <= 4'd0; wv <= 4'd0;
        end else begin
            wv <= 4'd0;
            for (integer l = 0; l < 4; l = l + 1) begin
                // the presented sector was taken at this edge
                if (r_rsp_v[l] && r_rsp_rdy[l]) begin
                    if (bt[l] + 1 == ql[l][qh[l] % 64]) begin bt[l] = 0; qh[l] = qh[l] + 1; qn[l] = qn[l] - 1; end
                    else bt[l] = bt[l] + 1;
                end
                // a request taken at this edge
                if (r_req_v[l] && r_req_rdy[l]) begin
                    if (r_req_addr[l*37 + 35 +: 2] != 2'(l)) $fatal(1, "FATAL rlanes: lane %0d got a request for stack %0d", l, r_req_addr[l*37 + 35 +: 2]);
                    if (r_req_len[l*4 +: 4] == 4'd0 || r_req_len[l*4 +: 4] > 4'd8 || (r_req_we[l] && r_req_len[l*4 +: 4] != 4'd1))
                        $fatal(1, "FATAL rlanes: lane %0d length %0d", l, r_req_len[l*4 +: 4]);
                    if (r_req_we[l] && r_req_wstrb[l*32 +: 32] != 32'hFFFFFFFF) $fatal(1, "FATAL rlanes: lane %0d partial-sector write", l);
                    if (r_req_we[l]) begin wv[l] <= 1'b1; wa[l*37 +: 37] <= r_req_addr[l*37 +: 37]; wd[l*256 +: 256] <= r_req_wdata[l*256 +: 256];
                        ws[l*32 +: 32] <= r_req_wstrb[l*32 +: 32]; end
                    qw[l][(qh[l] + qn[l]) % 64] = r_req_we[l];
                    if (r_req_addr[l*37 +: 5] != 5'd0) $fatal(1, "FATAL rlanes: lane %0d unaligned address", l);
                    qa[l][(qh[l] + qn[l]) % 64] = r_req_addr[l*37 +: 37]; ql[l][(qh[l] + qn[l]) % 64] = r_req_len[l*4 +: 4];
                    qt[l][(qh[l] + qn[l]) % 64] = r_req_tag[l*16 +: 16]; qd[l][(qh[l] + qn[l]) % 64] = tn + LAT;
                    qn[l] = qn[l] + 1;
                end
                // present the head's next sector
                if (qn[l] > 0 && qd[l][qh[l] % 64] <= tn) begin
                    r_rsp_v[l] <= 1'b1; r_rsp_tag[l*16 +: 16] <= qt[l][qh[l] % 64]; r_rsp_we[l] <= qw[l][qh[l] % 64];
                    r_rsp_last[l] <= bt[l] + 1 == ql[l][qh[l] % 64];
                    la[l*37 +: 37] <= qa[l][qh[l] % 64] + 37'(bt[l] * 32);
                end else r_rsp_v[l] <= 1'b0;
                r_req_rdy[l] <= qn[l] < NOL && (RAND == 0 || ($random(seed) & 3) != 0);
            end
        end
    end
endmodule
