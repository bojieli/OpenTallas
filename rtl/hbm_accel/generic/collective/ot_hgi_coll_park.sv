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
// Structural successor: wires-only parent, EQ independent queue roots plus tiny fault station.
module ot_hgi_coll_park #(
    parameter integer HARD_CLOCKS=0,
    parameter integer EQ    = 4,
    parameter integer PPK   = 512,
    parameter integer DEL   = 4,
    parameter integer PWT   = 545,
    parameter integer MACRO = 2,        // ot_fifo_sram_fwft MACRO: 2 = ot_sram_1r1w_128x256 (PPK / DEL <= 128)
    parameter integer MUT_PARK = 0,     // bench mutant: 1 = bank index ignored (every lane writes bank 0)
    parameter [3:0]   PSTAGE_MASK = 4'b0010  // queues with the bank-local push stage (the hard wrappers: Q1 only)
) (
    input  wire                         clk,
    input  wire [EQ-1:0]                clk_q,
    input  wire                         rst_n,
    input  wire [DEL-1:0]               pv,
    input  wire [DEL*$clog2(EQ)-1:0]    pq,
    input  wire [DEL*$clog2(DEL)-1:0]   ps,
    input  wire [DEL*PWT-1:0]           pd,
    output wire [EQ-1:0]                hv,
    output wire [EQ*PWT-1:0]            hd,
    input  wire [EQ-1:0]                pop,
    output wire                         ovf
);
`ifdef OT_COLL_PARK_HARD
    initial if(EQ!=4 || DEL!=4 || PWT!=545 || PPK!=512 || MACRO!=2 || MUT_PARK!=0) $fatal(1,"Hard park contract requires EQ4 DEL4 PWT545 PPK512 MACRO2 no mutant");
`endif
    wire [EQ*DEL-1:0] bank_ovf;
    genvar q;
    generate for(q=0;q<EQ;q=q+1) begin:g_q
`ifdef OT_COLL_PARK_HARD
        if(q==0) begin:g_h0
          ot_hgi_coll_park_q0 u_q (.clk(HARD_CLOCKS != 0 ? clk_q[q] : clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv[q]),.hd(hd[q*PWT+:PWT]),.pop(pop[q]),.bank_ovf(bank_ovf[q*DEL+:DEL]));
        end
        else if(q==1) begin:g_h1
          ot_hgi_coll_park_q1 u_q (.clk(HARD_CLOCKS != 0 ? clk_q[q] : clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv[q]),.hd(hd[q*PWT+:PWT]),.pop(pop[q]),.bank_ovf(bank_ovf[q*DEL+:DEL]));
        end
        else if(q==2) begin:g_h2
          ot_hgi_coll_park_q2 u_q (.clk(HARD_CLOCKS != 0 ? clk_q[q] : clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv[q]),.hd(hd[q*PWT+:PWT]),.pop(pop[q]),.bank_ovf(bank_ovf[q*DEL+:DEL]));
        end
        else if(q==3) begin:g_h3
          ot_hgi_coll_park_q3 u_q (.clk(HARD_CLOCKS != 0 ? clk_q[q] : clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv[q]),.hd(hd[q*PWT+:PWT]),.pop(pop[q]),.bank_ovf(bank_ovf[q*DEL+:DEL]));
        end
`else
        ot_hgi_coll_park_queue #(.EQ(EQ),.QID(q),.PPK(PPK),.DEL(DEL),.PWT(PWT),.MACRO(MACRO),.MUT_PARK(MUT_PARK),.PSTAGE(PSTAGE_MASK[q])) u_q
        (.clk(HARD_CLOCKS != 0 ? clk_q[q] : clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv[q]),.hd(hd[q*PWT+:PWT]),.pop(pop[q]),.bank_ovf(bank_ovf[q*DEL+:DEL]));
`endif
    end endgenerate
`ifdef OT_COLL_PARK_HARD
    ot_hgi_coll_park_fault u_fault
`else
    ot_hgi_coll_park_fault #(.N(EQ*DEL)) u_fault
`endif(.clk(clk),.rst_n(rst_n),.bank_ovf(bank_ovf),.ovf(ovf));
endmodule
