`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 VM shared lane group (hgi-unitrate 2026-10-10).  One 32-lane VM wide group (read: rq {v, sector} / rq_cr /
// rr {v, data}; write: wq {v, sector, data, mask} / wq_cr / wq_done) shared by K clients (SU, SFU, FUSED, HC, SM
// x-load, ATT staging) instead of one group per client (hbm-phys: per-client lanes overflow the VM-side wiring).
//   Ownership is per BURST: a client raises req for a whole stage or drain burst and holds it until every request of
//   the burst is answered (its credits are home and its responses / write dones landed); the group then goes to the
//   next requester in round-robin order.  So requests of two clients never mix on the group, credits never cross
//   owners, and every response belongs to the owner that issued it (no tags).
//   Physical form: the group is a registered bus past the client stations (request OR-merge of the owner's lanes,
//   responses broadcast, each station keeps those of its own grant): one register stage each way here (+1 edge each
//   way on the client's credit loop: size LQ to the loop).
// RSPW = 257 for a read group (the response is {v, data}); 1 for a write group (the response is the done pulse).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_lanearb #(
    parameter integer K = 3,              // clients
    parameter integer REQW = 16,          // lane request width (read 16, write 280)
    parameter integer RSPW = 257,         // lane response width (read 257, write 1 = done)
    parameter integer MUT = 0             // bench mutant: 1 the grant rotates every 64 edges even while the owner holds
) (
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire [K-1:0]           c_req,
    output reg  [K-1:0]           c_gnt,
    input  wire [K*32*REQW-1:0]   c_q,
    output reg  [K*32-1:0]        c_cr,
    output reg  [K*32*RSPW-1:0]   c_rsp,
    output reg  [32*REQW-1:0]     g_q,
    input  wire [31:0]            g_cr,
    input  wire [32*RSPW-1:0]     g_rsp
);
    reg [$clog2(K > 1 ? K : 2)-1:0] rr_ptr;
    reg [5:0] age;
    // ownership: hold while the owner requests; pick the next requester (round robin from rr_ptr) when free
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_gnt <= '0; rr_ptr <= '0; age <= '0; end
        else begin
            age <= age + 6'd1;
            if ((c_gnt & c_req) == '0 || (MUT == 1 && age == 6'd63)) begin : pick
                reg [K-1:0] ng; integer q;
                ng = '0;
                for (integer i = 0; i < K; i = i + 1) begin
                    q = (rr_ptr + 1 + i) % K;
                    if (ng == '0 && c_req[q] && !(MUT == 1 && c_gnt[q])) ng[q] = 1'b1;
                end
                c_gnt <= ng;
                for (integer i = 0; i < K; i = i + 1) if (ng[i]) rr_ptr <= i[$clog2(K > 1 ? K : 2)-1:0];
            end
        end
    end
    // request bus: the owner's lanes (registered); credits / responses back to the owner (registered)
    reg [K-1:0] own_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin g_q <= '0; c_cr <= '0; c_rsp <= '0; own_q <= '0; end
        else begin : bus
            reg [32*REQW-1:0] m;
            m = '0;
            for (integer i = 0; i < K; i = i + 1) if (c_gnt[i]) m = m | c_q[i*32*REQW +: 32*REQW];
            g_q <= m;
            own_q <= c_gnt;
            for (integer i = 0; i < K; i = i + 1) begin
                c_cr[i*32 +: 32] <= c_gnt[i] || own_q[i] ? g_cr : 32'd0;
                for (integer l = 0; l < 32; l = l + 1)
                    c_rsp[(i*32 + l)*RSPW +: RSPW] <= (c_gnt[i] || own_q[i]) ? g_rsp[l*RSPW +: RSPW] : {RSPW{1'b0}};
            end
        end
endmodule
`default_nettype wire
