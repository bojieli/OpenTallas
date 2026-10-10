`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_rgx_sink (hgi-1010/a 2026-10-10, spec G25): the DESTINATION side of the hardware COLL.ROW_GATHER.
//
// Delivery credits: lane l of the endpoint is dispatched only while cr[l] > 0 (del_permit); the dispatch reserves one
// credit (del_reserve, before the endpoint's HUBW wire flight) and the credit returns when the flit leaves this sink, so
// the per-lane FIFO can never overflow and a stalled writer holds flits in the endpoint receive buffers (switch egress
// credits back-pressure the senders).  CAP 64 covers the loop (dispatch 1 + HUBW 35 + 4 decode + 5 FIFO + 1 return).
// Decode (4 registered stages, then the FIFO): a delivered flit's gi = x * F + f -> list row x = (gi * ceil(2^22 / F)) >> 22 (exact for gi < 2^17, F <= 32:
// table, no divider), f = gi - x F; then the O address base + x stride + f (64 B in HBM, 16 words in VM); the FIFO
// holds {addr, x, f, data}.  The write port per lane is {w_v, w_addr, w_x, w_f, w_data} / w_rdy.  A rank that is not a
// destination (discard = 1) drains its flits without writing.  Fault (sticky): a delivered flit that is not a result
// flit, a FIFO overflow (only reachable if the credit accounting is broken), x >= K.
module ot_hgi_coll_rgx_sink #(
    parameter integer DEL = 4,
    parameter integer CAP = 64,
    parameter integer FW  = 512,
    parameter integer PWT = FW + 33,
    parameter integer MUT_CREDIT = 0     // bench mutant: a reservation does not consume a credit
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    input  wire [5:0]           cfg_nflit,   // F
    input  wire [11:0]          cfg_k,
    input  wire                 cfg_discard,
    input  wire [39:0]          cfg_obase,   // O: base (HBM byte address or VM word address)
    input  wire [31:0]          cfg_ostride, // O: row stride (same unit)
    input  wire                 cfg_ovm,     // O in VM: a flit is 16 words (else 64 bytes)
    input  wire [DEL-1:0]       del_reserve,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output wire [DEL-1:0]       w_v,
    output wire [DEL*11-1:0]    w_x,
    output wire [DEL*5-1:0]     w_f,
    output wire [DEL*40-1:0]    w_addr,      // O base + x stride + f (64 B or 16 words)
    output wire [DEL*FW-1:0]    w_data,
    input  wire [DEL-1:0]       w_rdy,
    output wire                 drained,
    output reg                  fault
);
    reg [5:0] f_q; reg [11:0] k_q; reg disc_q; reg [22:0] rcp_q; reg [39:0] ob_q; reg [31:0] os_q; reg ovm_q;
    function automatic [22:0] rcp(input [5:0] f);
        case (f)
            6'd1: rcp = 23'd4194304;
            6'd2: rcp = 23'd2097152;
            6'd3: rcp = 23'd1398102;
            6'd4: rcp = 23'd1048576;
            6'd5: rcp = 23'd838861;
            6'd6: rcp = 23'd699051;
            6'd7: rcp = 23'd599187;
            6'd8: rcp = 23'd524288;
            6'd9: rcp = 23'd466034;
            6'd10: rcp = 23'd419431;
            6'd11: rcp = 23'd381301;
            6'd12: rcp = 23'd349526;
            6'd13: rcp = 23'd322639;
            6'd14: rcp = 23'd299594;
            6'd15: rcp = 23'd279621;
            6'd16: rcp = 23'd262144;
            6'd17: rcp = 23'd246724;
            6'd18: rcp = 23'd233017;
            6'd19: rcp = 23'd220753;
            6'd20: rcp = 23'd209716;
            6'd21: rcp = 23'd199729;
            6'd22: rcp = 23'd190651;
            6'd23: rcp = 23'd182362;
            6'd24: rcp = 23'd174763;
            6'd25: rcp = 23'd167773;
            6'd26: rcp = 23'd161320;
            6'd27: rcp = 23'd155345;
            6'd28: rcp = 23'd149797;
            6'd29: rcp = 23'd144632;
            6'd30: rcp = 23'd139811;
            6'd31: rcp = 23'd135301;
            6'd32: rcp = 23'd131072;
            default: rcp = 23'd0;
        endcase
    endfunction
    reg [7:0] cr [0:DEL-1];
    reg [DEL-1:0] p1_v, p2_v;
    reg [15:0] p1_gi [0:DEL-1]; reg [FW-1:0] p1_d [0:DEL-1]; reg [38:0] p1_m [0:DEL-1];
    reg [10:0] p2_x [0:DEL-1]; reg [4:0] p2_f [0:DEL-1]; reg [FW-1:0] p2_d [0:DEL-1];
    reg [DEL-1:0] p3_v; reg [10:0] p3_x [0:DEL-1]; reg [4:0] p3_f [0:DEL-1]; reg [FW-1:0] p3_d [0:DEL-1]; reg [39:0] p3_p [0:DEL-1];
    reg [DEL-1:0] p4_v; reg [10:0] p4_x [0:DEL-1]; reg [4:0] p4_f [0:DEL-1]; reg [FW-1:0] p4_d [0:DEL-1]; reg [39:0] p4_a [0:DEL-1];
    localparam integer QW = FW + 56;     // {addr 40, x 11, f 5, data}
    wire [DEL-1:0] fe, fo; wire [QW-1:0] fd [0:DEL-1]; wire [6:0] fc [0:DEL-1];
    wire [DEL-1:0] pop;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_l
        assign del_permit[l] = (cr[l] != 8'd0);
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(QW), .AW(6)) u_q (.clk(clk), .rst_n(rst_n), .push(p4_v[l]),
            .din({p4_a[l], p4_x[l], p4_f[l], p4_d[l]}), .pop(pop[l]), .empty(fe[l]), .dout(fd[l]), .ovf(fo[l]), .count(fc[l]));
        assign w_addr[l*40 +: 40] = fd[l][FW+16 +: 40];
        assign w_v[l] = !fe[l] && !disc_q;
        assign w_x[l*11 +: 11] = fd[l][FW+5 +: 11];
        assign w_f[l*5 +: 5] = fd[l][FW +: 5];
        assign w_data[l*FW +: FW] = fd[l][FW-1:0];
        assign pop[l] = !fe[l] && (disc_q || w_rdy[l]);
    end
    reg [DEL-1:0] pop_q;
    // drained: every reserved credit is back (each reservation's flit has left the FIFO), nothing in the decode stages
    reg [DEL-1:0] full_cr;
    always @* for (integer l = 0; l < DEL; l = l + 1) full_cr[l] = (cr[l] == 8'(CAP));
    assign drained = (&full_cr) && (p1_v == '0) && (p2_v == '0) && (p3_v == '0) && (p4_v == '0) && (&fe) && (pop_q == '0) && (del_reserve == '0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault <= 1'b0; p1_v <= '0; p2_v <= '0; p3_v <= '0; p4_v <= '0; pop_q <= '0; ob_q <= 40'd0; os_q <= 32'd0; ovm_q <= 1'b0; f_q <= 6'd1; k_q <= 12'd1; disc_q <= 1'b0; rcp_q <= 23'd0;
            for (integer l = 0; l < DEL; l = l + 1) cr[l] <= 8'(CAP);
        end else begin
            if (start) begin
                f_q <= cfg_nflit; k_q <= cfg_k; disc_q <= cfg_discard; rcp_q <= rcp(cfg_nflit);
                ob_q <= cfg_obase; os_q <= cfg_ostride; ovm_q <= cfg_ovm;
            end
            pop_q <= pop;
            for (integer l = 0; l < DEL; l = l + 1) begin
                // credit: reserve at dispatch, return one edge after the FIFO pop
                cr[l] <= cr[l] - ((MUT_CREDIT != 0) ? 8'd0 : 8'(del_reserve[l])) + 8'(pop_q[l]);
                if (del_reserve[l] && cr[l] == 8'd0) fault <= 1'b1;
                // decode stage 1: gi * rcp; stage 2: x, f
                p1_v[l] <= del_valid[l];
                p1_gi[l] <= del_flit[l*PWT + FW +: 16]; p1_d[l] <= del_flit[l*PWT +: FW];
                p1_m[l] <= {23'd0, del_flit[l*PWT + FW +: 16]} * {16'd0, rcp_q};
                if (del_valid[l] && !del_flit[l*PWT + PWT - 1]) fault <= 1'b1;
                p2_v[l] <= p1_v[l];
                begin : dec
                    reg [16:0] x_;
                    x_ = 17'(p1_m[l] >> 22);
                    p2_x[l] <= 11'(x_); p2_f[l] <= 5'(p1_gi[l] - 16'(x_ * 17'(f_q))); p2_d[l] <= p1_d[l];
                    if (p1_v[l] && x_ >= 17'(k_q)) fault <= 1'b1;
                end
                // stage 3: x * stride; stage 4: the O address
                p3_v[l] <= p2_v[l]; p3_x[l] <= p2_x[l]; p3_f[l] <= p2_f[l]; p3_d[l] <= p2_d[l];
                p3_p[l] <= 40'(p2_x[l]) * 40'(os_q);
                p4_v[l] <= p3_v[l]; p4_x[l] <= p3_x[l]; p4_f[l] <= p3_f[l]; p4_d[l] <= p3_d[l];
                p4_a[l] <= ob_q + p3_p[l] + (ovm_q ? {31'd0, p3_f[l], 4'd0} : {29'd0, p3_f[l], 6'd0});
                if (fo[l]) fault <= 1'b1;
            end
        end
    end
endmodule
`default_nettype wire
