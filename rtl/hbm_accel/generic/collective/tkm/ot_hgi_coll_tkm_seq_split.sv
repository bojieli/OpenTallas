`timescale 1ns/1ps
// Wires-only sequencer parent: four independently clocked ingress leaves plus own-flop core.
module ot_hgi_coll_tkm_seq_split #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    output wire [339:0] chain_entry,
    output wire chain_valid,
    input wire [339:0] chain_up,
    output wire [((KMAX+63)/64)-1:0] chain_clr, chain_conv,
    output wire [6*((KMAX+63)/64)-1:0] chain_tt,
    output wire [7*((KMAX+63)/64)-1:0] chain_tl,
    input wire [84*((KMAX+63)/64)-1:0] chain_tau,
    input wire [((KMAX+63)/64)-1:0] chain_busy,
    input wire [DEL-1:0] lane_clk,
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
 wire[DEL-1:0]perm,ft,dv,fe,ldv,d0v,d1v,pop;
 wire[DEL*680-1:0]de,he;
 wire[DEL*8-1:0]hm,dn,occ,take;
 wire[DEL*2-1:0]hn;
 wire live;wire[82:0]tau;wire[7:0]g,gb;wire[15:0]pf;
 assign del_permit=perm;
 ot_hgi_coll_tkm_seq_lane_core #(.KMAX(KMAX),.DEL(DEL),.FW(FW),.PWT(PWT),.CAP(CAP),.MUT(MUT))u_core(
   .lane_d0v(d0v),.lane_d1v(d1v),.lane_permit(perm),.lane_fault(ft),.lane_dv(dv),.lane_fe(fe),.lane_ldv(ldv),
   .lane_de(de),.lane_he(he),.lane_hm(hm),.lane_dn(dn),.lane_occ(occ),.lane_hn(hn),.lane_take(take),.lane_pop(pop),
   .lane_live(live),.lane_tau(tau),.lane_g(g),.lane_gb(gb),.lane_pf(pf),
   .chain_entry(chain_entry),
   .chain_valid(chain_valid),
   .chain_up(chain_up),
   .chain_clr(chain_clr),
   .chain_tt(chain_tt),
   .chain_tl(chain_tl),
   .chain_tau(chain_tau),
   .chain_busy(chain_busy),
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
 for(genvar l=0;l<DEL;l=l+1)begin:g_lane
  wire[1:0]early;
  assign d0v[l]=early[0];assign d1v[l]=early[1];
  ot_hgi_coll_tkm_lane #(.MUT(MUT))u_lane(.clk(lane_clk[l]),.rst_n(rst_n),
   .del_valid(del_valid[l]),.del_reserve(del_reserve[l]),.del_flit(del_flit[PWT*l+:PWT]),
   .cfg_g(g),.cfg_gbase(gb),.cfg_pf(pf),.ins_live(live),.tau(tau),.sel_take(take[8*l+:8]),.sel_pop(pop[l]),
   .del_permit(perm[l]),.fault(ft[l]),.early_valid(early),.decoded_v(dv[l]),.decoded_e(de[680*l+:680]),
   .head_e(he[680*l+:680]),.head_m(hm[8*l+:8]),.taken(dn[8*l+:8]),.head_n(hn[2*l+:2]),.occ(occ[8*l+:8]),
   .landing_v(ldv[l]),.fifo_empty(fe[l]));
 end
`ifndef SYNTHESIS
 wire[3:0]ph=u_core.ph;
`endif
endmodule
