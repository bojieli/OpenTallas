`timescale 1ns/1ps
// PROPOSED native40/545 composition, no die/pacing/price adoption.
// Structural extraction: wires-only parent, sequencer own root, one entry per immutable CLOSED tile.
// Broadcast/return stations and legal die-pin placement remain required before parent qualification.
module ot_hgi_coll_tkm_native_cluster #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    input wire tile_ck0,
    input wire tile_ck1,
    input wire tile_ck2,
    input wire tile_ck3,
    input wire tile_ck4,
    input wire tile_ck5,
    input wire tile_ck6,
    input wire tile_ck7,
    input wire tile_ck8,
    input wire tile_ck9,
    input wire tile_ck10,
    input wire tile_ck11,
    input wire tile_ck12,
    input wire tile_ck13,
    input wire tile_ck14,
    input wire tile_ck15,
    input wire tile_ck16,
    input wire tile_ck17,
    input wire tile_ck18,
    input wire tile_ck19,
    input wire tile_ck20,
    input wire tile_ck21,
    input wire tile_ck22,
    input wire tile_ck23,
    input wire tile_ck24,
    input wire tile_ck25,
    input wire tile_ck26,
    input wire tile_ck27,
    input wire tile_ck28,
    input wire tile_ck29,
    input wire tile_ck30,
    input wire tile_ck31,
    input wire config_ck,
    input wire[39:0]native_control,output wire[544:0]native_write,
    input wire buffer_ck,
    input wire packer_ck,
    input wire lane_ck0,
    input wire lane_ck1,
    input wire lane_ck2,
    input wire lane_ck3,
    input  wire                 clk,
    input  wire                 rst_n,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output wire                 busy,
    output wire                  done,           // one edge: every output line accepted
    output wire                  fault,
    output wire                  config_fault,
    output wire  [31:0]          stat_cycles,    // start -> done
    output wire  [31:0]          stat_ins,       // blocks inserted
    output wire  [31:0]          stat_surv       // survivors taken
);
    wire start,seq_fault;
    wire[11:0]cfg_n;wire[12:0]cfg_k,cfg_nout;wire[7:0]cfg_g,cfg_gbase;
    wire[15:0]cfg_pf;wire[39:0]cfg_obase,cfg_rbase;wire cfg_has_r;
    wire[DEL-1:0]del_reserve;wire w_v;wire[39:0]w_addr;wire[15:0]w_mask;wire[FW-1:0]w_data;
    wire w_rdy=1'b0;assign fault=seq_fault;
    ot_hfd_tkm_native_config_leaf u_config(.clk(config_ck),.rst_n(rst_n),.packet(native_control),
      .start(start),.fault(config_fault),.n(cfg_n),.k(cfg_k),.nout(cfg_nout),.g(cfg_g),.gbase(cfg_gbase),
      .pf(cfg_pf),.obase(cfg_obase),.rbase(cfg_rbase),.has_r(cfg_has_r),.reservations(del_reserve));
    wire [31:0] tile_clk={tile_ck31,tile_ck30,tile_ck29,tile_ck28,tile_ck27,tile_ck26,tile_ck25,tile_ck24,tile_ck23,tile_ck22,tile_ck21,tile_ck20,tile_ck19,tile_ck18,tile_ck17,tile_ck16,tile_ck15,tile_ck14,tile_ck13,tile_ck12,tile_ck11,tile_ck10,tile_ck9,tile_ck8,tile_ck7,tile_ck6,tile_ck5,tile_ck4,tile_ck3,tile_ck2,tile_ck1,tile_ck0};
    wire [3:0] lane_clk={lane_ck3,lane_ck2,lane_ck1,lane_ck0};
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
    ot_hgi_coll_tkm_seq_split #(.NATIVE_OUTPUT(1),.KMAX(KMAX),.DEL(DEL),.FW(FW),.PWT(PWT),.CAP(CAP),.MUT(MUT))u_seq(
        .native_control(native_control),.native_write(native_write),.buffer_clk(buffer_ck),.packer_clk(packer_ck),.lane_clk(lane_clk),
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
        .fault(seq_fault),
        .stat_cycles(stat_cycles),
        .stat_ins(stat_ins),
        .stat_surv(stat_surv));
`ifndef SYNTHESIS
    // Preserve the existing benchmark phase trace through the extracted sequencer.
    wire [3:0] ph = u_seq.ph;
`endif
    for (genvar t=0; t<NT; t=t+1) begin : g_t
`ifdef OT_TKM_TILE_HARD
        ot_hgi_coll_tkm_tile u_t (
`else
        ot_hgi_coll_tkm_tile #(.PT((KMAX<64)?KMAX:64)) u_t (
`endif
          .clk(tile_clk[t]), .tid(6'(t)), .clr(chain_clr[t]), .conv(chain_conv[t]),
          .tau_t(chain_tt[6*t +: 6]), .tau_l(chain_tl[7*t +: 7]),
          .ins_v(down_v[t]), .ins_b(down[t]), .ovf_v(down_v[t+1]), .ovf_b(down[t+1]),
          .up_in(up[t+1]), .up_out(up[t]), .tau_o(chain_tau[84*t +: 84]), .busy(chain_busy[t]));
    end
endmodule
