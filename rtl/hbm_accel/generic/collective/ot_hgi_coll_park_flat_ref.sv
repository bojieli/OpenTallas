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
//   replay side : per queue c: hv[c] / hd[c] = the queue's head flit from a REGISTERED output stage (oq) loaded from
//                 the head bank's FWFT head (bank hb[c], advanced per load: the parking order); pop[c] is pin-flopped,
//                 so a popped head is replaced one edge later -- the parent must not pop the same queue on two
//                 consecutive edges (a queue replays at most every other cycle).  The parent keeps the occupancy count
//                 (the full check stays at the park decision, as in the flop form).
//   Boundary: every input lands in a pin flop, every output is a register (rtl_boundary registered_io).
//   ovf         : sticky, any bank FIFO overflowed (cannot happen while the parent's count check holds: fault input).
// Reset: through ot_rst_relay (EQ + 1 regions); pointers / valids only, payload registers are not reset.
// =====================================================================================================================
module ot_hgi_coll_park_flat_ref #(
    parameter integer EQ    = 4,
    parameter integer PPK   = 512,
    parameter integer DEL   = 4,
    parameter integer PWT   = 545,
    parameter integer MACRO = 2,        // ot_fifo_sram_fwft MACRO: 2 = ot_sram_1r1w_128x256 (PPK / DEL <= 128)
    parameter integer MUT_PARK = 0,     // bench mutant: 1 = bank index ignored (every lane writes bank 0)
    parameter [3:0]   PSTAGE_MASK = 4'b0010  // reference timing of the queues with a bank-local push stage (one park edge)
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire [DEL-1:0]               pv,
    input  wire [DEL*$clog2(EQ)-1:0]    pq,
    input  wire [DEL*$clog2(DEL)-1:0]   ps,
    input  wire [DEL*PWT-1:0]           pd,
    output wire [EQ-1:0]                hv,
    output wire [EQ*PWT-1:0]            hd,
    input  wire [EQ-1:0]                pop,
    output reg                          ovf
);
    localparam integer QB = (EQ > 1) ? $clog2(EQ) : 1;
    localparam integer SB = (DEL > 1) ? $clog2(DEL) : 1;
    localparam integer BD = PPK / DEL;
    initial if (BD * DEL != PPK) $fatal(1, "ot_hgi_coll_park: PPK must be a multiple of DEL");

    // ---- reset: the rst_n port drives only ot_rst_relay; region c = queue c (banks + head), region EQ = pin flops ----
    wire [EQ:0] rn;
    ot_rst_relay #(.REGIONS(EQ + 1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    // ---- pin flops (park side): valid reset, payload not ---------------------------------------------------------
    reg [DEL-1:0]     r_v;
    reg [QB-1:0]      r_q [0:DEL-1];
    reg [SB-1:0]      r_s [0:DEL-1];
    reg [PWT-1:0]     r_d [0:DEL-1];
    integer l;
    reg [EQ-1:0]      pop_r;
    always @(posedge clk or negedge rn[EQ])
        if (!rn[EQ]) begin r_v <= '0; pop_r <= '0; end else begin r_v <= pv; pop_r <= pop; end
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
        reg  [SB-1:0]  hb;                     // bank of the next flit to load into the output register
        reg            ohv; reg [PWT-1:0] ohd;  // registered queue head
        wire           ld;                     // load the output register from the head bank this edge
        assign hv[c] = ohv; assign hd[c*PWT +: PWT] = ohd;
        for (b = 0; b < DEL; b = b + 1) begin : g_b
            reg            push; reg [PWT-1:0] wd;
            integer        k;
            always @* begin
                push = 1'b0; wd = '0;
                for (k = 0; k < DEL; k = k + 1)
                    if (r_v[k] && r_q[k] == c[QB-1:0] && r_s[k] == b[SB-1:0]) begin push = 1'b1; wd = wd | r_d[k]; end
            end
            wire bpop = ld && hb == b[SB-1:0];
            wire bpush; wire [PWT-1:0] bwd;
            if (PSTAGE_MASK[c]) begin : g_ps
                reg ps_v; reg [PWT-1:0] ps_d;
                always @(posedge clk or negedge rn[c]) if (!rn[c]) ps_v <= 1'b0; else ps_v <= push;
                always @(posedge clk) ps_d <= wd;
                assign bpush = ps_v; assign bwd = ps_d;
            end else begin : g_nps
                assign bpush = push; assign bwd = wd;
            end
            ot_fifo_sram_fwft #(.W(PWT), .DEPTH(BD), .MACRO(MACRO)) u_f (.clk(clk), .rst_n(rn[c]), .push(bpush), .wdata(bwd),
                .pop(bpop), .hv(b_hv[c*DEL + b]), .head(b_hd[c*DEL + b]), .ovf(b_ovf[c*DEL + b]));
        end
        // registered queue head: (re)load when empty or popped last edge, from the head bank's FWFT head
        assign ld = (!ohv || pop_r[c]) && b_hv[c*DEL + hb];
        always @(posedge clk or negedge rn[c])
            if (!rn[c]) begin ohv <= 1'b0; hb <= '0; end
            else begin
                if (ld) begin ohv <= 1'b1; hb <= (DEL > 1) ? SB'((hb + 1) % DEL) : '0; end
                else if (pop_r[c]) ohv <= 1'b0;
            end
        always @(posedge clk) if (ld) ohd <= b_hd[c*DEL + hb];
    end endgenerate

    always @(posedge clk or negedge rn[EQ])
        if (!rn[EQ]) ovf <= 1'b0; else if (|b_ovf) ovf <= 1'b1;
endmodule
