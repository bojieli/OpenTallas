`timescale 1ns/1ps
// Wires-only sequencer parent: four independently clocked ingress leaves plus own-flop core.
module ot_hgi_coll_tkm_seq_split #(
    parameter integer NATIVE_OUTPUT=0,
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
    input wire buffer_clk,
    input wire packer_clk,
    input wire[39:0]native_control,output wire[544:0]native_write,
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
 wire[DEL*680-1:0]he;wire[DEL*2720-1:0]heads;wire[DEL*32-1:0]masks;wire[DEL*8-1:0]epochs,take_epochs;
 wire[DEL*8-1:0]nv_mask;
 wire[DEL*8-1:0]hm,dn,occ,take;
 wire[DEL*3-1:0]hn;
 wire live;wire[82:0]tau;wire[7:0]g,gb;wire[15:0]pf;
 wire bwv,brv,bresp;wire[9:0]bwa,bra;wire[339:0]bwd,brd;
 ot_hgi_coll_tkm_buffer u_buffer(.clk(buffer_clk),.rst_n(rst_n),.w_v(bwv),.w_addr(bwa),.w_data(bwd),.r_v(brv),.r_addr(bra),.rd_v(bresp),.rd_data(brd));
 wire ps,pcv,plast,pempty;wire[339:0]pcell;wire[1:0]pslot;
 wire[12:0]pnout;wire[39:0]pob,prb;wire phr;wire[3:0]pq;wire[9:0]pl;
 wire core_busy,core_done,core_fault;
 if(NATIVE_OUTPUT)begin:g_native_output
  ot_hfd_tkm_native_output_leaf #(.MUT(MUT))u_output(.clk(packer_clk),.rst_n(rst_n),.start(ps),
   .cfg_nout(pnout),.cfg_obase(pob),.cfg_rbase(prb),.cfg_has_r(phr),
   .cell_v(pcv),.cell_t(pcell),.cell_slot(pslot),.cell_last(plast),.native_control(native_control),
   .core_done(core_done),.core_busy(core_busy),.core_fault(core_fault),.native_write(native_write),
   .done(done),.busy(busy),.fault(fault),.queued(pq),.lines_pushed(pl),.pack_empty(pempty));
  assign w_v=1'b0;assign w_addr=0;assign w_mask=0;assign w_data=0;
 end else begin:g_legacy_output
 ot_hgi_coll_tkm_packer #(.FW(FW),.MUT(MUT))u_packer(.clk(packer_clk),.rst_n(rst_n),
 .start(ps),.cfg_nout(pnout),.cfg_obase(pob),.cfg_rbase(prb),.cfg_has_r(phr),
 .cell_v(pcv),.cell_t(pcell),.cell_slot(pslot),.cell_last(plast),.w_rdy(w_rdy),
 .w_ack(1'b0),.w_seq(),.w_v(w_v),.w_addr(w_addr),.w_mask(w_mask),.w_data(w_data),.queued(pq),.lines_pushed(pl),.empty(pempty));
 assign del_permit=perm;
  assign native_write=0;assign busy=core_busy;assign done=core_done;assign fault=core_fault;
 end
 ot_hgi_coll_tkm_seq_lane_core #(.KMAX(KMAX),.DEL(DEL),.FW(FW),.PWT(PWT),.CAP(CAP),.MUT(MUT))u_core(
   .lane_d0v(d0v),.lane_d1v(d1v),.lane_fault(ft),.lane_dv(dv),.lane_ldv(ldv),
   .lane_heads0(heads[0+:2720]),.lane_masks0(masks[0+:32]),.lane_epoch0(epochs[0+:8]),.lane_hn0(hn[0+:3]),.lane_heads1(heads[2720+:2720]),.lane_masks1(masks[32+:32]),.lane_epoch1(epochs[8+:8]),.lane_hn1(hn[3+:3]),.lane_heads2(heads[5440+:2720]),.lane_masks2(masks[64+:32]),.lane_epoch2(epochs[16+:8]),.lane_hn2(hn[6+:3]),.lane_heads3(heads[8160+:2720]),.lane_masks3(masks[96+:32]),.lane_epoch3(epochs[24+:8]),.lane_hn3(hn[9+:3]),.lane_take_epochs(take_epochs),.lane_nv_mask(nv_mask),.lane_occ(occ),.lane_take(take),.lane_pop(pop),
   .lane_live(live),.lane_tau(tau),.lane_g(g),.lane_gb(gb),.lane_pf(pf),
   .chain_entry(chain_entry),
   .chain_valid(chain_valid),
   .chain_up(chain_up),
   .chain_clr(chain_clr),
   .chain_conv(chain_conv),
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
   .buf_w_v(bwv),.buf_w_addr(bwa),.buf_w_data(bwd),.buf_r_v(brv),.buf_r_addr(bra),.buf_rd_v(bresp),.buf_rd_data(brd),
   .w_v(NATIVE_OUTPUT?!pempty:w_v),.pack_empty(pempty),.pack_queued(pq),.pack_lines(pl),
   .pack_start(ps),.pack_cell_v(pcv),.pack_last(plast),.pack_cell(pcell),.pack_slot(pslot),
   .pack_nout(pnout),.pack_obase(pob),.pack_rbase(prb),.pack_has_r(phr),
   .busy(core_busy),
   .done(core_done),
   .fault(core_fault),
   .stat_cycles(stat_cycles),
   .stat_ins(stat_ins),
   .stat_surv(stat_surv));
 for(genvar l=0;l<DEL;l=l+1)begin:g_lane
  wire[1:0]early;
  assign d0v[l]=early[0];assign d1v[l]=early[1];
  ot_hgi_coll_tkm_lane #(.MUT(MUT),.HEAD_SEAM(1))u_lane(.clk(lane_clk[l]),.rst_n(rst_n),
   .del_valid(del_valid[l]),.del_reserve(del_reserve[l]),.del_flit(del_flit[PWT*l+:PWT]),
   .cfg_g(g),.cfg_gbase(gb),.cfg_pf(pf),.ins_live(live),.tau(tau),.sel_take(take[8*l+:8]),.sel_pop(pop[l]),.sel_epoch(take_epochs[8*l+:8]),
   .del_permit(perm[l]),.fault(ft[l]),.early_valid(early),.decoded_v(dv[l]),.decoded_mask(nv_mask[8*l+:8]),
   .heads_e(heads[2720*l+:2720]),.heads_m(masks[32*l+:32]),.head_epoch(epochs[8*l+:8]),.head_e(he[680*l+:680]),.head_m(hm[8*l+:8]),.taken(dn[8*l+:8]),.head_n(hn[3*l+:3]),.occ(occ[8*l+:8]),
   .landing_v(ldv[l]),.fifo_empty(fe[l]));
 end
`ifndef SYNTHESIS
 wire[3:0]ph=u_core.ph;
`endif
endmodule
