`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 VM lane group as a CHAIN (hgi-unitrate 2026-10-10, hbm-phys / lead decision): one shared 32-lane bus per group
// runs VM face -> station 0 -> station 1 -> ... (R25GQ: lgW = VM -> SU -> SFU -> HC, lgE = VM -> CP -> quant).
//   ot_hgi_vm_lanehead   at the VM face: grants the bus per BURST (round robin over the K request bits that ride up the
//                        chain), passes the merged lane requests to the VM and broadcasts credits / responses / grant down;
//   ot_hgi_vm_lanestation in each client block (ID = its slot): one register stage each way on every chain signal
//                        (request bits / lane requests up; grant / credits / responses down); its local client ORs its
//                        request bit into slot ID and, only while granted, its lane requests into the up bus; credits and
//                        responses go to the local client only while it owns the bus.
// A burst holds the bus from grant to release (the client releases only when its credits are home and its responses /
// write dones landed), so lanes of two clients never mix and no response needs a tag.  Each station adds one edge each
// way to the credit loop: LQ (the client's credits = the VM lane queue depth) >= 2 x (stations to the VM + relays) + 8.
// Direction-generic: a read group has REQW 16 ({v, sector}) / RSPW 257 ({v, data}); a write group REQW 280 / RSPW 1 (done).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_vm_lanestation #(
    parameter integer K = 3,              // stations on the chain (request / grant bits)
    parameter integer ID = 0,             // this station's slot
    parameter integer REQW = 16,
    parameter integer RSPW = 257,
    parameter integer TAP = 1             // 0: a pure relay stage (no client)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // toward the VM (up)
    output reg  [K-1:0]         up_req,
    output reg  [32*REQW-1:0]   up_q,
    input  wire [K-1:0]         up_gnt,
    input  wire [31:0]          up_cr,
    input  wire [32*RSPW-1:0]   up_rsp,
    // away from the VM (down: the next station)
    input  wire [K-1:0]         dn_req,
    input  wire [32*REQW-1:0]   dn_q,
    output reg  [K-1:0]         dn_gnt,
    output reg  [31:0]          dn_cr,
    output reg  [32*RSPW-1:0]   dn_rsp,
    // the local client (unit ports rg_req / rg_gnt, wrq / wrq_cr / wrr, or the write side)
    input  wire                 l_req,
    output wire                 l_gnt,
    input  wire [32*REQW-1:0]   l_q,
    output reg  [31:0]          l_cr,
    output reg  [32*RSPW-1:0]   l_rsp
);
    reg own;                                           // this station's grant, registered here (the down copy's edge)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            up_req <= '0; up_q <= '0; dn_gnt <= '0; dn_cr <= '0; dn_rsp <= '0; l_cr <= '0; l_rsp <= '0; own <= 1'b0;
        end else begin
            up_req <= dn_req | ((TAP != 0 && l_req) ? (K'(1) << ID) : '0);
            up_q <= dn_q | ((TAP != 0 && own) ? l_q : '0);
            dn_gnt <= up_gnt; dn_cr <= up_cr; dn_rsp <= up_rsp;
            own <= (TAP != 0) && up_gnt[ID];
            l_cr <= (TAP != 0 && up_gnt[ID]) ? up_cr : 32'd0;
            for (integer l = 0; l < 32; l = l + 1)
                l_rsp[l*RSPW +: RSPW] <= (TAP != 0 && up_gnt[ID]) ? up_rsp[l*RSPW +: RSPW] : {RSPW{1'b0}};
        end
    assign l_gnt = own;
endmodule

module ot_hgi_vm_lanehead #(
    parameter integer K = 3,
    parameter integer REQW = 16,
    parameter integer RSPW = 257,
    parameter integer MUT = 0             // bench mutant: 1 the grant moves every 64 edges even while its owner holds it
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // the chain (first station's up side)
    input  wire [K-1:0]         c_req,
    input  wire [32*REQW-1:0]   c_q,
    output reg  [K-1:0]         c_gnt,
    output reg  [31:0]          c_cr,
    output reg  [32*RSPW-1:0]   c_rsp,
    // the VM unit's group (rq / rq_cr / rr or w2q / w2q_cr / w2q_done)
    output reg  [32*REQW-1:0]   g_q,
    input  wire [31:0]          g_cr,
    input  wire [32*RSPW-1:0]   g_rsp
);
    reg [$clog2(K > 1 ? K : 2)-1:0] rr_ptr; reg [5:0] age;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin c_gnt <= '0; rr_ptr <= '0; age <= '0; g_q <= '0; c_cr <= '0; c_rsp <= '0; end
        else begin
            age <= age + 6'd1;
            g_q <= c_q; c_cr <= g_cr; c_rsp <= g_rsp;
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
endmodule
`default_nettype wire
