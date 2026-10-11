`timescale 1ns/1ps
// =====================================================================================================================
// ot_hgi_coll_park: SRAM parking store of the pipelined ALL_GATHER (ot_hgi_coll_ep PIPE=1, PKSRAM=1).
//
// fe-push-hgi-1010 (feasibility 2026-10-10, item (e)): the flop form pk[EQ][PPK] x PWT (EQ 4, PPK 512, PWT 545 =
// ~1.1 Mb of flops, up to DEL lanes writing one queue an edge) cannot map to 1-port macros.  Here every epoch queue c
// is DEL interleaved banks: the k-th flit parked into queue c goes to bank k mod DEL.  The flits one edge parks into
// one queue take consecutive sequence numbers, so they land in DISTINCT banks: every bank has ONE writer an edge.
// Each bank is an ot_fifo_sram_fwft (catalog 1R1W macros, registered 2-entry head buffer); the queue head is the
// head of bank (h mod DEL), so the queue pops in exactly the parking order of the flop form.
//
//   park side   : per delivery lane l: pv[l] (park this edge), pq[l] (queue), ps[l] (bank = sequence mod DEL) and the
//                 flit; registered here at the pins (one edge), then pushed into the bank (bank write = AND-OR of the
//                 registered lanes, one-hot by construction).
//   replay side : per queue c: hv[c] / hd[c] = the queue's head flit (valid once the flit has reached its bank's head
//                 buffer: >= 2 edges after the park decision); pop[c] consumes it.  The parent keeps the occupancy count
//                 (the full check stays at the park decision, as in the flop form) and the head sequence number.
//   ovf         : sticky, any bank FIFO overflowed (cannot happen while the parent's count check holds: fault input).
// Reset: pointers / valids only (inside ot_fifo_sram_fwft); payload registers are not reset.
// =====================================================================================================================
module ot_hgi_coll_park #(
    parameter integer EQ    = 4,
    parameter integer PPK   = 512,
    parameter integer DEL   = 4,
    parameter integer PWT   = 545,
    parameter integer MACRO = 2,        // ot_fifo_sram_fwft MACRO: 2 = ot_sram_1r1w_128x256 (PPK / DEL <= 128)
    parameter integer MUT_PARK = 0      // bench mutant: 1 = bank index ignored (every lane writes bank 0)
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire [DEL-1:0]               pv,
    input  wire [DEL*$clog2(EQ)-1:0]    pq,
    input  wire [DEL*$clog2(DEL)-1:0]   ps,
    input  wire [DEL*PWT-1:0]           pd,
    input  wire [EQ*$clog2(DEL)-1:0]    hs,     // per queue: bank of the head flit (head sequence mod DEL)
    output wire [EQ-1:0]                hv,
    output wire [EQ*PWT-1:0]            hd,
    input  wire [EQ-1:0]                pop,
    output reg                          ovf
);
    localparam integer QB = (EQ > 1) ? $clog2(EQ) : 1;
    localparam integer SB = (DEL > 1) ? $clog2(DEL) : 1;
    localparam integer BD = PPK / DEL;
    initial if (BD * DEL != PPK) $fatal(1, "ot_hgi_coll_park: PPK must be a multiple of DEL");

    // ---- pin flops (park side): valid reset, payload not ---------------------------------------------------------
    reg [DEL-1:0]     r_v;
    reg [QB-1:0]      r_q [0:DEL-1];
    reg [SB-1:0]      r_s [0:DEL-1];
    reg [PWT-1:0]     r_d [0:DEL-1];
    integer l;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) r_v <= '0; else r_v <= pv;
    always @(posedge clk)
        for (l = 0; l < DEL; l = l + 1) begin
            r_q[l] <= pq[l*QB +: QB];
            r_s[l] <= (MUT_PARK == 1) ? '0 : ps[l*SB +: SB];
            if (pv[l]) r_d[l] <= pd[l*PWT +: PWT];
        end

    // ---- banks ---------------------------------------------------------------------------------------------------
    wire [EQ*DEL-1:0]     b_hv, b_ovf;
    wire [PWT-1:0]        b_hd [0:EQ*DEL-1];
    genvar c, b;
    generate for (c = 0; c < EQ; c = c + 1) begin : g_q
        for (b = 0; b < DEL; b = b + 1) begin : g_b
            reg            push; reg [PWT-1:0] wd;
            integer        k;
            always @* begin
                push = 1'b0; wd = '0;
                for (k = 0; k < DEL; k = k + 1)
                    if (r_v[k] && r_q[k] == c[QB-1:0] && r_s[k] == b[SB-1:0]) begin push = 1'b1; wd = wd | r_d[k]; end
            end
            wire bpop = pop[c] && hs[c*SB +: SB] == b[SB-1:0];
            ot_fifo_sram_fwft #(.W(PWT), .DEPTH(BD), .MACRO(MACRO)) u_f (.clk(clk), .rst_n(rst_n), .push(push), .wdata(wd),
                .pop(bpop), .hv(b_hv[c*DEL + b]), .head(b_hd[c*DEL + b]), .ovf(b_ovf[c*DEL + b]));
        end
        // queue head = head of its head bank
        assign hv[c] = b_hv[c*DEL + hs[c*SB +: SB]];
        assign hd[c*PWT +: PWT] = b_hd[c*DEL + hs[c*SB +: SB]];
    end endgenerate

    always @(posedge clk or negedge rst_n)
        if (!rst_n) ovf <= 1'b0; else if (|b_ovf) ovf <= 1'b1;
endmodule
