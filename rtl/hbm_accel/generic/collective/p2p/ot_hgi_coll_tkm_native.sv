`timescale 1ns/1ps
// HISTORICAL (OWNER 2026-10-14T23:16 HANDOFF 0an): credit/ready flow control on an on-chip HBM path. Diagnostic/component
// evidence only; NOT the production schedule. Being replaced by compiler-assigned fixed transfer slots (H-COLL plan, el1014-hbm-p2p-coll.log).
// Native TKM wrapper: explicit 32 tile clocks, 4 SRAM ingress clocks and sequencer clock.
// Structural extraction: wires-only parent, sequencer own root, one entry per immutable CLOSED tile.
// Broadcast/return stations and legal die-pin placement remain required before parent qualification.
module ot_hgi_coll_tkm_native #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    input wire [31:0] tile_clk,
    input wire [3:0] lane_clk,
    input wire buffer_clk, packer_clk,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,          // one edge: configuration below valid
    input  wire [11:0]          cfg_n,          // this rank's n (informational: validity is the sender's pad marker)
    input  wire [12:0]          cfg_k,          // k: O.n must equal min(k, elements received)
    input  wire [7:0]           cfg_g,          // group size
    input  wire [7:0]           cfg_gbase,      // the group's first rank (flit src - gbase = q)
    input  wire [15:0]          cfg_pf,         // ceil(n / 8)
    input  wire [12:0]          cfg_nout,       // O.n = min(k, the group's elements), 1 .. KMAX
    input  wire [39:0]          cfg_obase,      // O: VM word address (16-word aligned)
    input  wire [39:0]          cfg_rbase,      // R: VM word address (16-word aligned)
    input  wire                 cfg_has_r,
    input  wire [DEL-1:0]       del_reserve,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output wire                  w_v,
    output wire  [39:0]          w_addr,
    output wire  [15:0]          w_mask,
    output wire  [FW-1:0]        w_data,
    input  wire                 w_rdy,
    output wire                 busy,
    output wire                  done,           // one edge: every output line accepted
    output wire                  fault,
    output wire  [31:0]          stat_cycles,    // start -> done
    output wire  [31:0]          stat_ins,       // blocks inserted
    output wire  [31:0]          stat_surv       // survivors taken
);
    localparam integer NT = (KMAX+63)/64;
    wire [339:0] chain_entry, chain_up;
    wire chain_valid;
    wire [NT-1:0] chain_clr, chain_conv, chain_busy;
    wire [6*NT-1:0] chain_tt;
    wire [7*NT-1:0] chain_tl;
    wire [84*NT-1:0] chain_tau;
    wire [339:0] down [0:NT];
    wire [339:0] up [0:NT];
    wire [NT:0] down_v;
    assign down[0] = chain_entry;
    assign down_v[0] = chain_valid;
    assign up[NT] = '0;
    assign chain_up = up[0];
    ot_hgi_coll_tkm_seq_split #(.KMAX(KMAX),.DEL(DEL),.FW(FW),.PWT(PWT),.CAP(CAP),.MUT(MUT)) u_seq (.lane_clk(lane_clk), .buffer_clk(buffer_clk), .packer_clk(packer_clk), .native_control(40'd0), .native_write(),
        .chain_entry(chain_entry), .chain_valid(chain_valid), .chain_up(chain_up),
        .chain_clr(chain_clr), .chain_conv(chain_conv), .chain_tt(chain_tt), .chain_tl(chain_tl),
        .chain_tau(chain_tau), .chain_busy(chain_busy),
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .cfg_n(cfg_n),
        .cfg_k(cfg_k),
        .cfg_g(cfg_g),
        .cfg_gbase(cfg_gbase),
        .cfg_pf(cfg_pf),
        .cfg_nout(cfg_nout),
        .cfg_obase(cfg_obase),
        .cfg_rbase(cfg_rbase),
        .cfg_has_r(cfg_has_r),
        .del_reserve(del_reserve),
        .del_permit(del_permit),
        .del_valid(del_valid),
        .del_flit(del_flit),
        .w_v(w_v),
        .w_addr(w_addr),
        .w_mask(w_mask),
        .w_data(w_data),
        .w_rdy(w_rdy),
        .busy(busy),
        .done(done),
        .fault(fault),
        .stat_cycles(stat_cycles),
        .stat_ins(stat_ins),
        .stat_surv(stat_surv));
`ifndef SYNTHESIS
    // Preserve the existing benchmark phase trace through the extracted sequencer.
    wire [3:0] ph = u_seq.ph;
`endif
    for (genvar t=0; t<NT; t=t+1) begin : g_t
        ot_hgi_coll_tkm_tile #(.PT((KMAX<64)?KMAX:64)) u_t (
          .clk(tile_clk[t]), .tid(6'(t)), .clr(chain_clr[t]), .conv(chain_conv[t]),
          .tau_t(chain_tt[6*t +: 6]), .tau_l(chain_tl[7*t +: 7]),
          .ins_v(down_v[t]), .ins_b(down[t]), .ovf_v(down_v[t+1]), .ovf_b(down[t+1]),
          .up_in(up[t+1]), .up_out(up[t]), .tau_o(chain_tau[84*t +: 84]), .busy(chain_busy[t]));
    end
endmodule

